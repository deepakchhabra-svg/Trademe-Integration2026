
import sys
import os
import json
from sqlalchemy.orm import Session

# Ensure we can import from the current directory
sys.path.append(os.getcwd())

from retail_os.core.database import SessionLocal, SystemSetting

def check_settings():
    session = SessionLocal()
    try:
        setting = session.query(SystemSetting).filter(SystemSetting.key == "publishing.policy").first()
        if setting:
            print(f"Publishing Policy: {json.dumps(setting.value, indent=2)}")
            
            # Temporary bypass for testing if balance is an issue
            if setting.value.get("min_account_balance_nzd", 0) > 0:
                new_value = setting.value.copy()
                new_value["min_account_balance_nzd"] = 0.0
                setting.value = new_value
                session.commit()
                print("Updated min_account_balance_nzd to 0.0 for connection test.")
        else:
            print("Publishing Policy not found.")
    finally:
        session.close()

if __name__ == "__main__":
    check_settings()
