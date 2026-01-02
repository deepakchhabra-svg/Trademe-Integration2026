import os
import sys

# Ensure project root is in path
sys.path.append(os.getcwd())

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from retail_os.core.database import Base, Supplier, init_db, InternalProduct, TradeMeListing

# Match the DB URL from playwright.config.ts
DB_URL = os.environ.get("RETAILOS_E2E_DATABASE_URL", "sqlite:////tmp/retailos_e2e.sqlite")

def seed():
    print(f"Seeding DB: {DB_URL}")
    engine = create_engine(DB_URL)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed Suppliers
    if not session.query(Supplier).filter_by(name="ONECHEQ").first():
        s1 = Supplier(id=1, name="ONECHEQ", is_active=True, base_url="https://onecheq.co.nz")
        session.add(s1)
        print("Added Supplier: ONECHEQ")
    
    if not session.query(Supplier).filter_by(name="NOEL_LEEMING").first():
        s2 = Supplier(id=2, name="NOEL_LEEMING", is_active=True, base_url="https://www.noelleeming.co.nz")
        session.add(s2)
        print("Added Supplier: NOEL_LEEMING")

    # Seed Supplier Product for duplicates
    from retail_os.core.database import SupplierProduct
    
    sp1 = session.query(SupplierProduct).filter_by(external_sku="SKU-DUP-1").first()
    if not sp1:
        sp1 = SupplierProduct(
            supplier_id=1, 
            external_sku="SKU-DUP-1", 
            title="Duplicate Product Source",
            cost_price=5.0
        )
        session.add(sp1)
        session.flush() # Get ID
        print("Added SupplierProduct: SKU-DUP-1")

    # Seed Internal Product
    if not session.query(InternalProduct).filter_by(id=1).first():
        p1 = InternalProduct(
            id=1, 
            title="Duplicate Product", 
            sku="INT-SKU-1",
            primary_supplier_product_id=sp1.id
        )
        session.add(p1)
        print("Added InternalProduct: Duplicate Product")
    
    # Ensure TradeMeListing table works (seed dummy listing)
    from retail_os.core.database import TradeMeListing
    if not session.query(TradeMeListing).filter_by(tm_listing_id="12345").first():
        l1 = TradeMeListing(
            tm_listing_id="12345", 
            internal_product_id=1, 
            desired_price=10.0,
            actual_price=10.0
        )
        session.add(l1)
        print("Added TradeMeListing: 12345")

    session.commit()
    print("Seeding complete.")

if __name__ == "__main__":
    seed()
