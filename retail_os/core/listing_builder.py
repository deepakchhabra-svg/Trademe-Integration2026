"""
Authoritative listing payload builder for RetailOS V2.
Used by preflight, dry run, and real publish to ensure consistency.
"""
import hashlib
import json
from typing import Dict, Any, Optional
from retail_os.core.database import SessionLocal, InternalProduct
from retail_os.strategy.pricing import PricingStrategy
from retail_os.core.standardizer import Standardizer
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
        
        # Images (normalize URLs)
        photo_urls = []
        if sp.images:
            for img in (sp.images if isinstance(sp.images, list) else []):
                if isinstance(img, str):
                    if img:
                        if not img.startswith('http'):
                            img = 'https:' + img
                        photo_urls.append(img)

        from retail_os.core.marketplace_adapter import MarketplaceAdapter
        marketplace_data = MarketplaceAdapter.prepare_for_trademe(sp)
        
        # Build payload
        payload = {
            "Category": marketplace_data["category_id"],
            "Title": marketplace_data["title"][:49],
            "Description": [marketplace_data["description"]],
            "Duration": "Days7",
            "Pickup": 1,
            "BuyNowPrice": marketplace_data["price"],
            "PaymentOptions": [1, 2],
            "ShippingOptions": [],
            "PhotoUrls": photo_urls,
            "PhotoIds": [],
            "HasGallery": len(photo_urls) > 0,
            # Metadata for tracking
            "_internal_product_id": internal_product_id,
            "_cost_price": float(sp.cost_price or 0),
            "_trust_signal": marketplace_data["trust_signal"]
        }
        
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
