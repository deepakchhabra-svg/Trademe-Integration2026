import sys
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from retail_os.core.database import Base, Supplier, SupplierProduct, InternalProduct, TradeMeListing, Order, SystemCommand
from scripts.factory_reset import soft_reset, hard_reset

# Setup In-Memory DB for testing
@pytest.fixture(scope="function")
def test_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Helper to seed data
    supplier = Supplier(name="TEST", base_url="http://test.com")
    session.add(supplier)
    session.flush()
    session.commit()
    
    yield session
    session.close()

def test_soft_reset_preserves_live(test_session):
    s = test_session
    # Setup: 
    # 1. Live Chain (Should Stay)
    sp_live = SupplierProduct(supplier_id=1, external_sku="LIVE1", title="Live Item")
    s.add(sp_live); s.flush()
    ip_live = InternalProduct(sku="I-LIVE", primary_supplier_product_id=sp_live.id)
    s.add(ip_live); s.flush()
    tl_live = TradeMeListing(internal_product_id=ip_live.id, actual_state="Live", tm_listing_id="TM1")
    s.add(tl_live)

    # 2. Draft Chain (Should Go)
    sp_draft = SupplierProduct(supplier_id=1, external_sku="DRAFT1", title="Draft Item")
    s.add(sp_draft); s.flush()
    ip_draft = InternalProduct(sku="I-DRAFT", primary_supplier_product_id=sp_draft.id)
    s.add(ip_draft); s.flush()
    tl_draft = TradeMeListing(internal_product_id=ip_draft.id, actual_state="DRY_RUN", tm_listing_id="DRY1")
    s.add(tl_draft)
    
    # 3. Queue (Should Go)
    cmd = SystemCommand(id="cmd1", type="TEST")
    s.add(cmd)

    s.commit()
    
    # Run Soft Reset
    soft_reset(s)
    s.commit()
    
    # Assertions
    assert s.query(TradeMeListing).filter_by(tm_listing_id="TM1").count() == 1
    assert s.query(InternalProduct).filter_by(sku="I-LIVE").count() == 1
    assert s.query(SupplierProduct).filter_by(external_sku="LIVE1").count() == 1
    
    assert s.query(TradeMeListing).filter_by(tm_listing_id="DRY1").count() == 0
    assert s.query(InternalProduct).filter_by(sku="I-DRAFT").count() == 0
    assert s.query(SupplierProduct).filter_by(external_sku="DRAFT1").count() == 0
    
    assert s.query(SystemCommand).count() == 0

def test_hard_reset_safety_and_orders(test_session):
    s = test_session
    
    # Setup: 1 Live Listing (Safety Block)
    s.add(TradeMeListing(id=1, actual_state="Live", tm_listing_id="BLOCKER"))
    s.commit()
    
    # 1. Test Safety Block
    with pytest.raises(Exception) as e:
        hard_reset(s)
    assert "ABORTING" in str(e.value)
    
    # Setup: Clear Live, add Order linked to a Draft
    s.query(TradeMeListing).delete()
    
    tl_draft = TradeMeListing(id=2, actual_state="DRY_RUN", tm_listing_id="TM_OLD")
    s.add(tl_draft)
    s.flush()
    
    order = Order(id=1, tm_order_ref="O1", tm_listing_id=2, sold_price=10.0)
    s.add(order)
    s.commit()
    
    # 2. Run Hard Reset
    hard_reset(s)
    s.commit()
    
    # Assertions
    assert s.query(TradeMeListing).count() == 0
    
    # Order should exist but have NULL listing_id
    o = s.query(Order).first()
    assert o is not None
    assert o.tm_listing_id is None
    assert o.tm_order_ref == "O1"
