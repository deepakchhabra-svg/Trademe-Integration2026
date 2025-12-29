"""
Full OneCheq backfill runner (REAL MODE).

This is designed to be run on your own machine/server (not inside a short-lived CI session).

It will:
1) Scrape ALL OneCheq products (collection=all, pages=UNLIMITED)
2) Deterministically enrich ALL scraped SupplierProducts (no LLM)
3) Compute publish-readiness stats using LaunchLock hard gates
4) Print a JSON report with timings + counts + top blocker reasons

Environment:
- DATABASE_URL: sqlite:///... (recommended) or postgres
- RETAILOS_ONECHEQ_CONCURRENCY: default 12
"""

from __future__ import annotations

import json
import os
import time
from collections import Counter
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    # Make repo root importable regardless of cwd.
    import sys

    sys.path.append(os.getcwd())

    from retail_os.core.database import SessionLocal, Supplier, SupplierProduct, InternalProduct, init_db
    from retail_os.core.marketplace_adapter import MarketplaceAdapter
    from retail_os.core.validator import LaunchLock
    from retail_os.core.category_mapper import CategoryMapper

    init_db()

    # Ensure supplier exists
    s = SessionLocal()
    try:
        sup = s.query(Supplier).filter(Supplier.name == "ONECHEQ").first()
        if not sup:
            sup = Supplier(name="ONECHEQ", base_url="https://onecheq.co.nz", is_active=True)
            s.add(sup)
            s.commit()
        supplier_id = int(sup.id)
    finally:
        s.close()

    # 1) SCRAPE
    t0 = time.perf_counter()
    from retail_os.scrapers.onecheq.adapter import OneCheqAdapter

    pages = 0  # unlimited
    OneCheqAdapter().run_sync(pages=pages, collection="all")
    scrape_s = time.perf_counter() - t0

    # 2) ENRICH (deterministic)
    t0 = time.perf_counter()
    db = SessionLocal()
    try:
        q = db.query(SupplierProduct).filter(SupplierProduct.supplier_id == supplier_id)
        rows = q.all()
        enrich_ok = 0
        enrich_fail = 0
        enrich_reasons: Counter[str] = Counter()

        for sp in rows:
            try:
                md = MarketplaceAdapter.prepare_for_trademe(sp, use_ai=False)
                sp.enrichment_status = "SUCCESS"
                sp.enrichment_error = None
                sp.enriched_title = md["title"]
                sp.enriched_description = md["description"]
                enrich_ok += 1
            except Exception as e:
                sp.enrichment_status = "FAILED"
                sp.enrichment_error = str(e)
                enrich_fail += 1
                enrich_reasons[str(e)[:120]] += 1
        db.commit()
    finally:
        db.close()
    enrich_s = time.perf_counter() - t0

    # 3) READINESS (hard gates)
    t0 = time.perf_counter()
    db = SessionLocal()
    try:
        validator = LaunchLock(db)
        # fast image existence: list filenames in data/media once
        media_dir = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")), "data", "media")
        media_files = set()
        try:
            if os.path.isdir(media_dir):
                media_files = set(os.listdir(media_dir))
        except Exception:
            media_files = set()

        def has_local(sp: SupplierProduct) -> bool:
            imgs = sp.images or []
            if not isinstance(imgs, list):
                return False
            for raw in imgs:
                if not isinstance(raw, str) or not raw:
                    continue
                norm = raw.replace("\\", "/")
                if norm.startswith("data/media/"):
                    fn = norm[len("data/media/") :]
                    if fn in media_files:
                        return True
                    if not media_files and os.path.exists(norm):
                        return True
            return False

        ips = (
            db.query(InternalProduct)
            .join(SupplierProduct, InternalProduct.primary_supplier_product_id == SupplierProduct.id)
            .filter(SupplierProduct.supplier_id == supplier_id)
            .all()
        )
        ready = 0
        blocked = 0
        blockers: Counter[str] = Counter()

        for ip in ips:
            sp = ip.supplier_product
            if not sp:
                blocked += 1
                blockers["Missing supplier product link"] += 1
                continue
            # Mirror LaunchLock's hard gates quickly (avoid doing expensive trust checks twice)
            if sp.cost_price is None or float(sp.cost_price or 0) <= 0:
                blocked += 1
                blockers["Missing/invalid cost price"] += 1
                continue
            if not (sp.enriched_title or "").strip():
                blocked += 1
                blockers["Missing enriched title"] += 1
                continue
            if not (sp.enriched_description or "").strip():
                blocked += 1
                blockers["Missing enriched description"] += 1
                continue
            if not has_local(sp):
                blocked += 1
                blockers["Missing images (local)"] += 1
                continue
            cat_id = CategoryMapper.map_category(getattr(sp, "source_category", "") or "", sp.title or "")
            if not cat_id:
                blocked += 1
                blockers["Missing category mapping"] += 1
                continue

            # Full validation (includes policy + margin; trust may block depending on configuration)
            try:
                validator.validate_publish(ip, test_mode=False)
            except Exception as e:
                blocked += 1
                blockers[str(e)[:120]] += 1
                continue

            ready += 1
    finally:
        db.close()
    readiness_s = time.perf_counter() - t0

    report = {
        "started_at": _now(),
        "supplier": "ONECHEQ",
        "timings_seconds": {
            "scrape": round(scrape_s, 3),
            "enrich": round(enrich_s, 3),
            "readiness": round(readiness_s, 3),
        },
        "counts": {
            "supplier_products": None,
            "internal_products": len(ips),
            "enriched_success": enrich_ok,
            "enriched_failed": enrich_fail,
            "ready_for_publish": ready,
            "blocked": blocked,
        },
        "top_enrich_failures": enrich_reasons.most_common(20),
        "top_blockers": blockers.most_common(30),
        "finished_at": _now(),
    }

    # Fill SupplierProduct count at the end (fresh session)
    db = SessionLocal()
    try:
        report["counts"]["supplier_products"] = db.query(SupplierProduct).filter(SupplierProduct.supplier_id == supplier_id).count()
    finally:
        db.close()

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

