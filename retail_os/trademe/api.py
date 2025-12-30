import os
import json
import hashlib
import time
import re
import requests
from requests_oauthlib import OAuth1
from datetime import datetime
from sqlalchemy.orm import Session
from retail_os.core.database import PhotoHash
from dotenv import load_dotenv

# Config
# Ideally this comes from a Config class, but simple env vars for now
PROD_URL = "https://api.trademe.co.nz/v1"
TIMEOUT_SECS = 30
MAX_RETRIES = 3

class TradeMeAPI:
    def __init__(self):
        # Load dotenv if present (repo-root anchored), without requiring callers to do it.
        # This does NOT print secrets; it just allows local/dev to work when a .env exists.
        try:
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            load_dotenv(os.path.join(repo_root, ".env"), override=False)
            load_dotenv(override=False)
        except Exception:
            pass

        consumer_key = os.getenv("CONSUMER_KEY")
        consumer_secret = os.getenv("CONSUMER_SECRET")
        access_token = os.getenv("ACCESS_TOKEN")
        access_token_secret = os.getenv("ACCESS_TOKEN_SECRET")
        
        if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
            raise ValueError("Credentials missing in Environment")
            
        self.auth = OAuth1(consumer_key, consumer_secret, access_token, access_token_secret)
        self.session = requests.Session()
        self.session.auth = self.auth

    def _hash_bytes(self, b: bytes) -> str:
        return hashlib.xxhash64(b).hexdigest() if hasattr(hashlib, 'xxhash64') else hashlib.md5(b).hexdigest()

    def upload_photo_idempotent(self, db_session: Session, image_bytes: bytes, filename: str = "image.jpg") -> int:
        """
        Uploads a photo if not already uploaded.
        Returns: TradeMe PhotoID (int).
        Raises: Exception on failure.
        """
        # 1. Compute Hash
        img_hash = self._hash_bytes(image_bytes)
        
        # 2. Check Cache
        cached = db_session.query(PhotoHash).filter_by(hash=img_hash).first()
        if cached:
            print(f"API: Photo Cache Hit ({img_hash} -> {cached.tm_photo_id})")
            return cached.tm_photo_id
            
        # 3. Upload (JSON Base64 - Verified Working)
        print(f"API: Uploading Photo ({len(image_bytes)} bytes)...")
        import base64
        try:
             b64_str = base64.b64encode(image_bytes).decode('utf-8')
             # Infer filetype from filename or default to jpg? 
             # Logic: split ext.
             parts = filename.split('.')
             ext = parts[-1] if len(parts) > 1 else 'jpg'
             
             payload = {
                 "PhotoData": b64_str,
                 "FileName": filename,
                 "FileType": ext
             }
        
             res = self.session.post(f"{PROD_URL}/Photos.json", json=payload, timeout=TIMEOUT_SECS)
             res.raise_for_status()
             
             resp_json = res.json()
             if resp_json.get("Status") == 1:
                 photo_id = resp_json.get("PhotoId")
                 
                 # 4. Update Cache
                 new_cache = PhotoHash(hash=img_hash, tm_photo_id=photo_id)
                 db_session.add(new_cache)
                 db_session.commit()
                 
                 return photo_id
             else:
                 raise Exception(f"Photo Upload Logic Failure: {resp_json}")
                 
        except Exception as e:
            # Platform Error (Circuit Breaker Logic would handle this upstream)
            raise Exception(f"Photo Upload Failed: {e}")

    def validate_listing(self, payload: dict) -> dict:
        """
        Simulate a listing.
        Returns: API Response Dict.
        """
        print("API: Validating Payload...")
        try:
            res = self.session.post(f"{PROD_URL}/Selling/Validate.json", json=payload, timeout=TIMEOUT_SECS)
            # We don't raise_for_status purely because 400 is a valid logic result (Success=False)
            return res.json()
        except Exception as e:
            raise Exception(f"Validation Network Error: {e}")

    def publish_listing(self, payload: dict) -> int:
        """
        Execute the Write.
        Returns: ListingID (int).
        Raises: Exception (Timeout/500).
        """
        print("API: Publishing Listing...")
        res = self.session.post(f"{PROD_URL}/Selling.json", json=payload, timeout=TIMEOUT_SECS)
        res.raise_for_status()
        
        data = res.json()
        if data.get("Success"):
            return data.get("ListingId")
        else:
            raise Exception(f"Publish Logic Failure: {data}")

    def get_listing_details(self, listing_id: str) -> dict:
        """
        Read-Back Verification.
        Parses 'Asking price $50.00' into Floats.
        """
        print(f"API: Reading Listing {listing_id}...")
        res = self.session.get(f"{PROD_URL}/Listings/{listing_id}.json", timeout=TIMEOUT_SECS)
        
        if res.status_code == 400:
             # ID doesn't exist or archived
             return None
             
        res.raise_for_status()
        raw = res.json()
        
        # Strict Parser Logic
        parsed = {
            "ListingId": raw.get("ListingId"),
            "Title": raw.get("Title"),
            "Category": raw.get("Category"),
            "StartPrice": raw.get("StartPrice"),
            "BuyNowPrice": raw.get("BuyNowPrice"),
            "PriceDisplay": raw.get("PriceDisplay"),
            "ViewCount": raw.get("ViewCount", 0),
            "WatchCount": raw.get("BidderAndWatchers", 0), # Usually combined in TM API
        }
        
        # Text -> Float Parser
        # "Asking price $350,000" -> 350000.0
        # "Buy Now $50.00" -> 50.0
        price_text = raw.get("PriceDisplay", "")
        if price_text:
             clean_price = re.sub(r'[^\d.]', '', price_text)
             try:
                 parsed["ParsedPrice"] = float(clean_price)
             except:
                 parsed["ParsedPrice"] = 0.0
        
        return parsed

    def withdraw_listing(self, listing_id: str) -> bool:
        """
        Withdraws a live listing.
        """
        print(f"API: Withdrawing Listing {listing_id}...")
        # Endpoint: POST /Selling/Withdraw.json
        payload = {
            "ListingId": int(listing_id),
            "Type": 2, # 2 = ListingWasNotSold
            "Reason": "Integration Logic Test"
        }
        
        try:
            res = self.session.post(f"{PROD_URL}/Selling/Withdraw.json", json=payload, timeout=TIMEOUT_SECS)
            res.raise_for_status()
            data = res.json()
            if not data.get("Success"):
                print(f"API DEBUG: Withdraw Failed Response: {data}")
            return data.get("Success", False)
        except Exception as e:
            raise Exception(f"Withdraw Failed: {e}")

    def update_listing(self, payload: dict) -> dict:
        """
        Updates an existing listing.
        Trade Me V1 endpoint (commonly): POST /Selling/Update.json
        NOTE: Field support depends on account/category.
        """
        print("API: Updating Listing...")
        try:
            res = self.session.post(f"{PROD_URL}/Selling/Update.json", json=payload, timeout=TIMEOUT_SECS)
            res.raise_for_status()
            return res.json()
        except Exception as e:
            raise Exception(f"Update Listing Failed: {e}")

    def update_price(self, listing_id: str, new_price: float) -> bool:
        """
        Attempts to update listing price.
        Uses /Selling/Update.json with StartPrice.
        """
        payload = {"ListingId": int(listing_id), "StartPrice": float(new_price)}
        data = self.update_listing(payload)
        if data.get("Success") is True:
            return True
        raise Exception(f"Update Price Failed: {data}")

    def get_all_selling_items(self) -> list:
        """
        Fetches all currently selling items.
        Returns: List of Dicts.
        """
        print("API: Fetching All Selling Items...")
        # Endpoint: GET /MyTradeMe/SellingItems.json
        try:
            res = self.session.get(f"{PROD_URL}/MyTradeMe/SellingItems.json", timeout=TIMEOUT_SECS)
            res.raise_for_status()
            data = res.json()
            # The API returns specific list key 'List'
            lst = data.get("List", [])
            if not lst:
                print(f"API DEBUG: Raw Response Keys: {data.keys()}")
                print(f"API DEBUG: TotalCount: {data.get('TotalCount')}")
            return lst
        except Exception as e:
            raise Exception(f"Fetch Selling Failed: {e}")

    def get_sold_items(self, days: int = 7) -> list:
        """
        Fetches items sold in the last X days.
        """
        print(f"API: Fetching Sold Items (Last {days} days)...")
        # Endpoint: GET /MyTradeMe/SoldItems.json
        # Filter: filter=Last45Days (Trade Me default is 45 days)
        try:
            res = self.session.get(f"{PROD_URL}/MyTradeMe/SoldItems.json?filter=Last45Days", timeout=TIMEOUT_SECS)
            res.raise_for_status()
            data = res.json()
            lst = data.get("List", [])
            
            # Client-side filter for 'days'
            cutoff = datetime.utcnow().timestamp() - (days * 86400)
            
            recent_sales = []
            for item in lst:
                # "SoldDateHint": "/Date(1671234567000)/"
                date_str = item.get("SoldDateHint", "")
                ts_match = re.search(r'\d+', date_str)
                if ts_match:
                    ts = int(ts_match.group(0)) / 1000.0
                    if ts >= cutoff:
                        recent_sales.append(item)
                        
            return recent_sales
        except Exception as e:
            raise Exception(f"Fetch Sold Failed: {e}")

    def get_unsold_items(self) -> list:
        """
        Fetches items that expired without selling in the last 45 days.
        Ref: Critical for Relist Cycle.
        """
        print("API: Fetching Unsold Items...")
        try:
            res = self.session.get(f"{PROD_URL}/MyTradeMe/UnsoldItems.json?filter=Last45Days", timeout=TIMEOUT_SECS)
            res.raise_for_status()
            return res.json().get("List", [])
        except Exception as e:
            raise Exception(f"Fetch Unsold Failed: {e}")

    def relist_item(self, listing_id: int) -> int:
        """
        Relists an expired item.
        Returns: New Listing ID.
        """
        print(f"API: Relisting Item {listing_id}...")
        payload = {
            "ListingId": listing_id,
            "ReturnListingDetails": False
        }
        try:
            res = self.session.post(f"{PROD_URL}/Selling/Relist.json", json=payload, timeout=TIMEOUT_SECS)
            res.raise_for_status()
            data = res.json()
            if data.get("Success"):
                print(f"   -> Relist Success. New ID: {data.get('ListingId')}")
                return data.get("ListingId")
            else:
                raise Exception(f"Relist Logic Failure: {data}")
        except Exception as e:
            raise Exception(f"Relist Network Error: {e}")

    def get_account_summary(self) -> dict:
        """
        Gets account summary including balance, member info, etc.
        Returns: Dict with account details.
        """
        print("API: Fetching Account Summary...")
        try:
            # 1) Member summary (identity + reputation)
            res = self.session.get(f"{PROD_URL}/MyTradeMe/Summary.json", timeout=TIMEOUT_SECS)
            res.raise_for_status()
            data = res.json()

            # 2) Balances endpoint (matches "My balances" screen more closely)
            bal = {}
            bal_err = None
            try:
                r2 = self.session.get(f"{PROD_URL}/Account/Balance.json", timeout=TIMEOUT_SECS)
                r2.raise_for_status()
                bal = r2.json() if isinstance(r2.json(), dict) else {}
            except Exception:
                bal = {}
                bal_err = "Balance endpoint not available for this account/app"

            # Prefer Balance.json if present; fallback to Summary.json fields.
            account_balance = bal.get("Balance")
            if account_balance is None:
                # IMPORTANT: do not default to 0.0 (looks like “real $0”).
                # If Summary doesn't provide a balance, return None + diagnostic instead.
                account_balance = data.get("AccountBalance", None)

            # Parse and return key fields
            return {
                "member_id": data.get("MemberId"),
                "nickname": data.get("Nickname"),
                "email": data.get("Email"),
                "account_balance": account_balance,
                "pay_now_balance": data.get("PayNowBalance", None),
                "unique_positive": data.get("UniquePositive", None),
                "unique_negative": data.get("UniqueNegative", None),
                "feedback_count": data.get("FeedbackCount", None),
                "total_items_sold": data.get("TotalItemsSold", None),
                # Extra diagnostics (safe)
                "balance_raw": bal,
                "balance_error": bal_err,
            }
        except Exception as e:
            raise Exception(f"Get Account Summary Failed: {e}")

    def get_member_ledger(self, period: str = "Last28Days") -> list:
        """
        Gets member ledger transactions.
        Args:
            period: Last7Days, Last28Days, Last45Days
        Returns: List of transaction dicts.
        """
        print(f"API: Fetching Member Ledger ({period})...")
        try:
            res = self.session.get(f"{PROD_URL}/MyTradeMe/MemberLedger/{period}.json", timeout=TIMEOUT_SECS)
            if res.status_code == 404:
                # Endpoint not available or no data
                return []
            res.raise_for_status()
            data = res.json()
            return data.get("List", [])
        except Exception as e:
            print(f"   -> Member Ledger fetch failed: {e}")
            return []

    def get_paynow_ledger(self) -> list:
        """
        Gets PayNow ledger entries.
        Returns: List of PayNow transaction dicts.
        """
        print("API: Fetching PayNow Ledger...")
        try:
            res = self.session.get(f"{PROD_URL}/MyTradeMe/PayNowLedger/All.json", timeout=TIMEOUT_SECS)
            if res.status_code == 404:
                # PayNow not enabled
                return []
            res.raise_for_status()
            data = res.json()
            return data.get("List", [])
        except Exception as e:
            print(f"   -> PayNow Ledger not available: {e}")
            return []

    def get_ping_transactions(self, limit: int = 50) -> list:
        """
        Gets Ping balance ledger transactions.
        Args:
            limit: Number of transactions to return
        Returns: List of Ping transaction dicts.
        """
        print(f"API: Fetching Ping Transactions (limit={limit})...")
        try:
            res = self.session.get(f"{PROD_URL}/Ping/Transactions.json", timeout=TIMEOUT_SECS)
            if res.status_code == 404:
                # Ping not available
                return []
            res.raise_for_status()
            data = res.json()
            transactions = data.get("List", [])
            return transactions[:limit]
        except Exception as e:
            print(f"   -> Ping Transactions not available: {e}")
            return []
