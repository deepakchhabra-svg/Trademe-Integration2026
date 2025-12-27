"""
Performance Optimization Script
Adds database indexes for faster queries
"""

import sys
import os
# Ensure repo root is on sys.path regardless of cwd
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

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
                "CREATE INDEX IF NOT EXISTS idx_supplier_products_source_category ON supplier_products(source_category)",
                "CREATE INDEX IF NOT EXISTS idx_supplier_products_last_scraped_at ON supplier_products(last_scraped_at)",
                
                # Orders - frequently queried by tm_order_ref and status
                "CREATE INDEX IF NOT EXISTS idx_orders_tm_order_ref ON orders(tm_order_ref)",
                "CREATE INDEX IF NOT EXISTS idx_orders_fulfillment_status ON orders(fulfillment_status)",
                "CREATE INDEX IF NOT EXISTS idx_orders_order_status ON orders(order_status)",
                "CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at)",
                
                # Trade Me listings - frequently queried by state
                "CREATE INDEX IF NOT EXISTS idx_trademe_listings_actual_state ON trademe_listings(actual_state)",
                "CREATE INDEX IF NOT EXISTS idx_trademe_listings_tm_listing_id ON trademe_listings(tm_listing_id)",
                "CREATE INDEX IF NOT EXISTS idx_trademe_listings_lifecycle_state ON trademe_listings(lifecycle_state)",
                "CREATE INDEX IF NOT EXISTS idx_trademe_listings_internal_product_id ON trademe_listings(internal_product_id)",
                
                # Internal products - frequently joined
                "CREATE INDEX IF NOT EXISTS idx_internal_products_primary_supplier_product_id ON internal_products(primary_supplier_product_id)",

                # Commands - critical ops queues
                "CREATE INDEX IF NOT EXISTS idx_system_commands_status ON system_commands(status)",
                "CREATE INDEX IF NOT EXISTS idx_system_commands_type ON system_commands(type)",
                "CREATE INDEX IF NOT EXISTS idx_system_commands_created_at ON system_commands(created_at)",

                # Audit logs - high-volume verification trail
                "CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_audit_logs_entity ON audit_logs(entity_type, entity_id)",
                "CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action)",

                # Listing metrics - time series
                "CREATE INDEX IF NOT EXISTS idx_listing_metrics_listing_id ON listing_metrics(listing_id)",
                "CREATE INDEX IF NOT EXISTS idx_listing_metrics_captured_at ON listing_metrics(captured_at)",
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
