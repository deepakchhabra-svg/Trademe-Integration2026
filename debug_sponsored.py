
import sys
import os
import json
from dotenv import load_dotenv

# Ensure we can import from the current directory
sys.path.append(os.getcwd())

from retail_os.trademe.api import TradeMeAPI

def debug_sponsored():
    print("=== Trade Me Sponsored Listings API Discovery ===\n")
    api = TradeMeAPI()
    
    endpoints = [
        "/MyTradeMe/SponsoredListings/Campaigns.json",
        "/MyTradeMe/SponsoredListings/Summary.json",
        "/Advertising/Campaigns.json",
        "/MyTradeMe/SponsoredListings.json"
    ]
    
    for ep in endpoints:
        print(f"--- Testing Endpoint: {ep} ---")
        try:
            res = api.session.get(f"https://api.trademe.co.nz/v1{ep}", timeout=10)
            print(f"Status: {res.status_code}")
            if res.status_code == 200:
                print(json.dumps(res.json(), indent=2))
            else:
                print(f"Response: {res.text[:200]}")
        except Exception as e:
            print(f"Exception: {e}")
        print("\n")

if __name__ == "__main__":
    debug_sponsored()
