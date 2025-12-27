import sys
import os
import shutil
import subprocess
import re
from urllib.parse import urlparse
from datetime import datetime
import hashlib
from typing import Optional

sys.path.append(os.getcwd())

from bs4 import BeautifulSoup

from retail_os.core.database import SessionLocal, Supplier, SupplierProduct, InternalProduct
from retail_os.utils.seo import build_seo_description

class UniversalAdapter:
    """
    The 'Quick Add' Mechanism.
    Attempts to import ANY product URL using OpenGraph / Schema.org metadata.
    Ref: Master Requirements Level 1 'Add any other supplier'.
    """
    
    def __init__(self):
        self.db = SessionLocal()

    def _get_html_via_curl(self, url: str) -> str:
        """
        Bypassing 403s using system curl.
        """
        curl_path = shutil.which("curl")
        if not curl_path:
            raise Exception("CURL not found in system path.")
            
        cmd = [
            curl_path,
            "-L", # Follow redirects
            "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            url
        ]
        
        # Run
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        if result.returncode != 0:
            raise Exception(f"CURL Failed: {result.stderr}")
            
        return result.stdout

    def _extract_domain_as_supplier(self, url: str) -> int:
        """
        Extracts 'thewarehouse' from 'https://www.thewarehouse.co.nz/...'
        Creates Supplier if needed.
        Returns: supplier_id
        """
        parsed = urlparse(url)
        domain = parsed.netloc # www.thewarehouse.co.nz
        # Remove www.
        if domain.startswith("www."):
            domain = domain[4:]
        
        # Identifier: THEWAREHOUSE_CO_NZ -> THEWAREHOUSE
        parts = domain.split('.')
        name_candidate = parts[0].upper()
        
        # Check DB
        supplier = self.db.query(Supplier).filter_by(name=name_candidate).first()
        if not supplier:
            print(f"Universal: Created New Supplier '{name_candidate}'")
            supplier = Supplier(name=name_candidate, base_url=f"{parsed.scheme}://{parsed.netloc}")
            self.db.add(supplier)
            self.db.commit()
            
        return supplier.id

    def analyze_url(self, url: str) -> dict:
        """
        Fetches and extracts metadata from a URL without saving to DB.
        Useful for Validation Gates.
        """
        print(f"Universal: analyzing {url}...")
        
        # 1. Fetch
        html = self._get_html_via_curl(url)
        if not BeautifulSoup:
            # Fallback if bs4 missing (unlikely in prod)
            return {}
            
        soup = BeautifulSoup(html, "html.parser")
        
        # 2. Extract Metadata (Open Graph Strategy)
        og_title = soup.find("meta", property="og:title")
        og_image = soup.find("meta", property="og:image")
        og_desc = soup.find("meta", property="og:description")
        og_price = soup.find("meta", property="product:price:amount")
        
        title = og_title["content"] if og_title else soup.title.string if soup.title else "Unknown Product"
        image_url = og_image["content"] if og_image else None
        description = og_desc["content"] if og_desc else ""
        
        price = 0.0
        if og_price:
            try:
                price = float(og_price["content"])
            except:
                pass
                
        return {
            "title": title,
            "description": description,
            "price": price,
            "image_url": image_url,
            "url": url
        }

    def import_url(self, url: str) -> str:
        """
        Main Entry Point. Import a single URL.
        Returns: Product Title.
        """
        data = self.analyze_url(url)
        if not data:
            raise Exception("Analysis Failed")
            
        # 3. Create Supplier
        supplier_id = self._extract_domain_as_supplier(url)
        
        # 4. Generate SKU (Hash of URL)
        url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()[:8]
        sku = f"UNIV-{url_hash}"
        
        # 5. Upsert SupplierProduct
        sp = self.db.query(SupplierProduct).filter_by(supplier_id=supplier_id, external_sku=sku).first()
        
        imgs = [data["image_url"]] if data.get("image_url") else []
        
        if not sp:
            sp = SupplierProduct(
                supplier_id=supplier_id,
                external_sku=sku,
                title=data["title"],
                description=data["description"],
                cost_price=data.get("price", 0.0),
                stock_level=1, # Assume 1 for single import
                product_url=url,
                images=imgs,
                snapshot_hash=url_hash,
                last_scraped_at=datetime.utcnow()
            )
            self.db.add(sp)
            self.db.flush()
            
            # 6. Create InternalProduct
            ip = self.db.query(InternalProduct).filter_by(sku=sku).first()
            if not ip:
                ip = InternalProduct(
                    sku=sku,
                    title=data["title"],
                    primary_supplier_product_id=sp.id
                )
                self.db.add(ip)
                
            self.db.commit()
            return data["title"]
        else:
            return f"Existing: {sp.title}"

if __name__ == "__main__":
    ua = UniversalAdapter()
    # Test with a known URL if running directly
    # ua.import_url("...")
