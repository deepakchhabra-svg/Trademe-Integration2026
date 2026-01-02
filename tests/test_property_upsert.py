
import pytest
import sqlite3
import json
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from retail_os.core.database import Base, SupplierProduct, InternalProduct
from retail_os.core.product_upserter import ProductUpserter

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@patch("retail_os.core.product_upserter.ImageDownloader")
def test_upsert_idempotency(mock_downloader_cls, db_session):
    """
    Property: Upserting the same data twice yields identical DB state and 'unchanged' result.
    """
    # Setup Mock
    mock_downloader = mock_downloader_cls.return_value
    mock_downloader.download_image.return_value = {"success": True, "path": "data/media/foo.jpg"}
    
    upserter = ProductUpserter(db_session, supplier_id=1)
    
    data = {
        "buy_now_price": 100.0,
        "stock_level": 10,
        "title": "Test Product",
        "description": "Desc",
        "source_url": "http://example.com",
        "photo1": "http://img.com/1.jpg"
    }
    
    # 1. First Upsert -> Create
    res1 = upserter.upsert(data, "SKU123", "INT")
    assert res1 == "created"
    assert db_session.query(SupplierProduct).count() == 1
    sp = db_session.query(SupplierProduct).first()
    first_hash = sp.snapshot_hash
    
    # 2. Second Upsert -> Unchanged
    res2 = upserter.upsert(data, "SKU123", "INT")
    assert res2 == "unchanged"
    assert db_session.query(SupplierProduct).count() == 1
    sp2 = db_session.query(SupplierProduct).first()
    assert sp2.snapshot_hash == first_hash
    
    # 3. Change Data -> Update
    data["title"] = "New Title"
    res3 = upserter.upsert(data, "SKU123", "INT")
    assert res3 == "updated"
    sp3 = db_session.query(SupplierProduct).first()
    assert sp3.title == "New Title"
    assert sp3.snapshot_hash != first_hash
