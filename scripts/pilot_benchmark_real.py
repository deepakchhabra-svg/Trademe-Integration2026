"""
Pilot benchmark runner (REAL MODE).

What it does:
- Scrape real supplier data for configured categories (ONECHEQ + NOEL_LEEMING)
- Deterministically enrich scraped SupplierProducts (no LLM)
- Create/ensure InternalProducts for scraped SupplierProducts
- Run LaunchLock publish gate checks (the same pre-publish rules)
- Print a real metrics report: counts, timings, and top failure reasons

Safety:
- Does NOT publish anything to Trade Me.
- Uses a dedicated sqlite DB by default (in /tmp) unless DATABASE_URL is provided.
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

# Ensure repo root is importable when executed as a script.
sys.path.append(os.getcwd())


@dataclass(frozen=True)
class CategoryRun:
    supplier: str
    # ONECHEQ: Shopify collection handle (e.g. "smartphones-and-mobilephones")
    # NOEL_LEEMING: category URL
    source_category: str
    pages: int = 1
    deep_scrape: bool = False  # NL only


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_db_url() -> str:
    # Prefer caller-provided DATABASE_URL; otherwise isolate benchmark DB.
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url
    default = "sqlite:////tmp/retailos_pilot_benchmark.sqlite"
    os.environ["DATABASE_URL"] = default
    return default


def _supplier_row(session, name: str, base_url: str) -> Any:
    from retail_os.core.database import Supplier

    s = session.query(Supplier).filter(Supplier.name == name).first()
    if not s:
        s = Supplier(name=name, base_url=base_url, is_active=True)
        session.add(s)
        session.commit()
    return s


def _count_by_source_category(rows: Iterable[Any]) -> dict[str, int]:
    c: Counter[str] = Counter()
    for r in rows:
        c[str(getattr(r, "source_category", "") or "")] += 1
    return dict(sorted(c.items(), key=lambda kv: (-kv[1], kv[0])))


def _has_local_image(sp: Any) -> bool:
    imgs = sp.images or []
    if isinstance(imgs, str):
        try:
            imgs = json.loads(imgs)
        except Exception:
            imgs = [imgs]
    for img in imgs:
        if isinstance(img, str) and img and os.path.exists(img):
            return True
    return False


def _reason_bucket(msg: str) -> str:
    m = (msg or "").strip()
    if not m:
        return "UNKNOWN"
    prefixes = [
        "Missing images",
        "Missing enriched title",
        "Missing enriched description",
        "Missing title",
        "Missing/invalid cost price",
        "Missing category mapping",
        "Trust Violation",
        "Policy Violation",
        "Financial Danger",
    ]
    for p in prefixes:
        if m.startswith(p):
            return p
    if "UNPROFITABLE" in m.upper():
        return "UNPROFITABLE"
    return m.split(":")[0][:80]


def run(categories: list[CategoryRun]) -> dict[str, Any]:
    db_url = _ensure_db_url()

    from retail_os.core.database import SessionLocal, SupplierProduct, InternalProduct, init_db
    from retail_os.core.validator import LaunchLock
    from retail_os.core.marketplace_adapter import MarketplaceAdapter

    # Initialize schema + defaults.
    init_db()

    session = SessionLocal()
    try:
        # Ensure suppliers exist.
        oc = _supplier_row(session, "ONECHEQ", "https://onecheq.co.nz")
        nl = _supplier_row(session, "NOEL_LEEMING", "https://www.noelleeming.co.nz")
        supplier_id_by_name = {"ONECHEQ": int(oc.id), "NOEL_LEEMING": int(nl.id)}

        report: dict[str, Any] = {
            "started_at": _now(),
            "database_url": db_url,
            "runs": [],
            "totals": {},
        }

        # Track all SupplierProduct ids touched in this benchmark.
        touched_supplier_product_ids: set[int] = set()

        # --- SCRAPE ---
        for cat in categories:
            supplier = cat.supplier.upper().strip()
            supplier_id = supplier_id_by_name.get(supplier)
            if not supplier_id:
                report["runs"].append(
                    {
                        "supplier": supplier,
                        "source_category": cat.source_category,
                        "pages": cat.pages,
                        "deep_scrape": cat.deep_scrape,
                        "status": "SKIPPED",
                        "reason": "Unsupported supplier (pilot scope is ONECHEQ + NOEL_LEEMING)",
                    }
                )
                continue

            before_ids = {
                r[0]
                for r in session.query(SupplierProduct.id)
                .filter(SupplierProduct.supplier_id == supplier_id)
                .all()
            }

            t0 = time.perf_counter()
            scrape_err = None
            try:
                if supplier == "ONECHEQ":
                    from retail_os.scrapers.onecheq.adapter import OneCheqAdapter

                    OneCheqAdapter().run_sync(pages=int(cat.pages), collection=cat.source_category)
                else:
                    from retail_os.scrapers.noel_leeming.adapter import NoelLeemingAdapter

                    NoelLeemingAdapter().run_sync(
                        pages=int(cat.pages),
                        category_url=cat.source_category,
                        deep_scrape=bool(cat.deep_scrape),
                        headless=True,
                    )
            except Exception as e:
                scrape_err = str(e)
            dt = time.perf_counter() - t0

            # Refresh ids
            after_ids = {
                r[0]
                for r in session.query(SupplierProduct.id)
                .filter(SupplierProduct.supplier_id == supplier_id)
                .all()
            }
            new_ids = sorted(after_ids - before_ids)
            if new_ids:
                touched_supplier_product_ids.update(new_ids)

            report["runs"].append(
                {
                    "supplier": supplier,
                    "supplier_id": supplier_id,
                    "source_category": cat.source_category,
                    "pages": int(cat.pages),
                    "deep_scrape": bool(cat.deep_scrape),
                    "scrape_seconds": round(dt, 3),
                    "scrape_status": "FAILED" if scrape_err else "SUCCEEDED",
                    "scrape_error": scrape_err,
                    "scraped_new_supplier_products": len(new_ids),
                }
            )

        # If adapters updated existing rows but didn’t create new IDs, still benchmark “current” rows
        # in the categories we targeted.
        targeted_categories_by_supplier: dict[str, set[str]] = defaultdict(set)
        for cat in categories:
            targeted_categories_by_supplier[cat.supplier.upper()].add(cat.source_category)

        targeted_rows: list[Any] = []
        for supplier_name, cats in targeted_categories_by_supplier.items():
            sid = supplier_id_by_name.get(supplier_name)
            if not sid:
                continue
            q = session.query(SupplierProduct).filter(SupplierProduct.supplier_id == sid)
            # ONECHEQ uses handle in source_category; NL currently stores a value from scraper; best-effort filter.
            if cats:
                q = q.filter(SupplierProduct.source_category.in_(list(cats)))
            targeted_rows.extend(q.all())

        # --- ENRICH (deterministic) ---
        t0 = time.perf_counter()
        enriched_ok = 0
        enriched_fail = 0
        enrich_fail_reasons: Counter[str] = Counter()

        for sp in targeted_rows:
            try:
                md = MarketplaceAdapter.prepare_for_trademe(sp, use_ai=False)
                sp.enrichment_status = "SUCCESS"
                sp.enrichment_error = None
                sp.enriched_title = md["title"]
                sp.enriched_description = md["description"]
                enriched_ok += 1
            except Exception as e:
                sp.enrichment_status = "FAILED"
                sp.enrichment_error = str(e)
                enriched_fail += 1
                enrich_fail_reasons[_reason_bucket(str(e))] += 1
        session.commit()
        enrich_seconds = time.perf_counter() - t0

        # --- INTERNAL PRODUCT BOOTSTRAP ---
        t0 = time.perf_counter()
        created_internal = 0
        for sp in targeted_rows:
            ip = (
                session.query(InternalProduct)
                .filter(InternalProduct.primary_supplier_product_id == sp.id)
                .first()
            )
            if ip:
                continue
            # Deterministic, unique SKU
            supplier_name = (sp.supplier.name if getattr(sp, "supplier", None) else "SUP").upper()
            sku = f"{supplier_name}-{(sp.external_sku or '').strip()}"
            # Ensure uniqueness
            exists = session.query(InternalProduct).filter(InternalProduct.sku == sku).first()
            if exists:
                sku = f"{sku}-{sp.id}"
            ip = InternalProduct(
                sku=sku,
                title=(sp.enriched_title or sp.title or "").strip()[:255] or sku,
                primary_supplier_product_id=sp.id,
            )
            session.add(ip)
            created_internal += 1
        session.commit()
        internal_seconds = time.perf_counter() - t0

        # --- GATE CHECKS (publish readiness) ---
        t0 = time.perf_counter()
        validator = LaunchLock(session)
        ready = 0
        blocked = 0
        blocked_reasons: Counter[str] = Counter()

        # Only validate products for our targeted SupplierProducts.
        ips = (
            session.query(InternalProduct)
            .join(SupplierProduct, InternalProduct.primary_supplier_product_id == SupplierProduct.id)
            .filter(SupplierProduct.id.in_([sp.id for sp in targeted_rows]))
            .all()
        )
        for ip in ips:
            try:
                validator.validate_publish(ip, test_mode=False)
                ready += 1
            except Exception as e:
                blocked += 1
                blocked_reasons[_reason_bucket(str(e))] += 1
        gate_seconds = time.perf_counter() - t0

        # --- SUMMARY ---
        total_sp = len(targeted_rows)
        supplier_counts = Counter((sp.supplier.name if sp.supplier else "UNKNOWN") for sp in targeted_rows)
        with_local_img = sum(1 for sp in targeted_rows if _has_local_image(sp))
        with_price = sum(1 for sp in targeted_rows if float(sp.cost_price or 0) > 0)

        report["totals"] = {
            "targeted_supplier_products": total_sp,
            "by_supplier": dict(sorted(supplier_counts.items(), key=lambda kv: (-kv[1], kv[0]))),
            "by_source_category": _count_by_source_category(targeted_rows),
            "supplier_products_with_cost_price_gt_0": with_price,
            "supplier_products_with_local_image": with_local_img,
            "enrichment": {
                "seconds": round(enrich_seconds, 3),
                "success": enriched_ok,
                "failed": enriched_fail,
                "top_fail_reasons": enrich_fail_reasons.most_common(10),
            },
            "internal_products_created": created_internal,
            "internal_product_bootstrap_seconds": round(internal_seconds, 3),
            "launchlock": {
                "seconds": round(gate_seconds, 3),
                "ready_for_publish": ready,
                "blocked": blocked,
                "top_block_reasons": blocked_reasons.most_common(15),
            },
            "finished_at": _now(),
        }
        return report
    finally:
        session.close()


def _default_categories() -> list[CategoryRun]:
    # Small, real benchmark defaults (fast-ish). Override via env vars if desired.
    oc_pages = int(os.getenv("RETAILOS_BENCH_OC_PAGES", "1"))
    nl_pages = int(os.getenv("RETAILOS_BENCH_NL_PAGES", "1"))
    return [
        CategoryRun("ONECHEQ", os.getenv("RETAILOS_BENCH_OC_CATEGORY", "smartphones-and-mobilephones"), pages=oc_pages),
        CategoryRun("ONECHEQ", os.getenv("RETAILOS_BENCH_OC_CATEGORY_2", "laptops"), pages=oc_pages),
        CategoryRun(
            "NOEL_LEEMING",
            os.getenv("RETAILOS_BENCH_NL_CATEGORY", "https://www.noelleeming.co.nz/shop/computers-office-tech/computers"),
            pages=nl_pages,
            deep_scrape=False,
        ),
        CategoryRun(
            "NOEL_LEEMING",
            os.getenv("RETAILOS_BENCH_NL_CATEGORY_2", "https://www.noelleeming.co.nz/shop/phones-accessories/mobile-phones"),
            pages=nl_pages,
            deep_scrape=False,
        ),
    ]


if __name__ == "__main__":
    cats = _default_categories()
    out = run(cats)
    print(json.dumps(out, indent=2, sort_keys=True))
