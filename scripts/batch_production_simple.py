import sys
import os
sys.path.append(os.getcwd())

from retail_os.core.database import SessionLocal, SupplierProduct, InternalProduct
from retail_os.quality.rebuilder import ContentRebuilder
import csv
from pathlib import Path

def batch_production_simple(limit=100):
    """Simplified batch: works with actual schema."""
    
    db = SessionLocal()
    rebuilder = ContentRebuilder()
    
    # Get first N items
    items = db.query(SupplierProduct).limit(limit).all()
    
    print("=" * 60)
    print("PRODUCTION BATCH LAUNCH (SIMPLIFIED)")
    print("=" * 60)
    print(f"Processing {len(items)} items...")
    print()
    
    ready_items = []
    processed = 0
    passed = 0
    blocked = 0
    
    for idx, sp in enumerate(items, 1):
        try:
            # Match internal product by SKU
            internal_sku = f"CC-{sp.external_sku}"
            internal = db.query(InternalProduct).filter_by(sku=internal_sku).first()
            
            if not internal:
                continue
            
            # Rebuild content (no specs since schema doesn't have them)
            result = rebuilder.rebuild(
                title=sp.title or "",
                specs={},  # Empty since not in schema
                condition="Used",
                warranty_months=0
            )
            
            # Simple trust check: has title, description, and image
            has_title = bool(sp.title and len(sp.title) > 10)
            has_desc = bool(sp.description and len(sp.description) > 20)
            has_image = bool(sp.images and len(sp.images) > 0)
            is_clean = result.is_clean
            
            is_ready = has_title and has_desc and has_image and is_clean
            
            # Log first 5
            if idx <= 5:
                print(f"[{idx}] {sp.title[:50] if sp.title else 'No Title'}...")
                if is_ready:
                    print(f"    [SUCCESS] Ready for publish")
                    if sp.images:
                        print(f"    [IMAGE] {sp.images[0]}")
                else:
                    reasons = []
                    if not has_title: reasons.append("No Title")
                    if not has_desc: reasons.append("No Description")
                    if not has_image: reasons.append("No Image")
                    if not is_clean: reasons.append("Content Issues")
                    print(f"    [BLOCKED] {', '.join(reasons)}")
                print()
            
            # Collect ready items
            if is_ready:
                ready_items.append({
                    'SKU': sp.external_sku,
                    'Title': sp.title,
                    'Clean_Title': sp.title,  # No specs to extract from
                    'Local_Image': sp.images[0] if sp.images else '',
                    'Price': sp.cost_price or 0,
                    'URL': sp.product_url or ''
                })
                passed += 1
            else:
                blocked += 1
            
            processed += 1
            
        except Exception as e:
            print(f"[ERROR] Item {idx}: {e}")
    
    db.close()
    
    # Create CSV
    exports_dir = Path("exports")
    exports_dir.mkdir(exist_ok=True)
    csv_path = exports_dir / "ready_to_publish.csv"
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        if ready_items:
            writer = csv.DictWriter(f, fieldnames=ready_items[0].keys())
            writer.writeheader()
            writer.writerows(ready_items)
    
    print("=" * 60)
    print("COMPLETION REPORT")
    print("=" * 60)
    print(f"Total Processed: {processed}")
    print(f"[READY] Ready for publish: {passed}")
    print(f"[BLOCKED]: {blocked}")
    print(f"CSV Export: {csv_path}")
    print(f"   - {len(ready_items)} items in CSV")
    print("=" * 60)
    
    return {
        "processed": processed,
        "ready": passed,
        "blocked": blocked,
        "csv_path": str(csv_path)
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Batch Production Exporter")
    parser.add_argument("--limit", "-l", type=int, default=100, help="Max items to process")
    args = parser.parse_args()
    
    batch_production_simple(limit=args.limit) 

