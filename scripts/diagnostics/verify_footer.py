
import sys
import os
from sqlalchemy.orm import Session

# Ensure we can import from the current directory
sys.path.append(os.getcwd())

from retail_os.core.database import SessionLocal, InternalProduct
from retail_os.core.marketplace_adapter import MarketplaceAdapter

def verify_footer():
    print("=== Listing Footer Verification ===\n")
    session = SessionLocal()
    try:
        # Pick the same product we used for testing
        prod = session.query(InternalProduct).filter(InternalProduct.sku == "OC-2000-pc-ancient-map").first()
        if not prod:
            print("Product not found.")
            return

        print(f"Product: {prod.sku}")
        marketplace_data = MarketplaceAdapter.prepare_for_trademe(prod.supplier_product)
        
        desc = marketplace_data["description"]
        print("\n--- Final Description ---")
        print(desc)
        
        if "Welcome to SOULED Store" in desc:
            print("\n[SUCCESS] Footer correctly appended!")
        else:
            print("\n[FAILURE] Footer missing.")

    finally:
        session.close()

if __name__ == "__main__":
    verify_footer()
