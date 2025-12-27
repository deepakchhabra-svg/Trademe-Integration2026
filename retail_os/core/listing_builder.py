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
        
        # Title (max 49 chars for TradeMe) - already cleaned by scraper
        title = (sp.title or prod.title or "Product")[:49]
        
        # Description (prefer enriched, fallback to raw)
        description = sp.enriched_description or sp.description or "Listing created by RetailOS."
        description += "\\n\\n(Automated Listing via RetailOS)"
        
        # Pricing
        cost_price = float(sp.cost_price) if sp.cost_price else 0
        listing_price = cost_price * 1.15 if cost_price > 0 else 10.0
        
        # Category (use default - no category_mapping field exists)
        category_id = "0350-6076-6080-"  # Default general category
        
        # Images (normalize URLs)
        photo_urls = []
        if sp.images:
            for img in (sp.images if isinstance(sp.images, list) else []):
                if isinstance(img, str):
                    if img:
                        if not img.startswith('http'):
                            img = 'https:' + img
                        photo_urls.append(img)
        
        # Build payload with valid leaf category
        # Buy Now only (no StartPrice) = NO LISTING FEE per TradeMe policy
        payload = {
            "Category": "0187-0192-",  # Home & Garden > Other (valid leaf category)
            "Title": title,
            "Description": [description],
            "Duration": "Days7",
            "Pickup": 1,
            "BuyNowPrice": listing_price,  # Buy Now only = fee-free
            "PaymentOptions": [1, 2],
            "ShippingOptions": [],
            "PhotoUrls": photo_urls,
            "PhotoIds": [],
            "HasGallery": len(photo_urls) > 0,
            # Metadata for tracking
            "_internal_product_id": internal_product_id,
            "_cost_price": cost_price,
            "_margin_percent": ((listing_price - cost_price) / cost_price * 100) if cost_price > 0 else 0
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
