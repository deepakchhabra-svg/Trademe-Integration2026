import pytest
import os
from fastapi.testclient import TestClient
from services.api.main import app

@pytest.fixture
def client():
    # Enable Header-based Auth for TestClient during tests
    os.environ["RETAIL_OS_INSECURE_ALLOW_HEADER_ROLES"] = "true"
    with TestClient(app) as c:
        yield c
    # Cleanup
    if "RETAIL_OS_INSECURE_ALLOW_HEADER_ROLES" in os.environ:
        del os.environ["RETAIL_OS_INSECURE_ALLOW_HEADER_ROLES"]

def test_get_kpis(client):
    headers = {"X-RetailOS-Role": "power"} 
    resp = client.get("/ops/kpis", headers=headers)
    assert resp.status_code == 200
    kpis = resp.json()
    assert "sales_today" in kpis
    assert "listed_today" in kpis
    assert "failures_today" in kpis

def test_bulk_reprice_preview(client):
    headers = {"X-RetailOS-Role": "power"} 
    resp = client.post("/ops/bulk/reprice", json={
        "rule_type": "percentage",
        "rule_value": 0.20, # 20% margin
        "dry_run": True, 
        "limit": 5
    }, headers=headers)
    
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("dry_run") is True
    assert "items" in data
    
    # If there are items, verify structure
    if data["items"]:
        item = data["items"][0]
        assert "listing_id" in item
        assert "new_price" in item
        assert "is_safe" in item

def test_get_duplicates(client):
    headers = {"X-RetailOS-Role": "power"} 
    resp = client.get("/ops/duplicates", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "count" in data
    assert "duplicates" in data
    assert isinstance(data["duplicates"], list)
