"""
OneCheq real-mode scrape + validate runner.

Goal:
- Scrape up to N products from OneCheq (collection=all), downloading at least 1 local image per product
- Deterministically enrich
- Validate at least 1000 items via:
  - LaunchLock (publish gates)
  - Source re-scrape compare (title + price + image presence)
  - (Optional) Trade Me Selling/Validate.json if credentials are available

This is designed to run unattended for a long time.
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

    # Controls
    target_scrape = int(os.getenv("RETAILOS_ONECHEQ_TARGET_SCRAPE", "1100"))
    validate_n = int(os.getenv("RETAILOS_VALIDATE_N", "1000"))
    concurrency = int(os.getenv("RETAILOS_ONECHEQ_CONCURRENCY", "16"))
    image_limit = int(os.getenv("RETAILOS_IMAGE_LIMIT_PER_PRODUCT", "1"))
    db_url = os.getenv("DATABASE_URL", "sqlite:////tmp/onecheq_scrape_validate.sqlite")
    os.environ["DATABASE_URL"] = db_url
    os.environ["RETAILOS_ONECHEQ_MAX_PRODUCTS"] = str(target_scrape)
    os.environ["RETAILOS_ONECHEQ_CONCURRENCY"] = str(concurrency)
    os.environ["RETAILOS_IMAGE_LIMIT_PER_PRODUCT"] = str(image_limit)

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
        "config": {
            "target_scrape": target_scrape,
            "validate_n": validate_n,
            "concurrency": concurrency,
            "image_limit_per_product": image_limit,
        },
        "scrape": {},
        "enrich": {},
        "launchlock": {},
        "source_compare": {},
        "trademe_validate": {},
        "finished_at": None,
    }

    # 1) SCRAPE (capped)
    t0 = time.perf_counter()
    OneCheqAdapter().run_sync(pages=0, collection="all")
    scrape_s = time.perf_counter() - t0

    s = SessionLocal()
    try:
        sp_total = s.query(SupplierProduct).filter(SupplierProduct.supplier_id == supplier_id).count()
        report["scrape"] = {"seconds": round(scrape_s, 3), "supplier_products_total": sp_total}
    finally:
        s.close()

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
        enrich_s = time.perf_counter() - t0
        report["enrich"] = {"seconds": round(enrich_s, 3), "ok": ok, "fail": fail, "top_failures": reasons.most_common(20)}
    finally:
        s.close()

    # 3) LAUNCHLOCK validate N
    t0 = time.perf_counter()
    s = SessionLocal()
    try:
        validator = LaunchLock(s)
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
                validator.validate_publish(ip, test_mode=False)
                ready += 1
            except Exception as e:
                blocked += 1
                blockers[_bucket(str(e))] += 1
        launch_s = time.perf_counter() - t0
        report["launchlock"] = {
            "seconds": round(launch_s, 3),
            "validated": len(ips),
            "ready": ready,
            "blocked": blocked,
            "top_blockers": blockers.most_common(30),
        }
    finally:
        s.close()

    # 4) SOURCE COMPARE validate N (re-scrape each product_url)
    t0 = time.perf_counter()
    s = SessionLocal()
    try:
        from retail_os.scrapers.onecheq.scraper import scrape_onecheq_product

        ips = (
            s.query(InternalProduct)
            .join(SupplierProduct, InternalProduct.primary_supplier_product_id == SupplierProduct.id)
            .filter(SupplierProduct.supplier_id == supplier_id)
            .order_by(InternalProduct.id.asc())
            .limit(validate_n)
            .all()
        )
        compared = 0
        mismatches = 0
        mismatch_reasons = Counter()
        for ip in ips:
            sp = ip.supplier_product
            if not sp or not sp.product_url:
                mismatches += 1
                mismatch_reasons["missing_product_url"] += 1
                continue
            live = scrape_onecheq_product(sp.product_url)
            if not live:
                mismatches += 1
                mismatch_reasons["live_scrape_failed"] += 1
                continue
            compared += 1
            # title check (case/whitespace normalized)
            t_db = " ".join((sp.title or "").split()).strip().lower()
            t_live = " ".join((live.get("title") or "").split()).strip().lower()
            if t_db and t_live and t_db != t_live:
                mismatches += 1
                mismatch_reasons["title_mismatch"] += 1
                continue
            # price check (allow small drift)
            try:
                p_db = float(sp.cost_price or 0)
                p_live = float(live.get("buy_now_price") or 0)
                if p_db > 0 and p_live > 0 and abs(p_db - p_live) > 1.0:
                    mismatches += 1
                    mismatch_reasons["price_mismatch"] += 1
                    continue
            except Exception:
                mismatches += 1
                mismatch_reasons["price_parse_failed"] += 1
                continue
            # images check (at least one remote image exists from live)
            if not (live.get("photo1") or live.get("photo2")):
                mismatches += 1
                mismatch_reasons["live_missing_images"] += 1
                continue
        src_s = time.perf_counter() - t0
        report["source_compare"] = {
            "seconds": round(src_s, 3),
            "validated": len(ips),
            "compared_ok": compared,
            "mismatches": mismatches,
            "top_mismatch_reasons": mismatch_reasons.most_common(20),
        }
    finally:
        s.close()

    # 5) Trade Me validate (optional)
    t0 = time.perf_counter()
    try:
        from retail_os.trademe.api import TradeMeAPI
        from retail_os.core.listing_builder import build_listing_payload

        api = TradeMeAPI()
        s = SessionLocal()
        try:
            ips = (
                s.query(InternalProduct)
                .join(SupplierProduct, InternalProduct.primary_supplier_product_id == SupplierProduct.id)
                .filter(SupplierProduct.supplier_id == supplier_id)
                .order_by(InternalProduct.id.asc())
                .limit(validate_n)
                .all()
            )
            ok = 0
            fail = 0
            reasons = Counter()
            for ip in ips:
                payload = build_listing_payload(ip.id)
                # Trade Me endpoints expect PhotoIds (uploaded). For validate, PhotoUrls may still be acceptable
                # but if not, this will fail and we record the reason.
                res = api.validate_listing(payload)
                if res.get("Success"):
                    ok += 1
                else:
                    fail += 1
                    reasons[_bucket(json.dumps(res)[:500])] += 1
            report["trademe_validate"] = {
                "seconds": round(time.perf_counter() - t0, 3),
                "validated": len(ips),
                "ok": ok,
                "fail": fail,
                "top_failures": reasons.most_common(10),
            }
        finally:
            s.close()
    except Exception as e:
        report["trademe_validate"] = {"skipped": True, "reason": str(e)[:300]}

    report["finished_at"] = _now()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

