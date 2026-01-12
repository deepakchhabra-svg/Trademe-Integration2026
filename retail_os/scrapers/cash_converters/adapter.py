import os
import sys

# Ensure repo root is importable when running as a script from any cwd.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from typing import List
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import hashlib
import json

from retail_os.core.database import SessionLocal, Supplier, SupplierProduct, InternalProduct
from retail_os.utils.seo import build_seo_description

class CashConvertersAdapter:
    """
    Adapter for Cash Converters.
    Ref: Master Requirements Section 4 (Adapter & Normalisation).
    """
    
    def __init__(self):
        self.supplier_name = "CASH_CONVERTERS"
        self.db: Session = SessionLocal()
        
        # Ensure Supplier Exists
        supplier = self.db.query(Supplier).filter_by(name=self.supplier_name).first()
        if not supplier:
            supplier = Supplier(name=self.supplier_name, base_url="https://www.cashconverters.co.nz")
            self.db.add(supplier)
            self.db.commit()
        self.supplier_id = supplier.id

    def normalize_row(self, raw: dict) -> dict:
        """
        Maps Raw Scraper Dict -> Unified Schema Dict.
        """
        return {
            "source_listing_id": raw.get("source_id"),
            "title": raw.get("title"),
            "description": raw.get("description"),
            "brand": raw.get("brand") or (raw.get("specs") or {}).get("Brand") or "",
            "buy_now_price": raw.get("buy_now_price"),
            "source_url": raw.get("source_url"),
            "source_status": raw.get("source_status"),
            "images": [p for p in [raw.get("photo1"), raw.get("photo2"), raw.get("photo3"), raw.get("photo4")] if p],
            # Standard Fields
            "stock_level": raw.get("stock_level", 0),
            "condition": raw.get("condition") or (raw.get("specs") or {}).get("Condition") or "Used",
            "specs": raw.get("specs", {})  # CRITICAL: Pass specs to DB
        }


    def run_sync(
        self,
        pages: int = 1,
        browse_url: str = "https://shop.cashconverters.co.nz/Browse/R160787-R160789/North_Island-Auckland",
    ):
        print(f"CC Adapter: Starting Sync for {self.supplier_name}...")
        sync_start_time = datetime.now(timezone.utc)
        
        # 1. Discover product URLs
        from scripts.discover_category import discover_cash_converters_urls
        from retail_os.scrapers.cash_converters.scraper import scrape_single_item
        
        urls = discover_cash_converters_urls(browse_url, max_pages=pages)
        enhanced_items = []
        for url in urls:
            try:
                item = scrape_single_item(url)
                if item:
                    enhanced_items.append(item)
            except Exception as e:
                print(f"CC scrape failed for {url}: {e}")
        
        print(f"CC Adapter: Got {len(enhanced_items)} items with deep extraction. Processing...")
        
        count_updated = 0
        
        for item in enhanced_items:
            try:
                # 2. Normalize
                unified = self.normalize_row(item)
                unified["source_category"] = browse_url
                
                # 3. Validation
                if not unified["source_listing_id"] or not unified["title"]:
                    continue

                # 3.5 SEO Enhancement (Reusing Utils)
                unified["description"] = build_seo_description(unified)
                    
                # 4. Write to DB
                self._upsert_product(unified)
                count_updated += 1
                
            except Exception as e:
                print(f"CC Adapter Error on {item.get('source_id')}: {e}")
                
        print(f"CC Adapter: Sync Complete. Processed {count_updated} items.")
        
        # 5. Reconciliation
        from retail_os.core.reconciliation import ReconciliationEngine
        engine = ReconciliationEngine(self.db)
        
        # Step 2D: Safety Rails
        from retail_os.core.safety import SafetyGuard
        failed_count = len(enhanced_items) - count_updated
        
        if SafetyGuard.is_safe_to_reconcile(len(enhanced_items), failed_count):
             engine.process_orphans(self.supplier_id, sync_start_time)
        else:
             print("CC Adapter: Skipping Reconciliation due to Safety Guard.")
        
        self.db.close()

    def _upsert_product(self, data: dict):
        # Import downloader
        from retail_os.utils.image_downloader import ImageDownloader
        downloader = ImageDownloader()
        
        # Map Unified -> DB
        sku = data["source_listing_id"]
        # Supplier-native SKU should not include our prefix.
        supplier_sku = sku
        if isinstance(supplier_sku, str) and supplier_sku.startswith("CC-"):
            supplier_sku = supplier_sku.replace("CC-", "", 1)
        
        # Parse Price
        try:
            cost = float(data["buy_now_price"])
        except:
            cost = 0.0
            
        imgs = data.get("images", [])
        
        # PHYSICAL IMAGE DOWNLOAD (up to 4)
        local_images = []
        for idx, img_url in enumerate(imgs[:4], 1):
            img_sku = f"{sku}_{idx}" if idx > 1 else sku
            result = downloader.download_image(img_url, img_sku)
            if result["success"]:
                local_images.append(result["path"])
                print(f"   -> Downloaded image {idx}: {result['path']} ({result['size']} bytes)")
            else:
                print(f"   -> Image {idx} download failed: {result['error']}")
        
        # Calculate Snapshot Hash (include more fields so changes are detected)
        content = json.dumps(
            {
                "title": data.get("title"),
                "description": data.get("description"),
                "brand": data.get("brand"),
                "condition": data.get("condition"),
                "cost": cost,
                "status": data.get("source_status"),
                "images": local_images,
                "specs": data.get("specs") or {},
            },
            sort_keys=True,
            ensure_ascii=True,
        )
        current_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
        
        # DB Logic
        sp = self.db.query(SupplierProduct).filter_by(
            supplier_id=self.supplier_id, 
            external_sku=supplier_sku
        ).first()
        
        if not sp:
            # CREATE
            sp = SupplierProduct(
                supplier_id=self.supplier_id,
                external_sku=supplier_sku,
                title=data["title"],
                description=data["description"],
                brand=data.get("brand", ""),
                condition=data.get("condition", "Used"),
                cost_price=cost,
                stock_level=data.get("stock_level", 1),
                product_url=data["source_url"],
                images=local_images if local_images else imgs,  # Prefer local
                specs=data.get("specs", {}),
                source_category=data.get("source_category"),
                snapshot_hash=current_hash,
                last_scraped_at=datetime.now(timezone.utc)
            )
            self.db.add(sp)
            self.db.flush()
            
            # Auto-Create Internal
            # Prefix for Internal SKU
            my_sku = f"CC-{supplier_sku}"
            ip = self.db.query(InternalProduct).filter_by(sku=my_sku).first()
            if not ip:
                ip = InternalProduct(
                    sku=my_sku,
                    title=data["title"], # We use the same title initially
                    primary_supplier_product_id=sp.id
                )
                self.db.add(ip)
        else:
            # UPDATE
            sp.last_scraped_at = datetime.now(timezone.utc)
            # Always refresh category metadata even if content snapshot is unchanged.
            sp.source_category = data.get("source_category")
            if sp.snapshot_hash != current_hash:
                # Audit Logic
                from retail_os.core.database import AuditLog
                
                # Check Price Change
                if sp.cost_price != cost:
                    log = AuditLog(
                        entity_type="SupplierProduct",
                        entity_id=str(sp.id),
                        action="PRICE_CHANGE",
                        old_value=str(sp.cost_price),
                        new_value=str(cost),
                        user="System",
                        timestamp=datetime.now(timezone.utc)
                    )
                    self.db.add(log)
                    print(f"   -> Audited Price Change: {sp.cost_price} -> {cost}")

                # Check Title Change
                if sp.title != data["title"]:
                    log = AuditLog(
                        entity_type="SupplierProduct",
                        entity_id=str(sp.id),
                        action="TITLE_CHANGE",
                        old_value=sp.title,
                        new_value=data["title"],
                        user="System",
                        timestamp=datetime.now(timezone.utc)
                    )
                    self.db.add(log)

                sp.title = data["title"]
                sp.description = data.get("description", "")
                sp.brand = data.get("brand", "")
                sp.condition = data.get("condition", "Used")
                sp.cost_price = cost
                sp.images = local_images if local_images else imgs  # Prefer local
                sp.specs = data.get("specs", {})
                sp.snapshot_hash = current_hash
                
                self.db.commit()
                return 'updated'
            else:
                self.db.commit()
                return 'unchanged'
                
        self.db.commit()
        return 'created'

if __name__ == "__main__":
    adapter = CashConvertersAdapter()
    adapter.run_sync()
