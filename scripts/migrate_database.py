"""
Database Migration Script
Adds new columns to existing tables without losing data
"""

import sys
import os
sys.path.append(os.getcwd())

from retail_os.core.database import engine
from sqlalchemy import text

def migrate_database():
    """
    Add new columns to existing tables
    """
    print("Starting Database Migration...")
    
    with engine.connect() as conn:
        try:
            # Add new columns to orders table
            print("Adding columns to 'orders' table...")
            
            migrations = [
                "ALTER TABLE orders ADD COLUMN tm_listing_id INTEGER",
                "ALTER TABLE orders ADD COLUMN sold_price NUMERIC(10, 2)",
                "ALTER TABLE orders ADD COLUMN sold_date DATETIME",
                "ALTER TABLE orders ADD COLUMN buyer_email VARCHAR",
                "ALTER TABLE orders ADD COLUMN order_status VARCHAR DEFAULT 'PENDING'",
                "ALTER TABLE orders ADD COLUMN payment_status VARCHAR DEFAULT 'PENDING'",
                "ALTER TABLE orders ADD COLUMN fulfillment_status VARCHAR DEFAULT 'PENDING'",
                "ALTER TABLE orders ADD COLUMN shipped_date DATETIME",
                "ALTER TABLE orders ADD COLUMN delivered_date DATETIME",
                "ALTER TABLE orders ADD COLUMN updated_at DATETIME",
                
                # Rename old status column if it exists
                "ALTER TABLE orders RENAME COLUMN status TO old_status",
            ]
            
            for migration in migrations:
                try:
                    conn.execute(text(migration))
                    conn.commit()
                    print(f"  [OK] {migration[:50]}...")
                except Exception as e:
                    if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                        print(f"  [SKIP] Column already exists...")
                    else:
                        print(f"  [WARN] {str(e)[:100]}")
            
            print("\n[SUCCESS] Migration Complete!")
            print("\n[IMPORTANT] Restart the dashboard now!")
            
        except Exception as e:
            print(f"[ERROR] Migration failed: {e}")
            conn.rollback()

if __name__ == "__main__":
    migrate_database()
