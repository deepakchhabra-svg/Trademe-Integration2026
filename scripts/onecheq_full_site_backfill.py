"""
FULL OneCheq site backfill (REAL MODE).

This uses Shopify's authoritative JSON endpoint:
  https://onecheq.co.nz/collections/all/products.json?limit=250&page=N

Why:
- The HTML collection pages do NOT expose the full catalog reliably at 10k+ scale.
- The JSON endpoint returns the true catalog count (we measured 9089 products).

By default this script:
- Scrapes ALL products into the DB (streaming; no huge in-memory list)
- Downloads ZERO images (stores remote image URLs) for speed
  - Set RETAILOS_IMAGE_LIMIT_PER_PRODUCT=1..4 to download locally during backfill (slower)
- Deterministically enriches everything (no LLM)
- Runs LaunchLock on the first N items (default 1000) so you get hard publish readiness stats early

Env:
- DATABASE_URL (recommended sqlite:////tmp/onecheq_full.sqlite)
- RETAILOS_IMAGE_LIMIT_PER_PRODUCT (default 0 here)
- RETAILOS_ONECHEQ_SOURCE=json (default)
- RETAILOS_VALIDATE_N (default 1000)
"""

from __future__ import annotations

import json
import os
import time
from collections import Counter
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bucket(msg: str) -> str:
    m = (msg or "").strip()
    if not m:
        return "UNKNOWN"
    return m.split(":")[0][:120]


def main() -> None:
    import sys

    sys.path.append(os.getcwd())

    db_url = os.getenv("DATABASE_URL", "sqlite:////tmp/onecheq_full.sqlite")
    os.environ["DATABASE_URL"] = db_url
    os.environ["RETAILOS_ONECHEQ_SOURCE"] = os.getenv("RETAILOS_ONECHEQ_SOURCE", "json")
    os.environ["RETAILOS_IMAGE_LIMIT_PER_PRODUCT"] = os.getenv("RETAILOS_IMAGE_LIMIT_PER_PRODUCT", "0")

    validate_n = int(os.getenv("RETAILOS_VALIDATE_N", "1000"))

    from retail_os.core.database import init_db, SessionLocal, Supplier, SupplierProduct, InternalProduct
    from retail_os.scrapers.onecheq.adapter import OneCheqAdapter
    from retail_os.core.marketplace_adapter import MarketplaceAdapter
    from retail_os.core.validator import LaunchLock

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

    report: dict = {
        "started_at": _now(),
        "database_url": db_url,
        "onecheq_mode": os.getenv("RETAILOS_ONECHEQ_SOURCE"),
        "image_limit_per_product": int(os.getenv("RETAILOS_IMAGE_LIMIT_PER_PRODUCT", "0") or "0"),
        "scrape": {},
        "enrich": {},
        "launchlock": {},
        "finished_at": None,
    }

    # 1) SCRAPE (ALL)
    t0 = time.perf_counter()
    OneCheqAdapter().run_sync(pages=0, collection="all")
    scrape_s = time.perf_counter() - t0

    s = SessionLocal()
    try:
        sp_total = s.query(SupplierProduct).filter(SupplierProduct.supplier_id == supplier_id).count()
        ip_total = (
            s.query(InternalProduct)
            .join(SupplierProduct, InternalProduct.primary_supplier_product_id == SupplierProduct.id)
            .filter(SupplierProduct.supplier_id == supplier_id)
            .count()
        )
    finally:
        s.close()

    report["scrape"] = {"seconds": round(scrape_s, 3), "supplier_products_total": sp_total, "internal_products_total": ip_total}

    # 2) ENRICH (deterministic)
    t0 = time.perf_counter()
    s = SessionLocal()
    try:
        rows = s.query(SupplierProduct).filter(SupplierProduct.supplier_id == supplier_id).all()
        ok = 0
        fail = 0
        reasons = Counter()
        for sp in rows:
            try:
                md = MarketplaceAdapter.prepare_for_trademe(sp, use_ai=False)
                sp.enrichment_status = "SUCCESS"
                sp.enrichment_error = None
                sp.enriched_title = md["title"]
                sp.enriched_description = md["description"]
                ok += 1
            except Exception as e:
                sp.enrichment_status = "FAILED"
                sp.enrichment_error = str(e)
                fail += 1
                reasons[_bucket(str(e))] += 1
        s.commit()
        report["enrich"] = {
            "seconds": round(time.perf_counter() - t0, 3),
            "ok": ok,
            "fail": fail,
            "top_failures": reasons.most_common(20),
        }
    finally:
        s.close()

    # 3) LAUNCHLOCK validate first N (so you get hard readiness signal early)
    t0 = time.perf_counter()
    s = SessionLocal()
    try:
        v = LaunchLock(s)
        ips = (
            s.query(InternalProduct)
            .join(SupplierProduct, InternalProduct.primary_supplier_product_id == SupplierProduct.id)
            .filter(SupplierProduct.supplier_id == supplier_id)
            .order_by(InternalProduct.id.asc())
            .limit(validate_n)
            .all()
        )
        ready = 0
        blocked = 0
        blockers = Counter()
        for ip in ips:
            try:
                v.validate_publish(ip, test_mode=False)
                ready += 1
            except Exception as e:
                blocked += 1
                blockers[_bucket(str(e))] += 1
        report["launchlock"] = {
            "seconds": round(time.perf_counter() - t0, 3),
            "validated": len(ips),
            "ready": ready,
            "blocked": blocked,
            "top_blockers": blockers.most_common(30),
        }
    finally:
        s.close()

    report["finished_at"] = _now()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

