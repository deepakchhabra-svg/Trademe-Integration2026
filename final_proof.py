
import sys
import os
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

# Ensure we can import from the current directory
sys.path.append(os.getcwd())

from retail_os.core.database import SessionLocal, SystemCommand, CommandStatus, InternalProduct, TradeMeListing
from retail_os.trademe.api import TradeMeAPI
from retail_os.core.marketplace_adapter import MarketplaceAdapter

def prove_working_status():
    print("=== FINAL PROOF OF CONNECTIVITY & INTEGRATION ===\n")
    session = SessionLocal()
    api = TradeMeAPI()
    try:
        # 1. Pick a product
        prod = session.query(InternalProduct).filter(InternalProduct.sku == "OC-2000-pc-ancient-map").first()
        
        # 2. Build REAL payload
        print("1. Building real payload via MarketplaceAdapter...")
        marketplace_data = MarketplaceAdapter.prepare_for_trademe(prod.supplier_product)
        
        # 3. Upload Photo and get REAL ID
        print("2. Uploading photo to Trade Me Production...")
        with open("data/media/OC-2000-pc-ancient-map.jpg", "rb") as f:
            img_bytes = f.read()
        photo_id = api.upload_photo_idempotent(session, img_bytes)
        print(f"   [SUCCESS] Received REAL PhotoID: {photo_id}")
        
        # 4. Construct Payload
        payload = {
            "Category": marketplace_data["category_id"],
            "Title": marketplace_data["title"][:49],
            "Description": [marketplace_data["description"]],
            "Duration": 7,
            "Pickup": 1,
            "StartPrice": marketplace_data["price"],
            "PaymentOptions": 5,
            "ShippingOptions": [
                {"Price": 7.00, "Method": "Standard Courier", "Type": 1}
            ],
            "PhotoIds": [photo_id]
        }
        
        # 5. VALIDATE with Trade Me
        print("\n3. Validating complete listing package with Trade Me API...")
        val_res = api.validate_listing(payload)
        
        print(f"   Response Success: {val_res.get('Success')}")
        if val_res.get('Success'):
            print("   [SUCCESS] Trade Me accepted the listing payload as valid!")
            if val_res.get('ListingFee'):
                print(f"   Required Listing Fee: ${val_res.get('ListingFee')}")
        else:
            print(f"   [FAILURE] Trade Me rejected the payload: {val_res}")

        print("\n4. Checking Account Details again...")
        summary = api.get_account_summary()
        print(f"   Member: {summary.get('nickname')} (ID: {summary.get('member_id')})")
        print(f"   Current Balance: {summary.get('account_balance')}")

    finally:
        session.close()

if __name__ == "__main__":
    prove_working_status()
