from __future__ import annotations

import json
import os
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any


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
        
    from retail_os.core.database import REPO_ROOT
    for img in images:
        if not isinstance(img, str) or not img:
            continue
        # Case 1: Already absolute and exists
        if os.path.isabs(img) and os.path.exists(img):
            return True
        # Case 2: Relative to CWD
        if os.path.exists(img):
            return True
        # Case 3: Relative to REPO_ROOT (normpath handles slash differences)
        norm = img.replace("\\", "/")
        if "data/media/" in norm:
            idx = norm.index("data/media/")
            rel = norm[idx:]
            full = os.path.join(REPO_ROOT, rel)
            if os.path.exists(full):
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


def backfill_supplier_images_onecheq(
    *,
    session,
    supplier_id: int,
    batch: int = 5000,
    concurrency: int = 16,
    max_seconds: float = 540.0,
    cmd_id: str | None = None,
    progress_hook=None,
    should_abort=None,
) -> dict[str, Any]:
    """
    Backfills local images for ONECHEQ SupplierProducts.
    - Uses any remote URL already stored in SupplierProduct.images
    - If images list is empty, falls back to scraping product page to discover images
    """
    from retail_os.core.database import SupplierProduct
    from retail_os.utils.image_downloader import ImageDownloader
    from retail_os.scrapers.onecheq.scraper import scrape_onecheq_product
    import httpx

    batch = max(1, min(50000, int(batch)))
    concurrency = max(1, min(32, int(concurrency)))

    # Candidates: missing local image
    candidates: list[tuple[int, str, str, str]] = []
    rows = (
        session.query(SupplierProduct)
        .filter(SupplierProduct.supplier_id == int(supplier_id))
        .order_by(SupplierProduct.id.asc())
        .all()
    )
    for sp in rows:
        if _has_local(sp.images):
            continue
        sku = (sp.external_sku or str(sp.id)).strip()
        remote = _first_remote(sp.images)
        if remote:
            candidates.append((int(sp.id), sku, remote, "remote"))
        elif sp.product_url:
            candidates.append((int(sp.id), sku, sp.product_url, "html_discover"))
        if len(candidates) >= batch:
            break

    started = time.perf_counter()
    downloader = ImageDownloader()
    ok = 0
    fail = 0
    reasons: Counter[str] = Counter()
    total = len(candidates)

    def _dl(sp_id: int, sku: str, url: str, mode: str) -> tuple[int, dict]:
        try:
            try:
                if should_abort and bool(should_abort()):
                    return sp_id, {"success": False, "error": "cancelled"}
            except Exception:
                pass
            if mode == "html_discover":
                with httpx.Client(follow_redirects=True, timeout=25.0) as c:
                    parsed = scrape_onecheq_product(url, client=c) or {}
                remote_imgs = [parsed.get(k) for k in ("photo1", "photo2", "photo3", "photo4") if parsed.get(k)]
                if not remote_imgs:
                    return sp_id, {"success": False, "error": "no_images_found_on_product_page"}
                return sp_id, downloader.download_image(remote_imgs[0], sku, should_abort=should_abort)
            return sp_id, downloader.download_image(url, sku, should_abort=should_abort)
        except Exception as e:
            return sp_id, {"success": False, "error": f"exception: {e}"}

    futures = []
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        for sp_id, sku, url, mode in candidates:
            futures.append(ex.submit(_dl, sp_id, sku, url, mode))

        for fut in as_completed(futures):
            try:
                if should_abort and bool(should_abort()):
                    break
            except Exception:
                pass
            if (time.perf_counter() - started) > max_seconds:
                break
            sp_id, res = fut.result()
            if res.get("success"):
                path = res.get("path")
                sp = session.get(SupplierProduct, sp_id)
                if sp:
                    imgs = sp.images
                    if isinstance(imgs, str):
                        try:
                            imgs = json.loads(imgs)
                        except Exception:
                            imgs = [imgs]
                    if not isinstance(imgs, list):
                        imgs = []
                    if path and path not in imgs:
                        imgs = [path] + [x for x in imgs if x != path]
                        sp.images = imgs
                ok += 1
            else:
                fail += 1
                reasons[str(res.get("error") or "download_failed")[:160]] += 1

            # Progress (best-effort)
            done = ok + fail
            try:
                if progress_hook:
                    elapsed = time.perf_counter() - started
                    rate = (done / elapsed) if elapsed > 0 else 0.0
                    eta = int(round((max(total - done, 0) / rate))) if rate > 0 and total else None
                    progress_hook(
                        {
                            "phase": "images",
                            "supplier_id": int(supplier_id),
                            "done": int(done),
                            "total": int(total),
                            "eta_seconds": eta,
                            "message": f"Images: {done}/{total} (ok {ok}, failed {fail})",
                            "cmd_id": cmd_id,
                        }
                    )
            except Exception:
                pass

    session.commit()
    elapsed = time.perf_counter() - started

    # Remaining count
    remaining = (
        session.query(SupplierProduct)
        .filter(SupplierProduct.supplier_id == int(supplier_id))
        .all()
    )
    remaining_without_local = sum(1 for sp in remaining if not _has_local(sp.images))

    return {
        "candidates_queued": len(candidates),
        "downloaded_ok": ok,
        "downloaded_failed": fail,
        "top_failures": reasons.most_common(10),
        "remaining_without_local_images": remaining_without_local,
        "seconds": round(elapsed, 3),
        "batch": batch,
        "concurrency": concurrency,
        "max_seconds": max_seconds,
    }


