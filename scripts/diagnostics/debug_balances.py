
import sys
import os
import json
from dotenv import load_dotenv

# Ensure we can import from the current directory
sys.path.append(os.getcwd())

from retail_os.trademe.api import TradeMeAPI

def debug_balances():
    print("=== Trade Me Raw Balance Debug ===\n")
    api = TradeMeAPI()
    
    endpoints = [
        "/MyTradeMe/Summary.json",
        "/Account/Balance.json",
        "/Ping/Balance.json", # Speculative
        "/MyTradeMe/Balances.json", # Speculative
    ]
    
    for ep in endpoints:
        print(f"--- Endpoint: {ep} ---")
        try:
            res = api.session.get(f"https://api.trademe.co.nz/v1{ep}", timeout=15)
            print(f"Status: {res.status_code}")
            if res.status_code == 200:
                print(json.dumps(res.json(), indent=2))
            else:
                print(f"Error Content: {res.text}")
        except Exception as e:
            print(f"Exception: {e}")
        print("\n")

if __name__ == "__main__":
    debug_balances()
