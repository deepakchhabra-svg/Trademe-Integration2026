import os
import sys

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

    def run_sync(self, pages: int = 1, collection: str = "all"):
        if pages <= 0:
            print(f"Adapter: [WARNING] UNLIMITED SYNC REQUESTED for {self.supplier_name}", file=sys.stderr)
            pages = 0  # Passes through to scraper's <=0 logic
            
        print(f"Adapter: Starting Sync for {self.supplier_name} (Pages={'UNLIMITED' if pages == 0 else pages}, Collection={collection})...")
        sync_start_time = datetime.utcnow()
        
        # 1. Get Raw Data
        concurrency = int(os.getenv("RETAILOS_ONECHEQ_CONCURRENCY", "8"))
        raw_items_gen = scrape_onecheq(limit_pages=pages, collection=collection, concurrency=concurrency)
        print(f"Adapter: Starting processing stream from scraper...")
        
        count_updated = 0
        
        count_total_scraped = 0
        
        for item in raw_items_gen:
            count_total_scraped += 1
            try:
                # 2. Normalize (Unified Schema)
                unified: UnifiedProduct = normalize_onecheq_row(item)

                # Category/collection partitioning (critical for 20k+ scale)
                # Store Shopify collection handle as supplier-native category.
                unified["source_category"] = collection
                
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
                self._upsert_product(unified)
                count_updated += 1
                
            except Exception as e:
                print(f"Adapter Error on {item.get('source_id')}: {e}")
                
        print(f"Adapter: Sync Complete. Scraped {count_total_scraped}, Processed {count_updated} items.")
        
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

    def _upsert_product(self, data: UnifiedProduct):
        # Import downloader
        from retail_os.utils.image_downloader import ImageDownloader
        downloader = ImageDownloader()
        
        # Map Unified -> DB
        sku = data["source_listing_id"]
        # Supplier-native SKU should not include our prefix.
        supplier_sku = sku
        if isinstance(supplier_sku, str) and supplier_sku.startswith("OC-"):
            supplier_sku = supplier_sku.replace("OC-", "", 1)
        
        # Parse Price
        try:
            cost = float(data["buy_now_price"])
        except:
            cost = 0.0
            
        # Collect Images
        imgs = []
        for k in ["photo1", "photo2", "photo3", "photo4"]:
            val = data.get(k)
            if val:
                imgs.append(val)

        # Pass through structured specs (from scraper)
        specs = data.get("specs") if isinstance(data, dict) else None
        if not isinstance(specs, dict):
            specs = {}
        
        # PHYSICAL IMAGE DOWNLOAD - Download all available images
        local_images = []
        limit_imgs = int(os.getenv("RETAILOS_IMAGE_LIMIT_PER_PRODUCT", "4") or "4")
        limit_imgs = max(0, min(4, limit_imgs))
        for idx, img_url in enumerate(imgs[:limit_imgs], 1):
            if img_url:
                # Use SKU with index for multiple images
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
                "specs": specs,
                "stock_level": data.get("stock_level"),
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
                stock_level=int(data.get("stock_level") or 1),
                product_url=data["source_url"],
                images=local_images if local_images else imgs,  # Prefer local
                specs=specs,
                collection_rank=data.get("collection_rank"),
                collection_page=data.get("collection_page"),
                source_category=data.get("source_category"),
                snapshot_hash=current_hash,
                last_scraped_at=datetime.utcnow()
            )
            self.db.add(sp)
            self.db.flush()
            
            # Auto-Create Internal
            my_sku = f"OC-{supplier_sku}"
            ip = self.db.query(InternalProduct).filter_by(sku=my_sku).first()
            if not ip:
                ip = InternalProduct(
                    sku=my_sku,
                    title=data["title"],
                    primary_supplier_product_id=sp.id
                )
                self.db.add(ip)
            else:
                # Self-Healing: Ensure Link is correct
                if ip.primary_supplier_product_id != sp.id:
                    print(f"   -> Fixing Broken Link for {my_sku}: {ip.primary_supplier_product_id} -> {sp.id}")
                    ip.primary_supplier_product_id = sp.id
        else:
            # UPDATE
            sp.last_scraped_at = datetime.utcnow()
            # Always refresh category/ranking metadata even if content snapshot is unchanged.
            # Otherwise older rows (or newly-added DB columns) never get populated.
            sp.source_category = data.get("source_category")
            sp.collection_rank = data.get("collection_rank")
            sp.collection_page = data.get("collection_page")
            
            if sp.snapshot_hash != current_hash:
                # Audit Logic
                from retail_os.core.database import AuditLog
                
                # Check Price Change
                if sp.cost_price != cost:
                    price_log = AuditLog(
                        entity_type="SupplierProduct",
                        entity_id=str(sp.id),
                        action="PRICE_CHANGE",
                        old_value=str(sp.cost_price),
                        new_value=str(cost),
                        user="System",
                        timestamp=datetime.utcnow()
                    )
                    self.db.add(price_log)
                    print(f"   -> Audited Price Change: {sp.cost_price} -> {cost}")

                # Check Title Change
                if sp.title != data["title"]:
                    title_log = AuditLog(
                        entity_type="SupplierProduct",
                        entity_id=str(sp.id),
                        action="TITLE_CHANGE",
                        old_value=sp.title,
                        new_value=data["title"],
                        user="System",
                        timestamp=datetime.utcnow()
                    )
                    self.db.add(title_log)

                # Commit Updates
                sp.title = data["title"]
                sp.description = data.get("description", "")
                sp.brand = data.get("brand", "")
                sp.condition = data.get("condition", "Used")
                sp.cost_price = cost
                sp.images = local_images if local_images else imgs  # Prefer local
                sp.specs = specs
                sp.collection_rank = data.get("collection_rank")
                sp.collection_page = data.get("collection_page")
                sp.snapshot_hash = current_hash
                
                self.db.commit()
                return 'updated'
            else:
                self.db.commit()
                return 'unchanged'

        self.db.commit()
        return 'created'


if __name__ == "__main__":
    adapter = OneCheqAdapter()
    adapter.run_sync(pages=1, collection="smartphones-and-mobilephones")
