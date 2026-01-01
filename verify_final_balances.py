
import sys
import os
from sqlalchemy.orm import Session

# Ensure we can import from the current directory
sys.path.append(os.getcwd())

from retail_os.trademe.api import TradeMeAPI

def verify_balances():
    print("=== FINAL BALANCE VERIFICATION ===\n")
    api = TradeMeAPI()
    summary = api.get_account_summary()
    
    print("\nPROCESSED RESULTS:")
    print(f"Trade Me Balance (Fees): ${summary.get('account_balance')}")
    print(f"Ping Balance (Payments): ${summary.get('pay_now_balance')}")
    
    if summary.get('account_balance') == -9.0 and summary.get('pay_now_balance') == -223.98:
        print("\n[MATCH] Both balances now perfectly match the Trade Me website!")
    else:
        print("\n[MISMATCH] Check logic.")
        print(f"DEBUG: {summary}")

if __name__ == "__main__":
    verify_balances()
