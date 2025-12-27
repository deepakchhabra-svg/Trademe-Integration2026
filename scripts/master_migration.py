"""
MASTER MIGRATION SCRIPT
Fixes all identified schema gaps to align DB with Code.
"""

import sys
import os
sys.path.append(os.getcwd())

from retail_os.core.database import engine
from sqlalchemy import text

def run_migration():
    print("STARTING MASTER MIGRATION...")
    
    # Defined from Audit Result
    migrations = [
        "ALTER TABLE job_status ADD COLUMN items_created INTEGER DEFAULT 0",
        "ALTER TABLE job_status ADD COLUMN items_updated INTEGER DEFAULT 0",
        "ALTER TABLE job_status ADD COLUMN items_deleted INTEGER DEFAULT 0",

        # SupplierProduct categorization for scale (20k+ listings)
        "ALTER TABLE supplier_products ADD COLUMN source_category VARCHAR"
    ]
    
    with engine.connect() as conn:
        for sql in migrations:
            try:
                print(f"Running: {sql}")
                conn.execute(text(sql))
                conn.commit()
                print("  [OK] Success")
            except Exception as e:
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    print("  [SKIP] Column already exists")
                else:
                    print(f"  [ERROR] Failed: {e}")
                    
    print("\nMIGRATION COMPLETE.")

if __name__ == "__main__":
    run_migration()
