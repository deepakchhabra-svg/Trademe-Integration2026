
import pytest
import os
import json
import re
from fastapi.routing import APIRoute
from services.api.main import app

REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "../docs/operations_registry.json")

def parse_params(path: str) -> set[str]:
    """Extract {param} placeholders from a path string."""
    return set(re.findall(r"\{([a-zA-Z0-9_]+)\}", path))

def test_registry_full_coverage():
    """
    Contract: Validate EVERY operation in operations_registry.json:
    1. URI maps to a real backend route.
    2. HTTP method matches.
    3. Path parameters match exactly (name and count).
    """
    if not os.path.exists(REGISTRY_PATH):
        pytest.skip("operations_registry.json not found")

    with open(REGISTRY_PATH, "r") as f:
        registry = json.load(f)

    # Build map of Backend Routes: Path -> Method -> RouteObj
    backend_routes = {}
    for r in app.routes:
        if isinstance(r, APIRoute):
            # FastAPI paths are like /foo/{bar}
            # We index by path to check existence
            if r.path not in backend_routes:
                backend_routes[r.path] = {}
            for m in r.methods:
                backend_routes[r.path][m] = r

    operations = registry.get("operations", {})
    if isinstance(operations, dict):
        op_iterator = operations.items()
    elif isinstance(operations, list):
        # normalize to dict-like
        op_iterator = [(op.get("operation_id"), op) for op in operations]
    else:
        pytest.fail("Registry operations invalid format")

    errors = []

    for op_id, op in op_iterator:
        if not isinstance(op, dict): 
            continue
            
        uri = op.get("uri")
        method = op.get("method", "GET").upper()
        
        # 1. Check URI existence
        if uri not in backend_routes:
            errors.append(f"[{op_id}] URI {uri} not found in backend.")
            continue
            
        # 2. Check Method
        if method not in backend_routes[uri]:
            errors.append(f"[{op_id}] Method {method} not supported for {uri}. Allowed: {list(backend_routes[uri].keys())}")
            continue
            
        # 3. Check Params implicitly verified by exact string match of URI
        # If registry has /foo/{id} and backend has /foo/{supplier_id}, string match fails in step 1.
        
    if errors:
        pytest.fail("\n".join(errors))
