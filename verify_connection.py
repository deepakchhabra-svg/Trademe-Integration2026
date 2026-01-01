
import sys
import os
import json
from dotenv import load_dotenv

# Ensure we can import from the current directory
sys.path.append(os.getcwd())

from retail_os.trademe.api import TradeMeAPI

def verify_trademe_connection():
    print("=== TradeMe Connectivity & Credentials Verification ===\n")
    
    try:
        api = TradeMeAPI()
        print("[SUCCESS] TradeMeAPI initialized correctly (Credentials found in .env)")
    except Exception as e:
        print(f"[FAILURE] TradeMeAPI initialization failed: {e}")
        return

    # 1. Test Account Summary (Read test)
    print("\n1. Testing Account Summary (Read Test)...")
    try:
        summary = api.get_account_summary()
        print(f"   [SUCCESS] Account Summary Fetched.")
        print(f"   Member ID: {summary.get('member_id')}")
        print(f"   Nickname:  {summary.get('nickname')}")
        print(f"   Email:     {summary.get('email')}")
        print(f"   Balance:   {summary.get('account_balance')}")
        
        # Diagnostic info
        diag = summary.get('diagnostics', {})
        print(f"   Summary Endpoint: {diag.get('summary_endpoint')} (Status: {diag.get('summary_status_code')})")
        print(f"   Balance Endpoint: {diag.get('balance_endpoint')} (Status: {diag.get('balance_status_code')})")
        if summary.get('balance_error'):
            print(f"   Balance Error:    {summary.get('balance_error')}")
            
    except Exception as e:
        print(f"   [FAILURE] Account Summary fetch failed: {e}")

    # 2. Test Listings Fetch (Read test)
    print("\n2. Testing Listings Fetch...")
    try:
        listings = api.get_all_selling_items()
        print(f"   [SUCCESS] Selling Items Fetched. Count: {len(listings)}")
    except Exception as e:
        print(f"   [FAILURE] Selling Items fetch failed: {e}")

    # 3. Test Category Fetch (Public API test via OAuth)
    print("\n3. Testing Category Fetch (Internal API check)...")
    try:
        res = api.session.get("https://api.trademe.co.nz/v1/Categories.json", timeout=10)
        if res.status_code == 200:
            print(f"   [SUCCESS] Categories fetched successfully.")
        else:
            print(f"   [FAILURE] Category fetch returned status: {res.status_code}")
    except Exception as e:
        print(f"   [FAILURE] Category fetch failed: {e}")

    print("\n=== VERIFICATION COMPLETE ===")

if __name__ == "__main__":
    verify_trademe_connection()