def validate_launchlock(
    *,
    session,
    supplier_id: int,
    limit: int | None = 1000,
    cmd_id: str | None = None,
    progress_hook=None,
    should_abort=None,
) -> dict[str, Any]:
    from retail_os.core.database import SupplierProduct, InternalProduct
    from retail_os.core.validator import LaunchLock

    q = (
        session.query(InternalProduct)
        .join(SupplierProduct, InternalProduct.primary_supplier_product_id == SupplierProduct.id)
        .filter(SupplierProduct.supplier_id == int(supplier_id))
        .order_by(InternalProduct.id.asc())
    )
    if limit is not None:
        q = q.limit(int(limit))

    ips = q.all()
    v = LaunchLock(session)
    ready = 0
    blocked = 0
    reasons: Counter[str] = Counter()
    blocked_samples: list[dict[str, Any]] = []

    total = len(ips)
    started = time.perf_counter()

    for i, ip in enumerate(ips, 1):
        try:
            if should_abort and bool(should_abort()):
                break
        except Exception:
            pass
        try:
            v.validate_publish(ip, test_mode=False)
            ready += 1
        except Exception as e:
            blocked += 1
            msg = str(e)
            reasons[msg.split(":")[0][:120]] += 1
            if len(blocked_samples) < 10:
                sp = ip.supplier_product
                blocked_samples.append(
                    {
                        "internal_product_id": ip.id,
                        "sku": ip.sku,
                        "title": (sp.title if sp else None),
                        "url": (sp.product_url if sp else None),
                        "reason": msg[:300],
                    }
                )

        # Progress (best-effort)
        try:
            if progress_hook and (i == 1 or i % 50 == 0 or i == total):
                elapsed = time.perf_counter() - started
                rate = (i / elapsed) if elapsed > 0 else 0.0
                eta = int(round(max(total - i, 0) / rate)) if rate > 0 else None
                progress_hook(
                    {
                        "phase": "validate",
                        "supplier_id": int(supplier_id),
                        "done": int(i),
                        "total": int(total),
                        "eta_seconds": eta,
                        "message": f"Validate: {i}/{total} (ready {ready}, blocked {blocked})",
                        "cmd_id": cmd_id,
                    }
                )
        except Exception:
            pass

    return {
        "validated": int(min(total, (ready + blocked))),
        "ready": ready,
        "blocked": blocked,
        "top_blockers": reasons.most_common(20),
        "blocked_samples": blocked_samples,
        "limit": limit,
    }

