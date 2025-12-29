"""
Background Enrichment Worker
Processes PENDING products and marks them SUCCESS or FAILED.
Run this separately from the dashboard.
"""
import time
import sys
import os
sys.path.append(os.getcwd())

from typing import Optional

from retail_os.core.database import SessionLocal, SupplierProduct, SystemSetting
from retail_os.core.marketplace_adapter import MarketplaceAdapter


def _get_enrichment_policy(db) -> dict:
    """
    SystemSetting key: `enrichment.policy`
    Value shape:
      {
        "default": "NONE" | "TEMPLATE" | "AI",
        "by_supplier": {
           "CASH_CONVERTERS": "AI",
           "NOEL_LEEMING": "NONE",
           "ONECHEQ": "NONE"
        }
      }
    """
    default_policy = {
        # Pilot requirement: deterministic enrichment (no LLM) unless explicitly enabled.
        "default": "NONE",
        "by_supplier": {
            "ONECHEQ": "NONE",
            "NOEL_LEEMING": "NONE",
            # CASH_CONVERTERS intentionally out of scope for pilot
            "CASH_CONVERTERS": "NONE",
        },
    }
    row = db.query(SystemSetting).filter(SystemSetting.key == "enrichment.policy").first()
    if not row or not isinstance(row.value, dict):
        return default_policy
    merged = {**default_policy, **row.value}
    if "by_supplier" in row.value and isinstance(row.value["by_supplier"], dict):
        merged["by_supplier"] = {**default_policy["by_supplier"], **row.value["by_supplier"]}
    return merged


def _build_minimal_template(title: str, specs: dict) -> str:
    """
    Deterministic, premium-minimal template. No hallucinations: uses only known specs.
    """
    title_lower = title.lower()
    if any(word in title_lower for word in ["ring", "pendant", "necklace", "bracelet", "earring"]):
        intro = f"Minimal, premium piece: {title}."
    elif any(word in title_lower for word in ["laptop", "computer", "tablet", "phone", "ipad", "macbook"]):
        intro = f"Minimal, premium device: {title}."
    else:
        intro = f"Minimal, premium item: {title}."

    parts = [intro, ""]

    if specs:
        parts.append("**Specifications**")
        for k, v in list(specs.items())[:10]:
            parts.append(f"• **{str(k).replace('_', ' ').title()}**: {v}")
        parts.append("")

    parts.append("**Condition & Inclusions**")
    condition = specs.get("Condition", specs.get("condition", "See listing details"))
    parts.append(f"Condition: {condition}")
    parts.append("")
    parts.append("**Notes**")
    parts.append("Please review the specifications carefully before purchase.")
    return "\n".join(parts)

def enrich_batch(batch_size: int = 10, delay_seconds: int = 5, supplier_id: Optional[int] = None, source_category: Optional[str] = None):
    """
    Process a batch of pending products.
    
    Args:
        batch_size: How many to process in one run
        delay_seconds: Delay between items to respect rate limits
        supplier_id: Optional supplier scope
        source_category: Optional category/collection scope within supplier
    """
    db = SessionLocal()
    
    try:
        policy = _get_enrichment_policy(db)

        # Get pending products
        # Get pending products
        # Prioritize Priority 1 items (Noel Leeming has collection_rank > 0)
        # Then newest items first
        from sqlalchemy import desc
        
        q = db.query(SupplierProduct).filter(
            SupplierProduct.enrichment_status == "PENDING",
            SupplierProduct.cost_price > 0  # Skip invalid prices
        )

        if supplier_id is not None:
            q = q.filter(SupplierProduct.supplier_id == int(supplier_id))

        if source_category:
            q = q.filter(SupplierProduct.source_category == source_category)

        # Eager load supplier to avoid extra queries per row (and to apply supplier policy)
        from sqlalchemy.orm import joinedload
        pending = q.options(joinedload(SupplierProduct.supplier)).order_by(
            SupplierProduct.collection_rank.asc(), # Low rank number = High priority
            SupplierProduct.last_scraped_at.desc()
        ).limit(batch_size).all()
        
        if not pending:
            print("No pending products to enrich")
            return
        
        print(f"Processing {len(pending)} products...")
        
        for item in pending:
            try:
                print(f"  Processing {item.external_sku}...")

                supplier_name = (item.supplier.name if getattr(item, "supplier", None) else "").upper()
                mode = (policy.get("by_supplier", {}).get(supplier_name) or policy.get("default") or "NONE").upper()
                if supplier_name in {"ONECHEQ", "NOEL_LEEMING"}:
                    mode = "NONE"

                if mode == "AI":
                    # AI mode is not used for OC/NL pilot; if enabled explicitly, it must fail loudly.
                    result = MarketplaceAdapter.prepare_for_trademe(item, use_ai=True)
                    item.enrichment_status = "SUCCESS"
                    item.enrichment_error = None
                    item.enriched_title = result["title"]
                    item.enriched_description = result["description"]
                    print("    SUCCESS (AI)")

                elif mode == "TEMPLATE":
                    # No LLM calls even if key exists.
                    result = MarketplaceAdapter.prepare_for_trademe(item, use_ai=False)
                    title = result["title"]
                    item.enriched_title = title
                    item.enriched_description = _build_minimal_template(title=title, specs=item.specs or {})
                    item.enrichment_status = "SUCCESS"
                    item.enrichment_error = None
                    print("    SUCCESS (TEMPLATE)")

                else:
                    # NONE = heuristic-only (SEO + Standardizer), no LLM calls.
                    result = MarketplaceAdapter.prepare_for_trademe(item, use_ai=False)
                    item.enrichment_status = "SUCCESS"
                    item.enrichment_error = None
                    item.enriched_title = result["title"]
                    item.enriched_description = result["description"]
                    print("    SUCCESS (NONE)")
                
                db.commit()
                
                # Rate limit protection
                if delay_seconds and delay_seconds > 0:
                    time.sleep(delay_seconds)
                
            except Exception as e:
                item.enrichment_status = "FAILED"
                item.enrichment_error = str(e)
                db.commit()
                print(f"    ERROR: {e}")
        
        print(f"Batch complete")
        
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    
    batch_size = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    delay = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    supplier_id = int(sys.argv[3]) if len(sys.argv) > 3 else None
    source_category = sys.argv[4] if len(sys.argv) > 4 else None
    
    print(f"Starting enrichment worker")
    print(f"   Batch size: {batch_size}")
    print(f"   Delay: {delay}s between items")
    print()
    
    enrich_batch(batch_size=batch_size, delay_seconds=delay, supplier_id=supplier_id, source_category=source_category)
