"""
Marketplace Adapter.
The 'Clean Code' layer that finalizes a product for a specific marketplace (Trade Me).
Wraps Cleaning, SEO, and Categorization into a single endpoint.
"""

from typing import Dict, Any
import json
import os
from retail_os.core.category_mapper import CategoryMapper
from retail_os.utils.seo import build_seo_description
from retail_os.utils.cleaning import clean_title_for_trademe
from retail_os.strategy.pricing import PricingStrategy

class MarketplaceAdapter:
    
    @staticmethod
    def prepare_for_trademe(item: Any, use_ai: bool | None = None) -> Dict[str, Any]:
        """
        Takes a SupplierProduct (DB Object) and transforms it into a Retail-Ready Dictionary.
        Applies:
        - Title Cleaning
        - SEO Description Building
        - Category Mapping
        - Price Logic
        """
        
        # 1. Clean Title
        raw_title = item.title or "Untitled Product"
        final_title = clean_title_for_trademe(raw_title)
        
        # 2. Build Description (deterministic for pilot)
        # For OC/NL we do not call LLM. We treat enrichment output as the single source of truth.
        supplier_name = ""
        try:
            supplier_name = (item.supplier.name if getattr(item, "supplier", None) else "").upper()
        except Exception:
            supplier_name = ""

        # Default to deterministic unless explicitly forced.
        if use_ai is None:
            use_ai = False
        if supplier_name in {"ONECHEQ", "NOEL_LEEMING"}:
            use_ai = False

        from retail_os.utils.seo import clean_description
        clean_input = clean_description(item.description or "")

        # Remove dynamic boilerplate patterns
        from retail_os.core.boilerplate_detector import detector
        patterns = detector.detect_patterns()
        for p in patterns:
            if p in clean_input:
                clean_input = clean_input.replace(p, "")

        # Use enriched description if present; otherwise build deterministic SEO description.
        if getattr(item, "enriched_description", None):
            final_description = str(item.enriched_description)
        else:
            desc_input = {"title": raw_title, "description": clean_input, "specs": item.specs}
            final_description = build_seo_description(desc_input)
            from retail_os.core.standardizer import Standardizer
            final_description = Standardizer.polish(final_description)

        # Optional AI path (not used for OC/NL pilot)
        if use_ai:
            from retail_os.core.llm_enricher import enricher
            final_description = enricher.enrich(title=raw_title, raw_desc=clean_input, specs=item.specs or {})
        if item.specs and "**SPECIFICATIONS**" not in final_description:
             specs_block = "**SPECIFICATIONS**\n" + "\n".join([f"- {k}: {v}" for k, v in item.specs.items()])
             final_description = specs_block + "\n\n" + final_description

        # 3. Map Category
        cat_id = CategoryMapper.map_category(
            item.source_category if hasattr(item, 'source_category') else "", 
            raw_title
        )
        cat_name = CategoryMapper.get_category_name(cat_id)

        # 4. IMAGE AUDIT (Vision AI)
        from retail_os.core.image_guard import guard
        is_safe = True
        audit_reason = "Checked"
        
        # Prefer checking the first *local* image file path we have.
        # NOTE: ImageDownloader saves to data/media/<sku>.jpg (or <sku>_<n>.jpg).
        primary_img = None
        if getattr(item, "images", None):
            for img in item.images:
                if isinstance(img, str) and os.path.exists(img):
                    primary_img = img
                    break
        if primary_img:
            audit = guard.check_image(primary_img)
            is_safe = audit["is_safe"]
            audit_reason = audit.get("reason", "")
        elif guard.is_active():
            # Guard is active but we have no local image to analyze
            is_safe = False
            audit_reason = "No local image available for marketing-image audit"
        
        # Determine Final Trust Signal
        trust_signal = "HIGH"
        if not is_safe:
            trust_signal = "BANNED_IMAGE"

        # 5. Calculate Price (Strategy-Driven)
        # We need the supplier name. The Adapter is generic, so we might need to query it or infer it.
        # Ideally, SupplierProduct has '.supplier.name'. If relying on IDs, we need a DB lookup.
        # For efficiency in this specific function, we might pass it in, but to avoid signature change:
        # We assume 'item' is attached to a session or we use a fallback.
        
        supplier_name = None
        if hasattr(item, 'supplier') and item.supplier:
             supplier_name = item.supplier.name
        
        final_price = PricingStrategy.calculate_price(item.cost_price, cat_name, supplier_name)
        
        # 6. Return Ready Object
        return {
            "title": final_title,
            "description": final_description,
            "category_id": cat_id,
            "category_name": cat_name,
            "price": final_price, # MARGIN APPLIED HERE
            "original_title": raw_title,
            "original_description": item.description,
            "sku": item.external_sku,
            "trust_signal": trust_signal,
            "audit_reason": audit_reason
        }
