import os
import json
import hashlib
from datetime import datetime
from typing import Optional, Callable
from sqlalchemy.orm import Session
from retail_os.core.database import SupplierProduct, InternalProduct, AuditLog
from retail_os.core.unified_schema import UnifiedProduct
from retail_os.utils.image_downloader import ImageDownloader
from concurrent.futures import ThreadPoolExecutor, as_completed

class ProductUpserter:
    """
    Shared logic for upserting UnifiedProduct data into SupplierProduct and InternalProduct tables.
    Handles:
    - Image downloading
    - Snapshot hashing
    - Data mapping
    - Audit logging
    - InternalProduct linking
    """
    def __init__(self, db: Session, supplier_id: int):
        self.db = db
        self.supplier_id = supplier_id
        self.downloader = ImageDownloader()

    def upsert(
        self, 
        data: UnifiedProduct, 
        external_sku: str, 
        internal_sku_prefix: str,
        should_abort: Optional[Callable[[], bool]] = None, 
        progress_hook: Optional[Callable[[dict], None]] = None
    ) -> str:
        
        # Parse Price
        try:
            cost = float(data["buy_now_price"])
        except (ValueError, TypeError):
            cost = 0.0

        # Stock / availability
        stock_raw = data.get("stock_level")
        stock_level: Optional[int] = None
        try:
            if stock_raw is not None:
                stock_level = int(stock_raw)
        except (ValueError, TypeError):
            stock_level = None
            
        # Collect Images from data
        imgs = []
        for k in ["photo1", "photo2", "photo3", "photo4"]:
            val = data.get(k)
            if val:
                imgs.append(val)

        # Pass through structured specs
        specs = data.get("specs") if isinstance(data.get("specs"), dict) else {}
        
        # PHYSICAL IMAGE DOWNLOAD
        local_images = self._download_images(imgs, external_sku, should_abort)
        
        # Calculate Snapshot Hash
        # Include fields relevant for change detection
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
            external_sku=external_sku
        ).first()
        
        if not sp:
            return self._create_product(
                data, external_sku, internal_sku_prefix, cost, stock_level, 
                local_images, imgs, specs, current_hash
            )
        else:
            return self._update_product(
                sp, data, cost, stock_level, local_images, imgs, specs, current_hash
            )

    def _download_images(self, imgs: list[str], sku: str, should_abort: Optional[Callable[[], bool]]) -> list[str]:
        local_images = []
        limit_imgs = int(os.getenv("RETAILOS_IMAGE_LIMIT_PER_PRODUCT", "4") or "4")
        limit_imgs = max(0, min(4, limit_imgs))
        img_conc = int(os.getenv("RETAILOS_IMAGE_CONCURRENCY_PER_PRODUCT", "4") or "4")
        img_conc = max(1, min(8, img_conc))

        if limit_imgs <= 0:
            return []

        tasks = []
        for idx, img_url in enumerate(imgs[:limit_imgs], 1):
            if not img_url:
                continue
            img_sku = f"{sku}_{idx}" if idx > 1 else sku
            tasks.append((idx, img_url, img_sku))

        if tasks:
            with ThreadPoolExecutor(max_workers=min(img_conc, len(tasks))) as ex:
                def _dl(t):
                    i, u, s = t
                    return i, self.downloader.download_image(u, s, should_abort=should_abort)

                futs = [ex.submit(_dl, t) for t in tasks]
                for fut in as_completed(futs):
                    # Cooperative cancellation
                    try:
                        if should_abort and should_abort():
                            break
                    except Exception:
                        pass

                    idx, result = fut.result()
                    if result.get("success"):
                        local_images.append(result.get("path"))
        
        # Preserve cleanup/ordering if needed, here just returning what succeeded
        return [p for p in local_images if p]

    def _create_product(
        self, data: UnifiedProduct, external_sku: str, internal_prefix: str, 
        cost: float, stock_level: Optional[int], local_images: list[str], 
        original_images: list[str], specs: dict, current_hash: str
    ) -> str:
        sp = SupplierProduct(
            supplier_id=self.supplier_id,
            external_sku=external_sku,
            title=data["title"],
            description=data.get("description", ""),
            brand=data.get("brand", ""),
            condition=data.get("condition", "Used"),
            cost_price=cost,
            stock_level=stock_level,
            product_url=data["source_url"],
            images=local_images if local_images else original_images,  # Prefer local
            specs=specs,
            collection_rank=data.get("collection_rank"),
            collection_page=data.get("collection_page"),
            source_category=data.get("source_category"),
            source_categories=data.get("source_categories"),
            snapshot_hash=current_hash,
            last_scraped_at=datetime.utcnow()
        )
        self.db.add(sp)
        self.db.flush()
        
        # Auto-Create Internal
        my_sku = f"{internal_prefix}-{external_sku}" if internal_prefix else external_sku
        ip = self.db.query(InternalProduct).filter_by(sku=my_sku).first()
        if not ip:
            ip = InternalProduct(
                sku=my_sku,
                title=data["title"],
                primary_supplier_product_id=sp.id
            )
            self.db.add(ip)
        else:
            # Self-Healing
            if ip.primary_supplier_product_id != sp.id:
                print(f"   -> Fixing Broken Link for {my_sku}: {ip.primary_supplier_product_id} -> {sp.id}")
                ip.primary_supplier_product_id = sp.id
                
        self.db.commit()
        return 'created'

    def _update_product(
        self, sp: SupplierProduct, data: UnifiedProduct, cost: float, 
        stock_level: Optional[int], local_images: list[str], original_images: list[str], 
        specs: dict, current_hash: str
    ) -> str:
        sp.last_scraped_at = datetime.utcnow()
        # Always refresh category/ranking metadata
        sp.source_category = data.get("source_category")
        sp.source_categories = data.get("source_categories")
        sp.collection_rank = data.get("collection_rank")
        sp.collection_page = data.get("collection_page")
        
        if sp.snapshot_hash != current_hash:
            # Audit Logic
            if sp.cost_price != cost:
                self.db.add(AuditLog(
                    entity_type="SupplierProduct",
                    entity_id=str(sp.id),
                    action="PRICE_CHANGE",
                    old_value=str(sp.cost_price),
                    new_value=str(cost),
                    user="System",
                    timestamp=datetime.utcnow()
                ))

            if sp.title != data["title"]:
                self.db.add(AuditLog(
                    entity_type="SupplierProduct",
                    entity_id=str(sp.id),
                    action="TITLE_CHANGE",
                    old_value=sp.title,
                    new_value=data["title"],
                    user="System",
                    timestamp=datetime.utcnow()
                ))

            # Commit Updates
            sp.title = data["title"]
            sp.description = data.get("description", "")
            sp.brand = data.get("brand", "")
            sp.condition = data.get("condition", "Used")
            sp.cost_price = cost
            sp.stock_level = stock_level
            sp.images = local_images if local_images else original_images
            sp.specs = specs
            sp.snapshot_hash = current_hash
            
            self.db.commit()
            return 'updated'
        else:
            self.db.commit()
            return 'unchanged'
