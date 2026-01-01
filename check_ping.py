
import sys
import os
import json
from dotenv import load_dotenv

# Ensure we can import from the current directory
sys.path.append(os.getcwd())

from retail_os.trademe.api import TradeMeAPI

def check_ping():
    print("=== Ping Transactions Check ===\n")
    api = TradeMeAPI()
    try:
        txs = api.get_ping_transactions()
        print(f"Fetched {len(txs)} transactions.")
        if txs:
            print("Latest Transaction:")
            print(json.dumps(txs[0], indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_ping()
