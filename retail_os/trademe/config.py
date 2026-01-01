
# retail_os/trademe/config.py

import os
from typing import Optional


def _env_bool(name: str, default: bool = False) -> bool:
    v = (os.getenv(name) or "").strip().lower()
    if v in {"1", "true", "yes", "y", "on"}:
        return True
    if v in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _env_int(name: str) -> Optional[int]:
    v = (os.getenv(name) or "").strip()
    if not v:
        return None
    try:
        return int(v)
    except Exception:
        return None

class TradeMeConfig:
    """
    Centralized Configuration for Trade Me Listing Defaults.
    Ref: Master Requirements Section 7 (Listing Rules).
    """
    
    # --- DURATION ---
    # Options: 2, 3, 4, 5, 6, 7, 10, 14
    DEFAULT_DURATION = 7
    
    # --- PICKUP OPTIONS ---
    # 1 = Allow Pickup
    # 2 = No Pickup
    # 3 = Demand Pickup (Must pick up)
    PICKUP_OPTION = 1 
    
    # --- PAYMENT METHODS ---
    # Supported: "BankDeposit", "CreditCard", "Cash", "Afterpay", "Ping"
    # Note: Ping/Afterpay are enabled at Account Level, so we usually just enable Bank/Cash here.
    PAYMENT_METHODS = [2, 4] # 2=Bank Deposit, 4=Cash on Pickup. (Legacy ID mappings, best to use API string enums if V1 supports them, but V1 use Integers usually)
    # Actually, simpler V1 API just takes boolean flags usually or account defaults.
    # Checks:
    # Authenticated Member defaults usually apply. 
    # We will explicitly set key fields if required. 
    
    # --- SHIPPING TEMPLATES ---
    # Operator-grade rule: no account-specific hardcoding.
    #
    # If you want to use a Trade Me "Shipping Template", set:
    #   RETAIL_OS_TM_USE_SHIPPING_TEMPLATE=true
    #   RETAIL_OS_TM_SHIPPING_TEMPLATE_ID=<your template id>
    #
    # If not configured, RetailOS uses the manual ShippingOptions fallback.
    USE_SHIPPING_TEMPLATES = _env_bool("RETAIL_OS_TM_USE_SHIPPING_TEMPLATE", default=False)
    SHIPPING_TEMPLATE_ID = _env_int("RETAIL_OS_TM_SHIPPING_TEMPLATE_ID")

    # Fallback Manual Options (Used if USE_SHIPPING_TEMPLATES is False)
    DEFAULT_SHIPPING = [
        {"Price": 7.00, "Method": "Standard Courier", "Type": 1}, # Nationwide
        {"Price": 12.00, "Method": "Rural Delivery", "Type": 1},   # Nationwide
        {"Price": 0.00, "Method": "Pick up", "Type": 3}           # Pickup
    ]
    
    # --- IMAGE RULES ---
    MAX_IMAGES = 20
    MAX_IMAGE_SIZE_MB = 5
    PREFERRED_FORMAT = "jpeg"
    
    # --- PROMOTIONAL FEATURES ---
    # Sponsored Listings / Upgrades
    # Warning: These cost money!
    USE_PROMO_FEATURES = False
    

    PROMO_FLAGS = {
        "HasGallery": True,      # Gallery Image (Usually standard now)
        "IsBold": False,         # Bold Title ($)
        "IsFeatured": False,     # Category Feature ($$)
        "IsHighlighted": False,  # Yellow Background ($)
        "IsSuperFeatured": False # Homepage Feature ($$$)
    }
    
    # --- LIFECYCLE ---
    AUTO_RELIST = True # Automatically relist unsold items?

    # --- BRANDING ---
    # Optional operator-configured footer appended to buyer-visible description.
    # Keep empty by default (no forced branding).
    LISTING_FOOTER = (os.getenv("RETAIL_OS_LISTING_FOOTER") or "").strip()
    
    # --- INTELLIGENCE MODES ---
    # "STANDARD": Normal Margins
    # "AGGRESSIVE": Lower Margins (Volume)
    # "HARVEST": Higher Margins (Profit)
    # "CLEARANCE": Liquidation
    # "CLEARANCE": Liquidation
    MODE = "STANDARD" 
    
    # --- SUPPLIER MARGINS ---
    # Power User Overrides (Supplier Name -> {pct: float, flat: float})
    # If not found, uses default Strategy rules.
    SUPPLIER_MARGIN_OVERRIDES = {
        "ONECHEQ": {"pct": 0.15, "flat": 5.00},
        "CASH_CONVERTERS": {"pct": 0.20, "flat": 10.00},
        "NOEL_LEEMING": {"pct": 0.10, "flat": 5.00}
    }
    
    @staticmethod
    def get_payment_methods():
        # Trade Me V1 "PaymentOptions" field in /Selling.json
        # 1=Bank Deposit, 2=Credit Card, 4=Cash
        # Sum of bitflags usually. 
        # Safe default: Bank Deposit (1) + Cash (4) = 5
        return 5 
