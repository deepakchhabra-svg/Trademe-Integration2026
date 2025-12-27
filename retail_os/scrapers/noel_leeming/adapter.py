
import os
import sys

# Ensure repo root is importable when running as a script from any cwd.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from sqlalchemy.orm import Session
from datetime import datetime
import hashlib

from retail_os.core.database import SessionLocal, Supplier, SupplierProduct, InternalProduct
from retail_os.core.unified_schema import normalize_noel_leeming_row
from retail_os.scrapers.noel_leeming.scraper import scrape_category
from retail_os.utils.seo import build_seo_description

class NoelLeemingAdapter:
    """
    Adapter for Noel Leeming.
    """
    
    def __init__(self):
        self.supplier_name = "NOEL_LEEMING"
        self.db: Session = SessionLocal()
        
        # Ensure Supplier Exists
        supplier = self.db.query(Supplier).filter_by(name=self.supplier_name).first()
        if not supplier:
            supplier = Supplier(name=self.supplier_name, base_url="https://www.noelleeming.co.nz")
            self.db.add(supplier)
            self.db.commit()
        self.supplier_id = supplier.id

    def run_sync(
        self,
        pages: int = 1,
        category_url: str = "https://www.noelleeming.co.nz/shop/computers-office-tech/computers",
        deep_scrape: bool = False,
        headless: bool = True,
    ) -> None:
        print(f"NL Adapter: Starting Sync for {self.supplier_name}...")
        sync_start_time = datetime.utcnow()
        
        # 1. Scrape category pages (Selenium)
        raw_rows = scrape_category(
            headless=headless,
            max_pages=pages,
            category_url=category_url,
            deep_scrape=deep_scrape,
        )

        print(f"NL Adapter: Scraped {len(raw_rows)} rows. Normalizing/upserting...")

        count_updated = 0
        for row in raw_rows:
            try:
                unified = normalize_noel_leeming_row(row)

                # Build adapter-friendly dict
                data = {
                    "source_listing_id": unified.get("source_listing_id"),
                    "title": unified.get("title"),
                    "description": unified.get("description"),
                    "buy_now_price": unified.get("buy_now_price"),
                    "source_url": unified.get("source_url"),
                    "source_status": unified.get("source_status", "Active"),
                    "images": [p for p in [unified.get("photo1"), unified.get("photo2"), unified.get("photo3"), unified.get("photo4")] if p],
                    "stock_level": 1,
                    "specs": {},  # NL specs not extracted yet in this pipeline
                    # Category partitioning (prefer GTM category; fallback to configured category URL)
                    "source_category": unified.get("source_category") or category_url,
                }

                if not data["source_listing_id"] or not data["title"]:
                    continue

                # SEO enhancement (safe, deterministic)
                data["description"] = build_seo_description(
                    {"title": data["title"], "description": data["description"], "specs": data.get("specs", {})}
                )

                self._upsert_product(data)
                count_updated += 1
            except Exception as e:
                print(f"NL Adapter: row failed: {e}")

        print(f"NL Adapter: Sync Complete. Processed {count_updated} items.")

        # 2. Reconciliation (safe)
        from retail_os.core.reconciliation import ReconciliationEngine
        from retail_os.core.safety import SafetyGuard

        failed_count = len(raw_rows) - count_updated
        if SafetyGuard.is_safe_to_reconcile(len(raw_rows), failed_count):
            ReconciliationEngine(self.db).process_orphans(self.supplier_id, sync_start_time)
        else:
            print("NL Adapter: Skipping reconciliation (SafetyGuard).")

        self.db.close()
        
    def _upsert_product(self, data: dict) -> str:
        """
        Upserts a product into the database.
        Returns: 'created', 'updated', or 'unchanged'
        """
        # Import downloader
        from retail_os.utils.image_downloader import ImageDownloader
        downloader = ImageDownloader()
        
        # Map Unified -> DB
        sku = data["source_listing_id"]
        
        # Parse Price
        try:
            cost = float(data["buy_now_price"])
        except:
            cost = 0.0
            
        imgs = data.get("images", [])
        
        # DOWNLOADING
        local_images = []
        for idx, img_url in enumerate(imgs[:4], 1):
            img_sku = f"{sku}_{idx}" if idx > 1 else sku
            result = downloader.download_image(img_url, img_sku)
            if result["success"]:
                local_images.append(result["path"])
        
        # Calculate Snapshot Hash
        content = f"{data['title']}|{cost}|{data['source_status']}|{local_images}"
        current_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
        
        # DB Logic
        sp = self.db.query(SupplierProduct).filter_by(
            supplier_id=self.supplier_id, 
            external_sku=sku
        ).first()
        
        if not sp:
            # CREATE
            sp = SupplierProduct(
                supplier_id=self.supplier_id,
                external_sku=sku,
                title=data["title"],
                description=data["description"],
                cost_price=cost,
                stock_level=data.get("stock_level", 1),
                product_url=data["source_url"],
                images=local_images if local_images else imgs, 
                specs=data.get("specs", {}),
                source_category=data.get("source_category"),
                snapshot_hash=current_hash,
                last_scraped_at=datetime.utcnow()
            )
            self.db.add(sp)
            self.db.flush()
            
            # Auto-Create Internal
            my_sku = f"NL-{sku}"
            ip = self.db.query(InternalProduct).filter_by(sku=my_sku).first()
            if not ip:
                ip = InternalProduct(
                    sku=my_sku,
                    title=data["title"],
                    primary_supplier_product_id=sp.id
                )
                self.db.add(ip)
            
            self.db.commit()
            return 'created'
            
        else:
            # UPDATE
            sp.last_scraped_at = datetime.utcnow()
            # Always refresh category metadata even if snapshot is unchanged.
            sp.source_category = data.get("source_category")
            if sp.snapshot_hash != current_hash:
                # Audit Logic would go here
                
                sp.title = data["title"]
                sp.cost_price = cost
                sp.images = local_images if local_images else imgs
                sp.specs = data.get("specs", {})
                sp.snapshot_hash = current_hash
                
                self.db.commit()
                return 'updated'
            else:
                self.db.commit()
                return 'unchanged'

if __name__ == "__main__":
    adapter = NoelLeemingAdapter()
    adapter.run_sync()
