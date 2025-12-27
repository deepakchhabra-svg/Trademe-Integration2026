"""
COMPREHENSIVE SCHEMA AUDIT
Compares actual SQLite table columns against SQLAlchemy Model definitions.
Reports ALL missing columns across the entire database.
"""

import sys
import os
sys.path.append(os.getcwd())

from retail_os.core.database import engine, Base, SupplierProduct, InternalProduct, TradeMeListing, Order, JobStatus, SystemCommand, PhotoHash
from sqlalchemy import inspect

def analyze_schema_gaps():
    print("STARTING COMPREHENSIVE SCHEMA AUDIT...")
    inspector = inspect(engine)
    
    # Map table names to Model classes
    model_map = {
        'supplier_products': SupplierProduct,
        'internal_products': InternalProduct,
        'trademe_listings': TradeMeListing,
        'orders': Order,
        'job_status': JobStatus,
        'system_commands': SystemCommand,
        'photo_hashes': PhotoHash
    }
    
    all_gaps = []

    for table_name, model_class in model_map.items():
        print(f"\nAnalyzing Table: {table_name}")
        
        # Get actual columns in DB
        try:
            db_columns = [col['name'] for col in inspector.get_columns(table_name)]
        except Exception as e:
            print(f"  [MISSING] Table '{table_name}' does not exist in DB!")
            all_gaps.append(f"Table '{table_name}' MISSING entirely")
            continue
            
        # Get expected columns from Model
        model_columns = [c.name for c in model_class.__table__.columns]
        
        # Find missing columns
        missing_in_db = set(model_columns) - set(db_columns)
        
        if missing_in_db:
            print(f"  [GAP] Mismatch found! Missing: {missing_in_db}")
            for col in missing_in_db:
                # Get column type/details for the fix script
                col_obj = model_class.__table__.columns[col]
                all_gaps.append({
                    'table': table_name,
                    'column': col,
                    'type': str(col_obj.type),
                    'default': col_obj.default.arg if col_obj.default else None
                })
        else:
            print(f"  [OK] Table aligned ({len(db_columns)} columns)")

    print("\n" + "="*50)
    print("AUDIT RESULT")
    print("="*50)
    
    if all_gaps:
        print(f"Found {len(all_gaps)} schema gaps that need fixing.")
        return all_gaps
    else:
        print("NO SCHEMA GAPS FOUND. Database is perfectly aligned with Code.")
        return []

if __name__ == "__main__":
    gaps = analyze_schema_gaps()
    if gaps:
        print("\nGENERATING FIX COMMANDS...")
        for gap in gaps:
            if isinstance(gap, str):
                print(f"  - Create Table: {gap}")
            else:
                default_val = f" DEFAULT {gap['default']}" if gap['default'] is not None else ""
                print(f"  - ALTER TABLE {gap['table']} ADD COLUMN {gap['column']} {gap['type']}{default_val}")
