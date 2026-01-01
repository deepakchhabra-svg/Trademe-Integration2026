
# retail_os/trademe/config.py

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
    # Ideally, we pass "ShippingPresetId" if you have presets in TM.
    # Otherwise, we define manual options.
    USE_SHIPPING_TEMPLATES = True
    SHIPPING_TEMPLATE_ID = 137046  # Default: Aramex Standard ($10/$16/$24)
    
    SHIPPING_TEMPLATES = {
        "NZPOST_FREE": 159404,
        "ARAMEX_ECONOMY_LARGE": 137049,
        "ARAMEX_STANDARD": 137046,
        "ARAMEX_FREE": 135044
    }

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
    LISTING_FOOTER = """
Welcome to SOULED Store

Smart Savings: Big deals on popular brands.
Quality You Can Trust: Pre-loved & new items, carefully selected.
Discover Unique Finds: Curated collection, one-of-a-kind treasures.
"""
    
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
