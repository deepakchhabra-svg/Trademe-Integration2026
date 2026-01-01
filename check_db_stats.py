
import sys
import os
from sqlalchemy.orm import Session
from sqlalchemy import func

# Ensure we can import from the current directory
sys.path.append(os.getcwd())

from retail_os.core.database import SessionLocal, SupplierProduct, InternalProduct, TradeMeListing, Supplier

def check_db_stats():
    print("=== Database Statistics ===\n")
    session = SessionLocal()
    try:
        # Suppliers
        suppliers = session.query(Supplier).all()
        print(f"Suppliers ({len(suppliers)}):")
        for s in suppliers:
            count = session.query(SupplierProduct).filter(SupplierProduct.supplier_id == s.id).count()
            print(f"  - {s.name}: {count} products")
            
        print("\nGeneral Stats:")
        # Supplier Products
        sp_count = session.query(SupplierProduct).count()
        print(f"Total Supplier Products: {sp_count}")
        
        # Enrichment stats
        pending = session.query(SupplierProduct).filter(SupplierProduct.enrichment_status == "PENDING").count()
        success = session.query(SupplierProduct).filter(SupplierProduct.enrichment_status == "SUCCESS").count()
        failed = session.query(SupplierProduct).filter(SupplierProduct.enrichment_status == "FAILED").count()
        print(f"Enrichment: {pending} PENDING, {success} SUCCESS, {failed} FAILED")
        
        # Internal Products
        ip_count = session.query(InternalProduct).count()
        print(f"Total Internal Products: {ip_count}")
        
        # TradeMe Listings
        tm_count = session.query(TradeMeListing).count()
        live_count = session.query(TradeMeListing).filter(TradeMeListing.tm_listing_id.isnot(None)).count()
        print(f"Total TradeMe Listings in DB: {tm_count}")
        print(f"Live Listings (with TM ID): {live_count}")
        
    finally:
        session.close()

if __name__ == "__main__":
    check_db_stats()
