"""
Authoritative listing payload builder for RetailOS V2.
Used by preflight, dry run, and real publish to ensure consistency.
"""
import hashlib
import json
import os
from typing import Dict, Any, Optional
from retail_os.core.database import SessionLocal, InternalProduct
from retail_os.trademe.config import TradeMeConfig


def build_listing_payload(internal_product_id: int, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Build authoritative TradeMe listing payload.
    
    Args:
        internal_product_id: ID of InternalProduct
        overrides: Optional dict to override specific fields
        
    Returns:
        Complete listing payload dict ready for TradeMe API
    """
    session = SessionLocal()
    try:
        prod = session.query(InternalProduct).get(internal_product_id)
        if not prod or not prod.supplier_product:
            raise ValueError(f"Product {internal_product_id} not found or missing supplier data")
        
        sp = prod.supplier_product
        
        # Images (draft preview only)
        # Trade Me publishing uses PhotoIds (uploaded). Here we expose local/public URLs for operator visibility.
        photo_urls: list[str] = []
        if sp.images and isinstance(sp.images, list):
            for img in sp.images:
                if not isinstance(img, str) or not img:
                    continue
                norm = img.replace("\\", "/")
                if norm.startswith("http://") or norm.startswith("https://"):
                    photo_urls.append(norm)
                elif norm.startswith("data/media/"):
                    # Served by the API as /media/<file>
                    photo_urls.append("/media/" + norm[len("data/media/") :])
                elif os.path.exists(norm):
                    # Best effort: if it's a local path under data/media, still map to /media
                    low = norm.lower()
                    idx = low.rfind("/data/media/")
                    if idx != -1:
                        photo_urls.append("/media/" + norm[idx + len("/data/media/") :])

        from retail_os.core.marketplace_adapter import MarketplaceAdapter
        marketplace_data = MarketplaceAdapter.prepare_for_trademe(sp)
        
        # Build payload (match worker defaults)
        # NOTE: Trade Me v1 expects ints for Duration and bitflags for PaymentOptions.
        footer = (TradeMeConfig.listing_footer(session) or "").strip()
        desc = marketplace_data["description"]
        if footer:
            desc = f"{desc}\n\n{footer}"

        payload = {
            "Category": marketplace_data["category_id"],
            "Title": marketplace_data["title"][:49],
            "Description": [desc],
            "Duration": TradeMeConfig.DEFAULT_DURATION,
            "Pickup": TradeMeConfig.PICKUP_OPTION,
            # Default selling mode: auction with optional BuyNow matching StartPrice.
            "StartPrice": marketplace_data["price"],
            "BuyNowPrice": marketplace_data["price"],
            "PaymentOptions": TradeMeConfig.get_payment_methods(),
            "PhotoUrls": photo_urls,
            "PhotoIds": [],
            "HasGallery": len(photo_urls) > 0,
            # Metadata for tracking
            "_internal_product_id": internal_product_id,
            "_cost_price": float(sp.cost_price or 0),
            "_trust_signal": marketplace_data["trust_signal"]
        }

        # Shipping logic
        template_id = TradeMeConfig.shipping_template_id(session)
        if TradeMeConfig.use_shipping_template(session) and template_id:
            payload["Shipping"] = 3 # Specified shipping
            payload["ShippingTemplateId"] = int(template_id)
        else:
            payload["ShippingOptions"] = TradeMeConfig.DEFAULT_SHIPPING
        
        # Apply overrides
        if overrides:
            payload.update(overrides)
        
        return payload
        
    finally:
        session.close()


def compute_payload_hash(payload: Dict[str, Any]) -> str:
    """
    Compute deterministic hash of payload for comparison.
    Excludes PhotoIds and metadata fields.
    """
    # Create canonical version (exclude runtime fields)
    canonical = {k: v for k, v in payload.items() 
                 if not k.startswith('_') and k not in ['PhotoIds']}
    
    # Sort keys for deterministic JSON
    canonical_json = json.dumps(canonical, sort_keys=True)
    return hashlib.sha256(canonical_json.encode()).hexdigest()
