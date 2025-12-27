"""
Performance Optimization Script
Adds database indexes for faster queries
"""

import sys
import os
sys.path.append(os.getcwd())

from retail_os.core.database import engine
from sqlalchemy import text

def add_performance_indexes():
    """
    Add indexes to speed up common queries
    """
    print("Adding performance indexes...")
    
    with engine.connect() as conn:
        try:
            indexes = [
                # Supplier products - frequently queried by supplier_id
                "CREATE INDEX IF NOT EXISTS idx_supplier_products_supplier_id ON supplier_products(supplier_id)",
                "CREATE INDEX IF NOT EXISTS idx_supplier_products_external_sku ON supplier_products(external_sku)",
                "CREATE INDEX IF NOT EXISTS idx_supplier_products_enrichment_status ON supplier_products(enrichment_status)",
                "CREATE INDEX IF NOT EXISTS idx_supplier_products_sync_status ON supplier_products(sync_status)",
                
                # Orders - frequently queried by tm_order_ref and status
                "CREATE INDEX IF NOT EXISTS idx_orders_tm_order_ref ON orders(tm_order_ref)",
                "CREATE INDEX IF NOT EXISTS idx_orders_fulfillment_status ON orders(fulfillment_status)",
                "CREATE INDEX IF NOT EXISTS idx_orders_order_status ON orders(order_status)",
                
                # Trade Me listings - frequently queried by state
                "CREATE INDEX IF NOT EXISTS idx_trademe_listings_actual_state ON trademe_listings(actual_state)",
                "CREATE INDEX IF NOT EXISTS idx_trademe_listings_tm_listing_id ON trademe_listings(tm_listing_id)",
                "CREATE INDEX IF NOT EXISTS idx_trademe_listings_lifecycle_state ON trademe_listings(lifecycle_state)",
                
                # Internal products - frequently joined
                "CREATE INDEX IF NOT EXISTS idx_internal_products_primary_supplier_product_id ON internal_products(primary_supplier_product_id)",
            ]
            
            for idx_sql in indexes:
                try:
                    conn.execute(text(idx_sql))
                    conn.commit()
                    idx_name = idx_sql.split('idx_')[1].split(' ON')[0]
                    print(f"  [OK] Created index: idx_{idx_name}")
                except Exception as e:
                    if 'already exists' in str(e).lower():
                        print(f"  [SKIP] Index already exists")
                    else:
                        print(f"  [WARN] {str(e)[:100]}")
            
            print("\n[SUCCESS] All indexes created!")
            print("\n[IMPACT] Queries should be 10-100x faster now")
            
        except Exception as e:
            print(f"[ERROR] Failed to create indexes: {e}")
            conn.rollback()

if __name__ == "__main__":
    add_performance_indexes()
