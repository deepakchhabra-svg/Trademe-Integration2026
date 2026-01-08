import os
import sys

# NOTE: uses root logging configured by worker/uvicorn.
import logging

# Ensure repo root is importable when running as a script from any cwd.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from retail_os.core.database import SessionLocal, Supplier, SupplierProduct, InternalProduct
from retail_os.scrapers.onecheq.scraper import scrape_onecheq
from retail_os.core.unified_schema import normalize_onecheq_row, UnifiedProduct
from retail_os.utils.seo import build_seo_description
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed


class OneCheqAdapter:
    """
    Bridges the OneCheq Scraper and the Domain/DB Layer using Unified Schema.
    """
    
    def __init__(self):
        self.supplier_name = "ONECHEQ"
        self.db: Session = SessionLocal()
        
        # Ensure Supplier Exists
        supplier = self.db.query(Supplier).filter_by(name=self.supplier_name).first()
        if not supplier:
            supplier = Supplier(name=self.supplier_name, base_url="https://onecheq.co.nz")
            self.db.add(supplier)
            self.db.commit()
        self.supplier_id = supplier.id

    def run_sync(
        self,
        pages: int = 1,
        collection: str = "all",
        cmd_id: str | None = None,
        progress_every: int = 100,
        progress_hook=None,
        should_abort=None,
    ):
        if pages <= 0:
            print(f"Adapter: [WARNING] UNLIMITED SYNC REQUESTED for {self.supplier_name}", file=sys.stderr)
            pages = 0  # Passes through to scraper's <=0 logic
            
        print(f"Adapter: Starting Sync for {self.supplier_name} (Pages={'UNLIMITED' if pages == 0 else pages}, Collection={collection})...")
        sync_start_time = datetime.utcnow()
        t0 = datetime.utcnow()
        
        # 1. Get Raw Data
        concurrency = int(os.getenv("RETAILOS_ONECHEQ_CONCURRENCY", "1"))  # Reduced from 4 to 1 to prevent 429s
        raw_items_gen = scrape_onecheq(limit_pages=pages, collection=collection, concurrency=concurrency, cmd_id=cmd_id)
        print(f"Adapter: Starting processing stream from scraper...")
        
        count_updated = 0
        
        count_total_scraped = 0

        log = logging.getLogger(__name__)
        if progress_every <= 0:
            progress_every = 0

        # Best-effort total estimate for progress bars (honest: omit when unknown).
        total_estimate = None
        try:
            if pages and int(pages) > 0:
                json_limit = int(os.getenv("RETAILOS_ONECHEQ_JSON_LIMIT", "250") or "250")
                json_limit = max(1, min(250, json_limit))
                total_estimate = int(pages) * int(json_limit)
        except Exception:
            total_estimate = None
        
        for item in raw_items_gen:
            # Cooperative cancellation: allow the operator to cancel long runs.
            try:
                if should_abort and bool(should_abort()):
                    if cmd_id:
                        log.info(f"SCRAPE_ABORT cmd_id={cmd_id} supplier=ONECHEQ reason=CANCELLED_BY_OPERATOR")
                    return
            except Exception:
                # Never crash the scraper due to cancellation check failures.
                pass

            count_total_scraped += 1
            try:
                # 2. Normalize (Unified Schema)
                unified: UnifiedProduct = normalize_onecheq_row(item)

                # Category/collection partitioning (critical for 20k+ scale)
                # Preserve traversal context and/or derived membership from scraper.
                # - For /collections/all, the scraper derives a primary source_category from membership.
                # - For scoped runs, primary source_category remains the collection handle.
                unified["source_category"] = (item.get("source_category") or collection) if isinstance(item, dict) else collection
                if isinstance(item, dict) and item.get("source_categories") is not None:
                    unified["source_categories"] = item.get("source_categories")
                else:
                    unified["source_categories"] = [collection] if collection else []
                
                # 3. Validation
                if not unified["source_listing_id"] or not unified["title"]:
                    continue

                # 3.5 Keep supplier description raw.
                # MarketplaceAdapter/enrichment is responsible for producing listing-grade copy.
                # Pre-formatting here causes double-formatting and degraded output.
                
                # 3.6 Add ranking metadata
                unified["collection_rank"] = item.get("collection_rank")
                unified["collection_page"] = item.get("collection_page")
                    
                # 4. Write to DB
                self._upsert_product(unified, should_abort=should_abort, cmd_id=cmd_id, progress_hook=progress_hook)
                count_updated += 1
                
            except Exception as e:
                print(f"Adapter Error on {item.get('source_id')}: {e}")

            # Emit periodic progress for operator visibility (cmd_id-tagged so UI can tail it).
            if cmd_id and progress_every and (count_total_scraped % int(progress_every) == 0):
                try:
                    msg = (
                        f"SCRAPE_PROGRESS cmd_id={cmd_id} supplier=ONECHEQ collection={collection} "
                        f"scraped={count_total_scraped} upserted={count_updated}"
                    )
                    log.info(msg)
                except Exception:
                    pass
                try:
                    if progress_hook:
                        # ETA only when we have a total estimate
                        eta = None
                        try:
                            if total_estimate is not None:
                                elapsed = (datetime.utcnow() - t0).total_seconds()
                                rate = (count_total_scraped / elapsed) if elapsed > 0 else 0.0
                                if rate > 0:
                                    eta = int(round(max(total_estimate - count_total_scraped, 0) / rate))
                        except Exception:
                            eta = None
                        progress_hook(
                            {
                                "phase": "scrape",
                                "supplier": "ONECHEQ",
                                "collection": collection,
                                "scraped": int(count_total_scraped),
                                "upserted": int(count_updated),
                                "done": int(count_total_scraped),
                                "total": int(total_estimate) if total_estimate is not None else None,
                                "eta_seconds": eta,
                                "message": f"Scrape: {count_total_scraped} scraped ({count_updated} upserted)",
                            }
                        )
                except Exception:
                    pass
                
        print(f"Adapter: Sync Complete. Scraped {count_total_scraped}, Processed {count_updated} items.")

        # Final progress update
        if cmd_id:
            try:
                log.info(
                    f"SCRAPE_DONE cmd_id={cmd_id} supplier=ONECHEQ collection={collection} "
                    f"scraped={count_total_scraped} upserted={count_updated}"
                )
            except Exception:
                pass
            try:
                if progress_hook:
                    progress_hook(
                        {
                            "phase": "scrape",
                            "supplier": "ONECHEQ",
                            "collection": collection,
                            "scraped": int(count_total_scraped),
                            "upserted": int(count_updated),
                            "done": int(count_total_scraped),
                            "total": int(total_estimate) if total_estimate is not None else None,
                            "eta_seconds": 0 if total_estimate is not None else None,
                            "message": f"Scrape: {count_total_scraped} scraped ({count_updated} upserted)",
                            "finished": True,
                        }
                    )
            except Exception:
                pass
        
        # 5. Reconciliation (Handling Removals)
        from retail_os.core.reconciliation import ReconciliationEngine
        engine = ReconciliationEngine(self.db)
        
        # Step 2D: Safety Rails
        from retail_os.core.safety import SafetyGuard
        failed_count = count_total_scraped - count_updated
        
        # Safety Guard
        scrape_health_pct = (count_updated / count_total_scraped * 100) if count_total_scraped > 0 else 0
        print(f"SafetyGuard: Scrape Health = {scrape_health_pct:.1f}% ({count_updated}/{count_total_scraped})")
        
        if SafetyGuard.is_safe_to_reconcile(count_total_scraped, failed_count):
            # Fix: Check against sync_start_time. Any item not updated in this run is an orphan.
            engine.process_orphans(self.supplier_id, sync_start_time)
        else:
            print("Adapter: Skipping Reconciliation due to Safety Guard.")
        self.db.close()

    def _upsert_product(self, data: UnifiedProduct, should_abort=None, cmd_id: str | None = None, progress_hook=None):
        # Supplier-native SKU should not include our prefix.
        sku = data["source_listing_id"]
        supplier_sku = sku
        if isinstance(supplier_sku, str) and supplier_sku.startswith("OC-"):
            supplier_sku = supplier_sku.replace("OC-", "", 1)

        # Delegate to shared upserter
        # OneCheq uses "OC" as internal prefix.
        from retail_os.core.product_upserter import ProductUpserter
        upserter = ProductUpserter(self.db, self.supplier_id)
        
        return upserter.upsert(
            data=data,
            external_sku=supplier_sku,
            internal_sku_prefix="OC",
            should_abort=should_abort,
            progress_hook=progress_hook
        )

if __name__ == "__main__":
    adapter = OneCheqAdapter()
    adapter.run_sync(pages=1, collection="smartphones-and-mobilephones")
