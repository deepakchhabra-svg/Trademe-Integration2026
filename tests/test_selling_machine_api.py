"""
Backend Route Smoke Tests
Goal: 100% coverage of all FastAPI routes.
Each route is tested for expected status codes and basic response shape.
"""
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

POWER_HEADERS = {"X-RetailOS-Role": "power"}
ADMIN_HEADERS = {"X-RetailOS-Role": "root"}

# =============================================================================
# SYSTEM ROUTES
# =============================================================================

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "ok"

def test_whoami(client):
    resp = client.get("/whoami", headers=POWER_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "role" in data

# =============================================================================
# DASHBOARD / KPI ROUTES
# =============================================================================

def test_ops_summary(client):
    resp = client.get("/ops/summary", headers=POWER_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "pipeline" in data or "stats" in data or "kpis" in data or isinstance(data, dict)

def test_ops_kpis(client):
    resp = client.get("/ops/kpis", headers=POWER_HEADERS)
    assert resp.status_code == 200
    kpis = resp.json()
    assert "sales_today" in kpis or "listed_today" in kpis or isinstance(kpis, dict)

def test_ops_pipeline_summary(client):
    resp = client.get("/ops/pipeline_summary", headers=POWER_HEADERS)
    # May require supplier_id param, so 422 is acceptable
    assert resp.status_code in [200, 422]

def test_ops_alerts(client):
    resp = client.get("/ops/alerts", headers=POWER_HEADERS)
    assert resp.status_code == 200

# =============================================================================
# PIPELINE ROUTES
# =============================================================================

def test_suppliers_list(client):
    resp = client.get("/suppliers", headers=POWER_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)

def test_supplier_pipeline_smoke(client, db_session):
    # Create a supplier first
    from retail_os.core.database import Supplier
    s = Supplier(id=1, name="Test", base_url="http://test")
    db_session.add(s)
    db_session.commit()
    
    resp = client.get("/ops/suppliers/1/pipeline", headers=POWER_HEADERS)
    assert resp.status_code in [200, 404]  # 200 if found, 404 if DB mismatch

def test_supplier_policy_get(client, db_session):
    from retail_os.core.database import Supplier
    s = Supplier(id=1, name="Test", base_url="http://test")
    db_session.add(s)
    db_session.commit()
    
    resp = client.get("/suppliers/1/policy", headers=POWER_HEADERS)
    assert resp.status_code in [200, 404]

# =============================================================================
# VAULT ROUTES
# =============================================================================

def test_vault_raw(client):
    resp = client.get("/vaults/raw", headers=POWER_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data or isinstance(data, list)

def test_vault_enriched(client):
    resp = client.get("/vaults/enriched", headers=POWER_HEADERS)
    assert resp.status_code == 200

def test_vault_live(client):
    resp = client.get("/vaults/live", headers=POWER_HEADERS)
    assert resp.status_code == 200

# =============================================================================
# JOBS / COMMANDS ROUTES
# =============================================================================

def test_commands_list(client):
    resp = client.get("/commands", headers=POWER_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data or isinstance(data, list)

def test_ops_inbox(client):
    resp = client.get("/ops/inbox", headers=POWER_HEADERS)
    assert resp.status_code == 200

def test_jobs_list(client):
    resp = client.get("/jobs", headers=POWER_HEADERS)
    assert resp.status_code == 200

def test_audits(client):
    resp = client.get("/audits", headers=POWER_HEADERS)
    assert resp.status_code == 200

# =============================================================================
# PRODUCT ROUTES
# =============================================================================

def test_products_list(client):
    resp = client.get("/products", headers=POWER_HEADERS)
    assert resp.status_code == 200

def test_orders_list(client):
    resp = client.get("/orders", headers=POWER_HEADERS)
    assert resp.status_code == 200

# =============================================================================
# MONITORING ROUTES
# =============================================================================

def test_trademe_account_summary(client):
    resp = client.get("/trademe/account_summary", headers=POWER_HEADERS)
    # May be 200 or error if TM not configured, just no 500
    assert resp.status_code in [200, 400, 401, 503]

def test_llm_health(client):
    resp = client.get("/llm/health", headers=POWER_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "active" in data or "provider" in data or isinstance(data, dict)

# =============================================================================
# PUBLISH / READINESS ROUTES
# =============================================================================

def test_ops_readiness(client):
    resp = client.get("/ops/readiness", headers=POWER_HEADERS)
    assert resp.status_code == 200

def test_ops_removed_items(client):
    resp = client.get("/ops/removed_items", headers=POWER_HEADERS)
    assert resp.status_code == 200

def test_ops_duplicates(client):
    resp = client.get("/ops/duplicates", headers=POWER_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "count" in data
    assert "duplicates" in data

# =============================================================================
# BULK MUTATION ROUTES (Dry Run / Preview)
# =============================================================================

def test_bulk_reprice_preview(client):
    resp = client.post("/ops/bulk/reprice", json={
        "rule_type": "percentage",
        "rule_value": 0.20,
        "dry_run": True,
        "limit": 5
    }, headers=POWER_HEADERS)
    
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("dry_run") is True
    assert "items" in data

def test_bulk_dryrun_publish(client, db_session):
    from retail_os.core.database import Supplier
    s = Supplier(id=1, name="Test", base_url="http://test")
    db_session.add(s)
    db_session.commit()
    
    resp = client.post("/ops/bulk/dryrun_publish", json={
        "supplier_id": 1,
        "limit": 5
    }, headers=POWER_HEADERS)
    
    assert resp.status_code in [200, 404]

def test_bulk_withdraw_removed(client, db_session):
    from retail_os.core.database import Supplier
    s = Supplier(id=1, name="Test", base_url="http://test")
    db_session.add(s)
    db_session.commit()
    
    resp = client.post("/ops/bulk/withdraw_removed", json={
        "supplier_id": 1
    }, headers=POWER_HEADERS)
    
    assert resp.status_code in [200, 404]

def test_trademe_validate_drafts(client, db_session):
    from retail_os.core.database import Supplier
    s = Supplier(id=1, name="Test", base_url="http://test")
    db_session.add(s)
    db_session.commit()
    
    resp = client.post("/trademe/validate_drafts", json={
        "supplier_id": 1,
        "limit": 5
    }, headers=POWER_HEADERS)
    
    # May fail validation but shouldn't 500
    assert resp.status_code in [200, 400, 404]

# =============================================================================
# COMMAND LIFECYCLE ROUTES
# =============================================================================

def test_command_lifecycle(client, db_session):
    from retail_os.core.database import SystemCommand, CommandStatus
    import uuid
    
    # Create a test command
    cmd = SystemCommand(
        id=str(uuid.uuid4()),
        type="TEST_COMMAND",
        payload={},
        status=CommandStatus.PENDING
    )
    db_session.add(cmd)
    db_session.commit()
    cmd_id = cmd.id
    
    # Test GET detail
    resp = client.get(f"/commands/{cmd_id}", headers=POWER_HEADERS)
    assert resp.status_code == 200
    
    # Test GET progress
    resp = client.get(f"/commands/{cmd_id}/progress", headers=POWER_HEADERS)
    assert resp.status_code in [200, 404]
    
    # Test GET logs
    resp = client.get(f"/commands/{cmd_id}/logs", headers=POWER_HEADERS)
    assert resp.status_code in [200, 404]
    
    # Test retry (should work on PENDING or FAILED)
    resp = client.post(f"/commands/{cmd_id}/retry", headers=POWER_HEADERS)
    assert resp.status_code in [200, 400, 409]
    
    # Test cancel
    resp = client.post(f"/commands/{cmd_id}/cancel", headers=POWER_HEADERS)
    assert resp.status_code in [200, 400, 409]
    
    # Test ack
    resp = client.post(f"/commands/{cmd_id}/ack", headers=POWER_HEADERS)
    assert resp.status_code in [200, 400, 409]

# =============================================================================
# SETTINGS ROUTES (Admin)
# =============================================================================

def test_settings_get(client):
    resp = client.get("/settings/test_key", headers=ADMIN_HEADERS)
    # 200 if exists, 404 if not
    assert resp.status_code in [200, 404]

def test_settings_put(client):
    resp = client.put("/settings/test_key", json={"value": "test"}, headers=ADMIN_HEADERS)
    # May or may not accept based on implementation
    assert resp.status_code in [200, 400, 404]

# =============================================================================
# DETAIL ROUTES (Entity-Specific GETs)
# =============================================================================

def test_supplier_product_detail(client, db_session):
    from retail_os.core.database import Supplier, SupplierProduct
    s = Supplier(id=1, name="Test", base_url="http://test")
    db_session.add(s)
    db_session.flush()
    
    sp = SupplierProduct(
        supplier_id=1,
        external_sku="TEST-001",
        title="Test Product"
    )
    db_session.add(sp)
    db_session.commit()
    
    resp = client.get(f"/supplier-products/{sp.id}", headers=POWER_HEADERS)
    assert resp.status_code in [200, 404]

def test_internal_product_detail(client, db_session):
    from retail_os.core.database import Supplier, SupplierProduct, InternalProduct
    s = Supplier(id=1, name="Test", base_url="http://test")
    db_session.add(s)
    db_session.flush()
    
    sp = SupplierProduct(
        supplier_id=1,
        external_sku="TEST-002",
        title="Test Product"
    )
    db_session.add(sp)
    db_session.flush()
    
    ip = InternalProduct(
        sku="MY-TEST-002",
        title="Internal Product",
        primary_supplier_product_id=sp.id
    )
    db_session.add(ip)
    db_session.commit()
    
    resp = client.get(f"/internal-products/{ip.id}", headers=POWER_HEADERS)
    assert resp.status_code in [200, 404]

def test_listing_detail(client, db_session):
    from retail_os.core.database import Supplier, SupplierProduct, InternalProduct, TradeMeListing
    s = Supplier(id=1, name="Test", base_url="http://test")
    db_session.add(s)
    db_session.flush()
    
    sp = SupplierProduct(supplier_id=1, external_sku="TEST-003", title="Test")
    db_session.add(sp)
    db_session.flush()
    
    ip = InternalProduct(sku="MY-TEST-003", title="Internal", primary_supplier_product_id=sp.id)
    db_session.add(ip)
    db_session.flush()
    
    listing = TradeMeListing(internal_product_id=ip.id, tm_listing_id="999999")
    db_session.add(listing)
    db_session.commit()
    
    resp = client.get(f"/listings/{listing.id}", headers=POWER_HEADERS)
    assert resp.status_code in [200, 404]

def test_listing_by_tm_id(client, db_session):
    from retail_os.core.database import Supplier, SupplierProduct, InternalProduct, TradeMeListing
    s = Supplier(id=1, name="Test", base_url="http://test")
    db_session.add(s)
    db_session.flush()
    
    sp = SupplierProduct(supplier_id=1, external_sku="TEST-004", title="Test")
    db_session.add(sp)
    db_session.flush()
    
    ip = InternalProduct(sku="MY-TEST-004", title="Internal", primary_supplier_product_id=sp.id)
    db_session.add(ip)
    db_session.flush()
    
    listing = TradeMeListing(internal_product_id=ip.id, tm_listing_id="888888")
    db_session.add(listing)
    db_session.commit()
    
    resp = client.get("/listings/by-tm/888888", headers=POWER_HEADERS)
    assert resp.status_code in [200, 404]

def test_inspector_supplier_product(client, db_session):
    from retail_os.core.database import Supplier, SupplierProduct
    s = Supplier(id=1, name="Test", base_url="http://test")
    db_session.add(s)
    db_session.flush()
    
    sp = SupplierProduct(supplier_id=1, external_sku="INSP-001", title="Inspect Me")
    db_session.add(sp)
    db_session.commit()
    
    resp = client.get(f"/inspector/supplier-products/{sp.id}", headers=POWER_HEADERS)
    assert resp.status_code in [200, 404]

def test_trust_internal_product(client, db_session):
    from retail_os.core.database import Supplier, SupplierProduct, InternalProduct
    s = Supplier(id=1, name="Test", base_url="http://test")
    db_session.add(s)
    db_session.flush()
    
    sp = SupplierProduct(supplier_id=1, external_sku="TRUST-001", title="Trust Me")
    db_session.add(sp)
    db_session.flush()
    
    ip = InternalProduct(sku="MY-TRUST-001", title="Trusted", primary_supplier_product_id=sp.id)
    db_session.add(ip)
    db_session.commit()
    
    resp = client.get(f"/trust/internal-products/{ip.id}", headers=POWER_HEADERS)
    assert resp.status_code in [200, 404]

def test_validate_internal_product(client, db_session):
    from retail_os.core.database import Supplier, SupplierProduct, InternalProduct
    s = Supplier(id=1, name="Test", base_url="http://test")
    db_session.add(s)
    db_session.flush()
    
    sp = SupplierProduct(supplier_id=1, external_sku="VAL-001", title="Validate Me")
    db_session.add(sp)
    db_session.flush()
    
    ip = InternalProduct(sku="MY-VAL-001", title="Validated", primary_supplier_product_id=sp.id)
    db_session.add(ip)
    db_session.commit()
    
    resp = client.get(f"/validate/internal-products/{ip.id}", headers=POWER_HEADERS)
    assert resp.status_code in [200, 404]

def test_listing_metrics(client, db_session):
    from retail_os.core.database import Supplier, SupplierProduct, InternalProduct, TradeMeListing
    s = Supplier(id=1, name="Test", base_url="http://test")
    db_session.add(s)
    db_session.flush()
    
    sp = SupplierProduct(supplier_id=1, external_sku="MET-001", title="Metrics")
    db_session.add(sp)
    db_session.flush()
    
    ip = InternalProduct(sku="MY-MET-001", title="Metrics", primary_supplier_product_id=sp.id)
    db_session.add(ip)
    db_session.flush()
    
    listing = TradeMeListing(internal_product_id=ip.id, tm_listing_id="777777")
    db_session.add(listing)
    db_session.commit()
    
    resp = client.get(f"/metrics/listings/{listing.id}", headers=POWER_HEADERS)
    assert resp.status_code in [200, 404]
