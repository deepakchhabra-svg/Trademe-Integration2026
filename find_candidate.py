
import sys
import os
from sqlalchemy.orm import Session

# Ensure we can import from the current directory
sys.path.append(os.getcwd())

from retail_os.core.database import SessionLocal, SupplierProduct, InternalProduct, TradeMeListing, Supplier
from retail_os.core.validator import LaunchLock

def find_listing_candidate():
    print("=== Finding Real Listing Candidate ===\n")
    session = SessionLocal()
    try:
        validator = LaunchLock(session)
        products = session.query(InternalProduct).all()
        
        candidates = []
        for p in products:
            try:
                # We use test_mode=False to ensure trust score is also checked
                validator.validate_publish(p, test_mode=False)
                candidates.append(p)
                if len(candidates) >= 5:
                    break
            except Exception:
                continue
                
        if not candidates:
            print("No perfect candidates found passing ALL strict LaunchLock gates.")
            # Let's try to find why
            sample = products[0] if products else None
            if sample:
                print(f"\nChecking sample product {sample.sku} for blockers:")
                try:
                    validator.validate_publish(sample, test_mode=False)
                except Exception as e:
                    print(f"  - BLOCKED: {e}")
            return

        print(f"Found {len(candidates)} candidates ready for REAL listing:")
        for c in candidates:
            sp = c.supplier_product
            print(f"  - SKU: {c.sku}")
            print(f"    Title: {sp.enriched_title}")
            print(f"    Cost: ${sp.cost_price}")
            print(f"    Images: {sp.images}")
            print("-" * 20)
            
    finally:
        session.close()

if __name__ == "__main__":
    find_listing_candidate()
