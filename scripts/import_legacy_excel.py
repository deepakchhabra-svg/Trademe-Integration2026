"""
Import Legacy Excel/CSV Products into RetailOS

This script imports products from the legacy Excel file into the database
as SupplierProduct entries under a "LEGACY" supplier, then creates
InternalProduct records ready for enrichment and listing.

Usage:
    python scripts/import_legacy_excel.py [--dry-run] [--limit N]
"""
import os
import sys
import re
import argparse
from datetime import datetime, timezone
from decimal import Decimal

# Add repo root to path
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import pandas as pd
from retail_os.core.database import (
    SessionLocal, init_db,
    Supplier, SupplierProduct, InternalProduct, SystemCommand
)
from sqlalchemy import func
import uuid

def parse_price(value) -> float:
    """Parse price string like '1,169.00' to float."""
    if pd.isna(value):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    # Remove currency symbols and commas
    cleaned = re.sub(r'[,$NZD\s]', '', str(value))
    try:
        return float(cleaned)
    except ValueError:
        return 0.0

def clean_text(value) -> str:
    """Clean text field."""
    if pd.isna(value):
        return ""
    return str(value).strip()

def import_products(csv_path: str, dry_run: bool = False, limit: int = None):
    """Import products from CSV into database."""
    
    print(f"Loading data from: {csv_path}")
    df = pd.read_csv(csv_path)
    
    if limit:
        df = df.head(limit)
        print(f"Limited to {limit} products")
    
    print(f"Total products to import: {len(df)}")
    
    if dry_run:
        print("\n[DRY RUN MODE - No changes will be made]\n")
    
    init_db()
    session = SessionLocal()
    
    try:
        # 1. Create or get LEGACY supplier
        supplier = session.query(Supplier).filter_by(name="LEGACY").first()
        if not supplier:
            if not dry_run:
                supplier = Supplier(
                    name="LEGACY",
                    base_url="file://legacy-import",
                    is_active=True
                )
                session.add(supplier)
                session.commit()
                print(f"Created LEGACY supplier (id={supplier.id})")
            else:
                print("Would create LEGACY supplier")
                supplier_id = 999  # Placeholder for dry run
        else:
            print(f"Using existing LEGACY supplier (id={supplier.id})")
        
        supplier_id = supplier.id if supplier else 999
        
        # 2. Import products
        created = 0
        updated = 0
        skipped = 0
        errors = []
        
        for idx, row in df.iterrows():
            try:
                sku = clean_text(row.get('Code', ''))
                title = clean_text(row.get('Name', ''))
                
                if not sku or not title:
                    skipped += 1
                    continue
                
                # Parse prices
                sell_price = parse_price(row.get('Sell Price Inc Tax', 0))
                cost_price = parse_price(row.get('Cost Price', 0))
                
                # If no cost price, estimate at 60% of sell price (typical retail margin)
                if cost_price <= 0 and sell_price > 0:
                    cost_price = sell_price * 0.6
                
                # Extract other fields
                description = clean_text(row.get('Description', ''))
                brand = clean_text(row.get('Brand', ''))
                barcode = clean_text(row.get('Barcode', ''))
                photo = clean_text(row.get('Photo Identifier', ''))
                notes = clean_text(row.get('Internal Notes', ''))
                
                # Determine stock status from notes
                is_out_of_stock = 'out of stock' in notes.lower() if notes else False
                
                if dry_run:
                    print(f"  [{idx+1}] Would import: {sku} - {title[:50]}... (${sell_price:.2f})")
                    created += 1
                    continue
                
                # Check if already exists
                existing = session.query(SupplierProduct).filter_by(
                    supplier_id=supplier_id,
                    external_sku=sku
                ).first()
                
                if existing:
                    # Update existing
                    existing.title = title
                    existing.description = description
                    existing.brand = brand
                    existing.cost_price = Decimal(str(cost_price))
                    existing.last_scraped_at = datetime.now(timezone.utc)
                    existing.sync_status = "REMOVED" if is_out_of_stock else "PRESENT"
                    if photo:
                        existing.images = [photo]
                    updated += 1
                else:
                    # Create new
                    sp = SupplierProduct(
                        supplier_id=supplier_id,
                        external_sku=sku,
                        title=title,
                        description=description,
                        brand=brand,
                        condition="New",
                        cost_price=Decimal(str(cost_price)),
                        stock_level=0 if is_out_of_stock else 1,
                        product_url=f"legacy://{sku}",
                        images=[photo] if photo else [],
                        enrichment_status="PENDING",
                        last_scraped_at=datetime.now(timezone.utc),
                        sync_status="REMOVED" if is_out_of_stock else "PRESENT",
                        source_category="LEGACY_IMPORT",
                    )
                    session.add(sp)
                    session.flush()
                    
                    # Create InternalProduct linkage
                    internal_sku = f"LEG-{sku}"
                    existing_ip = session.query(InternalProduct).filter_by(sku=internal_sku).first()
                    if not existing_ip:
                        ip = InternalProduct(
                            sku=internal_sku,
                            title=title,
                            primary_supplier_product_id=sp.id
                        )
                        session.add(ip)
                    
                    created += 1
                
                # Commit every 100 records
                if (idx + 1) % 100 == 0:
                    session.commit()
                    print(f"  Progress: {idx+1}/{len(df)} ({created} created, {updated} updated)")
            
            except Exception as e:
                errors.append(f"Row {idx+1} ({sku}): {str(e)}")
                continue
        
        if not dry_run:
            session.commit()
        
        print(f"\n=== IMPORT COMPLETE ===")
        print(f"Created: {created}")
        print(f"Updated: {updated}")
        print(f"Skipped: {skipped}")
        print(f"Errors: {len(errors)}")
        
        if errors and len(errors) <= 10:
            print("\nErrors:")
            for e in errors:
                print(f"  - {e}")
        elif errors:
            print(f"\nFirst 10 errors (of {len(errors)}):")
            for e in errors[:10]:
                print(f"  - {e}")
        
        # 3. Queue enrichment if products were created
        if created > 0 and not dry_run:
            print("\n=== QUEUEING ENRICHMENT ===")
            cmd = SystemCommand(
                id=str(uuid.uuid4()),
                type="ENRICH_SUPPLIER",
                payload={
                    "supplier_id": supplier_id,
                    "supplier_name": "LEGACY",
                    "batch_size": 50
                },
                status="PENDING",
                priority=50
            )
            session.add(cmd)
            session.commit()
            print(f"Queued ENRICH_SUPPLIER command for LEGACY supplier")
            print(f"Command ID: {cmd.id}")
        
        return created, updated, skipped, len(errors)
    
    except Exception as e:
        session.rollback()
        print(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 0, 0, 0, 1
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import legacy Excel products")
    parser.add_argument("--dry-run", action="store_true", help="Preview without making changes")
    parser.add_argument("--limit", type=int, help="Limit number of products to import")
    parser.add_argument("--file", type=str, default="data/import_listings.xlsx", help="Path to CSV/Excel file")
    
    args = parser.parse_args()
    
    import_products(args.file, dry_run=args.dry_run, limit=args.limit)
