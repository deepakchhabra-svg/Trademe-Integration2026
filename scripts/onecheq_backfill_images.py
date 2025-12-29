"""
Backfill local images for OneCheq SupplierProducts (REAL MODE).

This is the missing step after doing a fast JSON scrape with
RETAILOS_IMAGE_LIMIT_PER_PRODUCT=0 (remote URLs only).

The script:
- Finds OneCheq rows without ANY local image path
- Downloads up to N rows per run (batch)
- Adds the downloaded local path to sp.images (keeps remote URLs too)
- Designed to be re-run until completion

Env:
- DATABASE_URL (sqlite:///... or postgres)
- RETAILOS_IMAGE_BACKFILL_BATCH (default 400)
- RETAILOS_IMAGE_BACKFILL_CONCURRENCY (default 16)
- RETAILOS_IMAGE_BACKFILL_MAX_SECONDS (default 540)  # keep under tool timeout
"""

from __future__ import annotations

import json
import os
import time
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Literal


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _has_local(images: Any) -> bool:
    if not images:
        return False
    if isinstance(images, str):
        try:
            images = json.loads(images)
        except Exception:
            images = [images]
    if not isinstance(images, list):
        return False
    for img in images:
        if isinstance(img, str) and img and (img.startswith("data/media/") or img.startswith("/workspace/data/media/")):
            if os.path.exists(img):
                return True
            # also allow relative data/media paths
            if img.startswith("data/media/") and os.path.exists(os.path.join("/workspace", img)):
                return True
    return False


def _first_remote(images: Any) -> str:
    if not images:
        return ""
    if isinstance(images, str):
        try:
            images = json.loads(images)
        except Exception:
            images = [images]
    if not isinstance(images, list):
        return ""
    for img in images:
        if isinstance(img, str) and img.startswith("http"):
            return img
    return ""


def main() -> None:
    import sys

    sys.path.append(os.getcwd())

    batch = int(os.getenv("RETAILOS_IMAGE_BACKFILL_BATCH", "400"))
    concurrency = int(os.getenv("RETAILOS_IMAGE_BACKFILL_CONCURRENCY", "16"))
    max_seconds = float(os.getenv("RETAILOS_IMAGE_BACKFILL_MAX_SECONDS", "540"))
    batch = max(1, min(5000, batch))
    concurrency = max(1, min(32, concurrency))

    from concurrent.futures import ThreadPoolExecutor, as_completed

    from retail_os.core.database import init_db, SessionLocal, Supplier, SupplierProduct
    from retail_os.utils.image_downloader import ImageDownloader
    from retail_os.scrapers.onecheq.scraper import scrape_onecheq_product
    import httpx

    init_db()

    s = SessionLocal()
    try:
        sup = s.query(Supplier).filter(Supplier.name == "ONECHEQ").first()
        if not sup:
            raise RuntimeError("ONECHEQ supplier missing in DB")
        supplier_id = int(sup.id)

        # Find candidates:
        # - Prefer direct remote URL already stored in sp.images
        # - If sp.images is empty (JSON endpoint had no images), fallback to HTML scrape to discover images
        candidates: list[tuple[int, str, str, Literal["remote", "html_discover"]]] = []
        rows = (
            s.query(SupplierProduct)
            .filter(SupplierProduct.supplier_id == supplier_id)
            .order_by(SupplierProduct.id.asc())
            .all()
        )
        for sp in rows:
            if _has_local(sp.images):
                continue
            url = _first_remote(sp.images)
            # stable key for filenames
            ext_sku = (sp.external_sku or str(sp.id)).strip()
            if url:
                candidates.append((int(sp.id), ext_sku, url, "remote"))
            else:
                # If no remote URL is present, try to discover one from the product page.
                if sp.product_url:
                    candidates.append((int(sp.id), ext_sku, sp.product_url, "html_discover"))
            if len(candidates) >= batch:
                break

        started = time.perf_counter()
        downloader = ImageDownloader()
        ok = 0
        fail = 0
        reasons: Counter[str] = Counter()

        def _dl(sp_id: int, sku: str, url: str, mode: Literal["remote", "html_discover"]) -> tuple[int, dict]:
            try:
                if mode == "html_discover":
                    with httpx.Client(follow_redirects=True, timeout=25.0) as c:
                        parsed = scrape_onecheq_product(url, client=c) or {}
                    # Extract candidate remote image URLs from parsed product page
                    remote_imgs = [parsed.get(k) for k in ("photo1", "photo2", "photo3", "photo4") if parsed.get(k)]
                    if not remote_imgs:
                        return sp_id, {"success": False, "error": "no_images_found_on_product_page"}
                    res = downloader.download_image(remote_imgs[0], sku)
                    if res.get("success"):
                        # Keep a hint that this came from HTML discovery (optional)
                        res["discovered_remote"] = remote_imgs[0]
                    return sp_id, res
                # mode == "remote"
                res = downloader.download_image(url, sku)
                return sp_id, res
            except Exception as e:
                return sp_id, {"success": False, "error": f"exception: {e}"}

        futures = []
        with ThreadPoolExecutor(max_workers=concurrency) as ex:
            for sp_id, sku, url, mode in candidates:
                futures.append(ex.submit(_dl, sp_id, sku, url, mode))

            for fut in as_completed(futures):
                if (time.perf_counter() - started) > max_seconds:
                    break
                sp_id, res = fut.result()
                if res.get("success"):
                    path = res.get("path")
                    sp = s.get(SupplierProduct, sp_id)
                    if sp:
                        imgs = sp.images
                        if isinstance(imgs, str):
                            try:
                                imgs = json.loads(imgs)
                            except Exception:
                                imgs = [imgs]
                        if not isinstance(imgs, list):
                            imgs = []
                        # Prepend local path, keep rest for reference
                        if path and path not in imgs:
                            imgs = [path] + [x for x in imgs if x != path]
                            sp.images = imgs
                    ok += 1
                else:
                    fail += 1
                    reasons[str(res.get("error") or "download_failed")[:120]] += 1

        s.commit()
        elapsed = time.perf_counter() - started

        remaining = (
            s.query(SupplierProduct)
            .filter(SupplierProduct.supplier_id == supplier_id)
            .all()
        )
        remaining_without_local = sum(1 for sp in remaining if not _has_local(sp.images))

        print(
            json.dumps(
                {
                    "started_at": _now(),
                    "batch_requested": batch,
                    "candidates_queued": len(candidates),
                    "concurrency": concurrency,
                    "seconds": round(elapsed, 3),
                    "downloaded_ok": ok,
                    "downloaded_failed": fail,
                    "top_failures": reasons.most_common(10),
                    "remaining_without_local_images": remaining_without_local,
                    "finished_at": _now(),
                },
                indent=2,
            )
        )
    finally:
        s.close()


if __name__ == "__main__":
    main()

