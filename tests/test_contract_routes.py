
import pytest
from fastapi.routing import APIRoute
from services.api.main import app

def test_backend_routes_exist():
    """
    Contract: Verify that critical backend routes expected by the UI/Registry actually exist in the FastAPI app.
    """
    routes = {r.path for r in app.routes if isinstance(r, APIRoute)}
    
    # Core
    assert "/whoami" in routes
    assert "/products" in routes
    assert "/commands" in routes
    assert "/commands/{command_id}/retry" in routes
    assert "/commands/{command_id}/cancel" in routes

    # Ops
    assert "/ops/inbox" in routes
    # verify if /ops/enqueue exists if used by UI. 
    # If not, this test protects us by failing until UI is fixed or Route added.
    
    # Vaults
    assert "/vaults/live" in routes
    assert "/listings/{listing_id}" in routes

    # Validation
    assert "/inspector/supplier-products/{supplier_product_id}" in routes
    assert "/draft/internal-products/{internal_product_id}/trademe" in routes

@pytest.mark.parametrize("method, path", [
    ("POST", "/commands"),
    ("GET", "/ops/inbox"),
    ("GET", "/vaults/live"),
])
def test_critical_methods_allowed(method, path):
    """
    Contract: Confirm critical endpoints support the correct HTTP methods.
    """
    found_methods = set()
    for r in app.routes:
        if isinstance(r, APIRoute) and r.path == path:
            found_methods.update(r.methods)
    
    assert found_methods, f"Route {path} not found"
    assert method in found_methods, f"Route {path} exists but allows {found_methods}, expected {method}"
