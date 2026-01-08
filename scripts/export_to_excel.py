"""
Export ready-to-publish products to Excel

Usage:
    python scripts/export_to_excel.py [--supplier SUPPLIER_NAME] [--output filename.xlsx]
    
Examples:
    python scripts/export_to_excel.py
    python scripts/export_to_excel.py --supplier NOEL_LEEMING
    python scripts/export_to_excel.py --output my_products.xlsx
"""
import os
import sys
import argparse
from datetime import datetime

# Add repo root to path
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from retail_os.core.database import SessionLocal, InternalProduct, Supplier
from sqlalchemy import and_

def export_to_excel(supplier_name: str | None = None, output_file: str | None = None):
    """Export ready-to-publish products to Excel."""
    
    # Default output filename
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        supplier_suffix = f"_{supplier_name}" if supplier_name else ""
        output_file = f"ready_to_publish{supplier_suffix}_{timestamp}.xlsx"
    
    print(f"Exporting ready-to-publish products to: {output_file}")
    
    # Query database
    db = SessionLocal()
    try:
        query = db.query(InternalProduct).filter(
            InternalProduct.ready_to_publish == True
        )
        
        # Filter by supplier if specified
        if supplier_name:
            supplier = db.query(Supplier).filter_by(name=supplier_name.upper()).first()
            if not supplier:
                print(f"ERROR: Supplier '{supplier_name}' not found")
                return
            query = query.filter(InternalProduct.supplier_id == supplier.id)
        
        products = query.all()
        
        if not products:
            print("No ready-to-publish products found!")
            return
        
        print(f"Found {len(products)} ready-to-publish products")
        
        # Prepare data for Excel
        data = []
        for p in products:
            data.append({
                "ID": p.id,
                "SKU": p.sku,
                "Supplier": p.supplier.name if p.supplier else "N/A",
                "Title": p.title,
                "Description": (p.description or "")[:100] + "..." if p.description and len(p.description) > 100 else p.description,
                "Buy Now Price": p.buy_now_price,
                "Reserve Price": p.reserve_price,
                "Start Price": p.start_price,
                "Category": p.category,
                "Condition": p.condition,
                "Brand": p.brand,
                "Model": p.model,
                "Stock Level": p.stock_level,
                "Source URL": p.source_url,
                "Photo 1": p.photo1,
                "Photo 2": p.photo2,
                "Photo 3": p.photo3,
                "Created": p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else None,
                "Updated": p.updated_at.strftime("%Y-%m-%d %H:%M") if p.updated_at else None,
            })
        
        # Export to Excel using pandas
        try:
            import pandas as pd
            df = pd.DataFrame(data)
            
            # Create Excel writer with formatting
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Ready to Publish')
                
                # Auto-adjust column widths
                worksheet = writer.sheets['Ready to Publish']
                for idx, col in enumerate(df.columns):
                    max_length = max(
                        df[col].astype(str).apply(len).max(),
                        len(col)
                    )
                    worksheet.column_dimensions[chr(65 + idx)].width = min(max_length + 2, 50)
            
            print(f"✅ Successfully exported to: {output_file}")
            print(f"   Total products: {len(products)}")
            
        except ImportError:
            print("ERROR: pandas and openpyxl are required for Excel export")
            print("Install with: pip install pandas openpyxl")
            
            # Fallback to CSV
            import csv
            csv_file = output_file.replace('.xlsx', '.csv')
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                if data:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
            print(f"✅ Exported to CSV instead: {csv_file}")
            
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export ready-to-publish products to Excel")
    parser.add_argument("--supplier", type=str, help="Filter by supplier name (e.g., NOEL_LEEMING, ONECHEQ)")
    parser.add_argument("--output", type=str, help="Output filename (default: ready_to_publish_YYYYMMDD_HHMMSS.xlsx)")
    
    args = parser.parse_args()
    
    export_to_excel(
        supplier_name=args.supplier,
        output_file=args.output
    )
