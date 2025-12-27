"""
TradeMe Account Balance Check
Tests account balance and transaction endpoints
"""
import sys
import os
sys.path.append(os.getcwd())

from dotenv import load_dotenv
load_dotenv()

from retail_os.trademe.api import TradeMeAPI
import json

def check_account_balance():
    print("=== TradeMe Account Balance Check ===\n")
    
    api = TradeMeAPI()
    
    # 1. MyTradeMe Summary (Account Balance)
    print("1. Fetching Account Summary...")
    try:
        res = api.session.get("https://api.trademe.co.nz/v1/MyTradeMe/Summary.json", timeout=30)
        if res.status_code == 200:
            data = res.json()
            print(f"   Account Balance: ${data.get('AccountBalance', 'N/A')}")
            print(f"   Pay Now Balance: ${data.get('PayNowBalance', 'N/A')}")
            print(f"   Member ID: {data.get('MemberId', 'N/A')}")
            print(f"   Nickname: {data.get('Nickname', 'N/A')}")
            print(f"   Email: {data.get('Email', 'N/A')}")
            print(f"   Unique Negative: {data.get('UniqueNegative', 'N/A')}")
            print(f"   Unique Positive: {data.get('UniquePositive', 'N/A')}")
        else:
            print(f"   ERROR: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # 2. Member Ledger (Transactions)
    print("\n2. Fetching Member Ledger (Recent Transactions)...")
    try:
        res = api.session.get("https://api.trademe.co.nz/v1/MyTradeMe/MemberLedger.json", timeout=30)
        if res.status_code == 200:
            data = res.json()
            ledger = data.get('List', [])
            print(f"   Total Transactions: {len(ledger)}")
            if ledger:
                print("\n   Recent Transactions (Last 5):")
                for i, tx in enumerate(ledger[:5]):
                    ref = tx.get('ReferenceNumber', 'N/A')
                    desc = tx.get('Description', 'N/A')
                    amount = tx.get('Amount', 0)
                    date = tx.get('Date', 'N/A')
                    print(f"     {i+1}. [{ref}] {desc} - ${amount} ({date})")
        else:
            print(f"   ERROR: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # 3. Current Selling Items
    print("\n3. Fetching Current Selling Items...")
    try:
        selling = api.get_all_selling_items()
        print(f"   Active Listings: {len(selling)}")
        if selling:
            for i, item in enumerate(selling[:3]):
                title = item.get('Title', 'N/A')
                price = item.get('PriceDisplay', 'N/A')
                print(f"     {i+1}. {title} - {price}")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    print("\n=== END ===")

if __name__ == "__main__":
    check_account_balance()
