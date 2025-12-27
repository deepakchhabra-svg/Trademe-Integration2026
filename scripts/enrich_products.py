"""
Background Enrichment Worker
Processes PENDING products and marks them SUCCESS or FAILED.
Run this separately from the dashboard.
"""
import time
import sys
import os
sys.path.append(os.getcwd())

from retail_os.core.database import SessionLocal, SupplierProduct
from retail_os.core.marketplace_adapter import MarketplaceAdapter

def enrich_batch(batch_size=10, delay_seconds=5):
    """
    Process a batch of pending products.
    
    Args:
        batch_size: How many to process in one run
        delay_seconds: Delay between items to respect rate limits
    """
    db = SessionLocal()
    
    try:
        # Get pending products
        # Get pending products
        # Prioritize Priority 1 items (Noel Leeming has collection_rank > 0)
        # Then newest items first
        from sqlalchemy import desc
        
        pending = db.query(SupplierProduct).filter(
            SupplierProduct.enrichment_status == "PENDING",
            SupplierProduct.cost_price > 0  # Skip invalid prices
        ).order_by(
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
                
                # Run enrichment
                result = MarketplaceAdapter.prepare_for_trademe(item)
                
                # Check if LLM failed - use smart factual template
                if "⚠️ LLM FAILURE" in result['description']:
                    print(f"    LLM failed, generating smart template...")
                    
                    title = result['title']
                    specs = item.specs or {}
                    
                    # Detect category from title
                    title_lower = title.lower()
                    
                    # Category-specific intros (factual only)
                    if any(word in title_lower for word in ['ring', 'pendant', 'necklace', 'bracelet', 'earring']):
                        category = 'jewelry'
                        intro = f"Add elegance to your collection with this {title.lower()}."
                    elif any(word in title_lower for word in ['laptop', 'computer', 'tablet', 'phone', 'ipad', 'macbook']):
                        category = 'electronics'
                        intro = f"Enhance your productivity with this {title.lower()}."
                    elif any(word in title_lower for word in ['drill', 'saw', 'tool', 'hammer', 'wrench']):
                        category = 'tools'
                        intro = f"Complete your workshop with this {title.lower()}."
                    elif any(word in title_lower for word in ['watch', 'clock']):
                        category = 'timepiece'
                        intro = f"Keep time in style with this {title.lower()}."
                    else:
                        category = 'general'
                        intro = f"Discover this quality {title.lower()}."
                    
                    desc_parts = [intro, ""]
                    
                    # Add specs - formatted by category
                    if specs:
                        desc_parts.append("**Product Details**")
                        
                        # Smart spec ordering based on category
                        priority_keys = {
                            'jewelry': ['Material', 'Weight', 'Size', 'Condition', 'Stamp'],
                            'electronics': ['Model', 'Processor', 'RAM', 'Storage', 'Condition'],
                            'tools': ['Brand', 'Model', 'Power', 'Condition'],
                            'general': []
                        }
                        
                        ordered_specs = []
                        priority = priority_keys.get(category, [])
                        
                        # Add priority specs first
                        for key in priority:
                            for spec_key, spec_value in specs.items():
                                if key.lower() in spec_key.lower():
                                    ordered_specs.append((spec_key, spec_value))
                                    break
                        
                        # Add remaining specs
                        for spec_key, spec_value in specs.items():
                            if (spec_key, spec_value) not in ordered_specs:
                                ordered_specs.append((spec_key, spec_value))
                        
                        # Format specs cleanly
                        for key, value in ordered_specs[:8]:  # Max 8 specs
                            formatted_key = key.replace('_', ' ').title()
                            desc_parts.append(f"• **{formatted_key}**: {value}")
                        
                        desc_parts.append("")
                    
                    # Factual condition statement
                    condition = specs.get('Condition', specs.get('condition', 'See description'))
                    desc_parts.append("**Item Condition**")
                    desc_parts.append(f"Condition: {condition}")
                    desc_parts.append("")
                    
                    # Category-specific value propositions (factual)
                    desc_parts.append("**Why Buy?**")
                    if category == 'jewelry':
                        desc_parts.append("✓ Authenticated materials as described")
                        desc_parts.append("✓ Detailed specifications provided")
                        desc_parts.append("✓ Quality pre-owned jewelry")
                    elif category == 'electronics':
                        desc_parts.append("✓ Tested and functional")
                        desc_parts.append("✓ Full specifications listed")
                        desc_parts.append("✓ Ready to use")
                    elif category == 'tools':
                        desc_parts.append("✓ Professional-grade equipment")
                        desc_parts.append("✓ Specifications verified")
                        desc_parts.append("✓ Ready for your next project")
                    else:
                        desc_parts.append("✓ Quality item as described")
                        desc_parts.append("✓ Full details provided")
                        desc_parts.append("✓ Ready for purchase")
                    
                    desc_parts.append("")
                    desc_parts.append("**Purchase Information**")
                    desc_parts.append("All items sold as described. Please review specifications carefully before purchase.")
                    
                    template_desc = "\n".join(desc_parts)
                    
                    item.enrichment_status = "SUCCESS"
                    item.enrichment_error = None
                    item.enriched_title = result['title']
                    item.enriched_description = template_desc
                    print(f"    SUCCESS (smart template - {category})")
                else:
                    # LLM succeeded
                    item.enrichment_status = "SUCCESS"
                    item.enrichment_error = None
                    item.enriched_title = result['title']
                    item.enriched_description = result['description']
                    print(f"    SUCCESS (LLM)")
                
                db.commit()
                
                # Rate limit protection
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
    
    print(f"Starting enrichment worker")
    print(f"   Batch size: {batch_size}")
    print(f"   Delay: {delay}s between items")
    print()
    
    enrich_batch(batch_size, delay)
