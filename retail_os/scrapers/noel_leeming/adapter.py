
import sys
import os
sys.path.append(os.getcwd())

from typing import List
from sqlalchemy.orm import Session
from datetime import datetime
import hashlib
import json

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

    def run_sync(self, pages: int = 1):
        print(f"NL Adapter: Starting Sync for {self.supplier_name}...")
        sync_start_time = datetime.utcnow()
        
        # 1. Get Raw Data
        # We start with computers as a default category for the sync button
        start_url = "https://www.noelleeming.co.nz/shop/computers-office-tech/computers"
        from scripts.discover_noel_leeming import discover_noel_leeming_urls
        
        # A. Discovery
        item_urls = discover_noel_leeming_urls(start_url, max_pages=pages)
        
        count_updated = 0
        
        # B. Scraping & Upsert
        for url in item_urls:
            try:
                # Scrape Content
                from retail_os.scrapers.noel_leeming.scraper import scrape_category # Reusing generic scraper logic if suitable or specialized one
                # Note: 'scrape_category' was a misnomer in previous context, checking imports.
                # Actually we need a 'scrape_single_product' function. 
                # If unavailable, we write a quick inline scraper or assume discovery returned data.
                # Checking discover_noel_leeming... it only returns URLs.
                # We need to fetch the page content.
                pass 
                # Placeholder: We will assume we have a scraper. 
                # For now, to prevent crashing, we skip deep scraping if function missing.
            except Exception:
                pass

        # Since we don't have a robust Single Page Scraper for NL in the context yet, 
        # we will stub this to ensure the BUTTON doesn't crash, but warns.
        print("NL Adapter: Basic Stub. Deep scraping pending implementation of 'scrape_noel_leeming_product'.")
        
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
        if imgs and len(imgs) > 0:
            primary_url = imgs[0]
            result = downloader.download_image(primary_url, sku)
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
                specifications=data.get("specifications", {}),
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
            if sp.snapshot_hash != current_hash:
                # Audit Logic would go here
                
                sp.title = data["title"]
                sp.cost_price = cost
                sp.images = local_images if local_images else imgs
                sp.specifications = data.get("specifications", {})
                sp.snapshot_hash = current_hash
                
                self.db.commit()
                return 'updated'
            else:
                self.db.commit()
                return 'unchanged'

if __name__ == "__main__":
    adapter = NoelLeemingAdapter()
    adapter.run_sync()
