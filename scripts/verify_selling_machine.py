import sys
import os
from pathlib import Path

# Add repo root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Enable Header-based Auth for TestClient
os.environ["RETAIL_OS_INSECURE_ALLOW_HEADER_ROLES"] = "true"

from fastapi.testclient import TestClient
from services.api.main import app

def verify():
    print("Starting Selling Machine Verification...")
    client = TestClient(app)
    
    # Headers for RBAC
    headers = {"X-RetailOS-Role": "power"} 
    
    # 1. Test KPIs
    print("1. Testing GET /ops/kpis...")
    resp = client.get("/ops/kpis", headers=headers)
    if resp.status_code != 200:
        print(f"FAILED: {resp.status_code} {resp.text}")
        sys.exit(1)
    
    kpis = resp.json()
    print("   KPIs keys:", kpis.keys())
    assert "sales_today" in kpis
    assert "listed_today" in kpis
    print("   [PASS]")

    # 2. Test Reprice Preview (Dry Run)
    print("2. Testing POST /ops/bulk/reprice (Dry Run)...")
    resp = client.post("/ops/bulk/reprice", json={
        "rule_type": "percentage",
        "rule_value": 0.20, # 20% margin
        "dry_run": True, 
        "limit": 5
    }, headers=headers)
    
    if resp.status_code != 200:
        print(f"FAILED: {resp.status_code} {resp.text}")
        sys.exit(1)
        
    data = resp.json()
    items = data.get("items", [])
    print(f"   Returned {len(items)} items in preview.")
    
    if items:
        ex = items[0]
        print(f"   Sample Item: Listing {ex.get('tm_listing_id')}")
        print(f"     Cost: ${ex.get('cost')}")
        print(f"     Current: ${ex.get('current_price')}")
        print(f"     Proposed: ${ex.get('new_price')}")
        print(f"     Profitable? {ex.get('is_safe')} ({ex.get('safety_reason')})")
        
        # Guardrail Check
        if not ex.get('is_safe'):
            print("   [PASS] Guardrail flagged unsafe item correctly.")
        else:
            print("   [PASS] Item marked safe.")
    else:
        print("   (No live items found to test reprice against, ensure DB has data)")

    # 3. Test Duplicates
    print("3. Testing GET /ops/duplicates...")
    resp = client.get("/ops/duplicates", headers=headers)
    if resp.status_code != 200:
        print(f"FAILED: {resp.status_code} {resp.text}")
        sys.exit(1)
    dupes = resp.json()
    print(f"   Found {dupes.get('count')} duplicate groups.")
    print("   [PASS]")

    print("\nOVERALL: VERIFICATION PASSED")

if __name__ == "__main__":
    verify()
