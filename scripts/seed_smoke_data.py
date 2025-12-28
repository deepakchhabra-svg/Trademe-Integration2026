import sys
import os

# Add repo root to PYTHONPATH so we can import 'retail_os'
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(repo_root)

# Force use of dev_db.sqlite BEFORE importing database module
os.environ["DATABASE_URL"] = "sqlite:///dev_db.sqlite"

from retail_os.core.database import SessionLocal, init_db, Supplier, SupplierProduct, InternalProduct, TradeMeListing, ListingState, engine
from sqlalchemy import create_engine
from datetime import datetime

def seed_smoke_data():
    print(f"Environment DATABASE_URL: {os.environ.get('DATABASE_URL')}")
    print(f"Engine URL: {engine.url}")
    print(f"Seeding smoke test data into: {os.environ['DATABASE_URL']}")
    
    # Initialize DB (create tables if missing)
    init_db()
    
    session = SessionLocal()
    try:
        print("Checking Supplier 1...")
        # 1. Supplier: ONECHEQ (id=1)
        supplier = session.query(Supplier).filter_by(id=1).first()
        print(f"Supplier query result: {supplier}")
        if not supplier:
            supplier = Supplier(id=1, name="ONECHEQ", base_url="https://onecheq.co.nz", is_active=True)
            session.add(supplier)
            print("Created Supplier: ONECHEQ")
            session.flush() # Try flush
        
        # 2. SupplierProduct (id=101, linked to ONECHEQ)
        sp = session.query(SupplierProduct).filter_by(id=101).first()
        if not sp:
            sp = SupplierProduct(
                id=101,
                supplier_id=1,
                external_sku="TEST-SKU-001",
                title="Google Pixel 7 Pro",
                description="A powerful smartphone from Google.",
                cost_price=899.00,
                stock_level=10,
                product_url="https://onecheq.co.nz/pixel-7",
                sync_status="PRESENT",
                enrichment_status="PENDING",
                last_scraped_at=datetime.utcnow(),
                source_category="smartphones"
            )
            session.add(sp)
            print("Created SupplierProduct: 101")

        # 3. Enriched Product (id=201)
        ip = session.query(InternalProduct).filter_by(id=201).first()
        if not ip:
            # Check if this IP is already linked to sp 101 just in case
            ip = InternalProduct(
                id=201,
                sku="OS-PIXEL-7",
                title="Google Pixel 7 Pro (Enriched)",
                primary_supplier_product_id=101
            )
            session.add(ip)
            print("Created InternalProduct: 201")
            
            # Update SP to link to this IP
            sp.enrichment_status = "SUCCESS"
            sp.enriched_title = "Google Pixel 7 Pro (Enriched)"
            sp.enriched_description = "The Google Pixel 7 Pro is a powerful smartphone featuring a telephoto lens, wide-angle camera, and 24-hour battery life. Unlocked for all carriers."

        # 4. Listing (id=301, linked to IP 201)
        listing = session.query(TradeMeListing).filter_by(id=301).first()
        if not listing:
            listing = TradeMeListing(
                id=301,
                internal_product_id=201,
                tm_listing_id="TM-123456",
                desired_price=950.00,
                actual_price=950.00,
                desired_state="Live",
                actual_state="Live",
                lifecycle_state=ListingState.STABLE,
                last_synced_at=datetime.utcnow()
            )
            session.add(listing)
            print("Created TradeMeListing: 301")

        session.commit()
        print("Seeding complete.")
        
    except Exception as e:
        session.rollback()
        print(f"Error during seeding: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    seed_smoke_data()
