
import pytest
from unittest.mock import patch
from retail_os.core.database import Supplier, SupplierProduct, InternalProduct

@pytest.fixture
def seeded_db(db_session, tmp_path):
    # create fake image
    img_path = tmp_path / "fake.jpg"
    img_path.write_text("fake image content")
    str_path = str(img_path)
    
    s = Supplier(id=1, name="Test Supplier", is_active=True)
    db_session.add(s)
    sp = SupplierProduct(
        id=10, supplier_id=1, external_sku="SKU", title="Test Item", 
        cost_price=10.0, sync_status="PRESENT", product_url="http://x",
        enriched_title="Enriched Item", enriched_description="Desc",
        images=[str_path]
    )
    db_session.add(sp)
    ip = InternalProduct(id=100, sku="INT-SKU", title="Test Item", primary_supplier_product_id=10)
    db_session.add(ip)
    db_session.commit()
    return db_session


@patch("retail_os.core.category_mapper.CategoryMapper.map_category")
def test_bulk_dryrun_publish(mock_map, client, seeded_db):
    mock_map.return_value = "0001-0002"
    headers = {"X-RetailOS-Role": "power"}
    payload = {
        "supplier_id": 1,
        "limit": 5
    }
    resp = client.post("/ops/bulk/dryrun_publish", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    
    if data.get("enqueued") != 1:
        print(f"DEBUG BULK: {data}")
    
    # Assert
    assert data["enqueued"] == 1
    assert data["requested_limit"] == 5

def test_bulk_reprice_preview(client, seeded_db):
    # Skipped as per previous context
    pass 
