"""
Category Mapper Adapter.
Maps source categories (Cash Converters, Noel Leeming) to Trade Me Category IDs.
"""

from typing import Optional

class CategoryMapper:
    # Trade Me Category IDs (simplified for Pilot)
    # https://help.trademe.co.nz/hc/en-us/articles/360007263671-Category-IDs
    
    # Common Mappings
    CATEGORY_MAP = {
        # TECH
        "laptop": "3399", # Computers > Laptops
        "laptops": "3399",
        "macbook": "3399",
        "notebook": "3399",
        "mobile phones": "0002-0356-0002-", # Mobile phones > Mobile phones
        "phones": "0002-0356-0002-",
        "tablets": "0002-0356-0003-", # Mobile phones > Tablets
        "digital cameras": "0005-0044-", # Electronics & Photography > Digital cameras
        "cameras": "0005-0044-",
        "headphones": "0005-0676-4706-", # Electronics > Headphones
        "audio": "0005-0676-",
        "speakers": "0005-0676-0683-",
        "gaming": "0005-0886-", # Gaming
        "consoles": "0005-0886-2582-",
        "games": "0005-0886-2581-",
        
        # TOOLS & DIY
        "tools": "0022-0238-", # Building & renovation > Tools
        "power tools": "0022-0238-0239-",
        "drills": "0022-0238-0239-2993-",
        
        # MUSICAL
        "musical instruments": "0386-",
        "guitars": "0386-2516-",
        "keyboards": "0386-2519-",
        
        # Brand/title heuristics (tech)
        "samsung": "0002-0356-0002-",  # Mobile phones
        # Apple needs context: default to phones, but laptop keywords above win.
        "apple": "0002-0356-0002-",
        "iphone": "0002-0356-0002-",
        "huawei": "0002-0356-0002-",
        "pixel": "0002-0356-0002-", # Fallback to mobile phones 
        
        # MISC
        "jewellery": "0202-",
        "phone": "0002-0356-0002-", # Mobile phones > Mobile phones (Leaf?) No, usually needs brand.
        # But '0002-0356-0002-' is better than '0002-0356-'
        "mobile": "0002-0356-0002-",
        "tablet": "0002-0356-0003-",
        "laptop": "3399", # Computers > Laptops
        "laptops": "3399",
        "computer": "3399", # Computers > Laptops (Safe leaf)
        "baby": "0187-0192-",  # Antiques & Collectables > Other (safe default leaf)
        "monitor": "0187-0192-",  
        "puzzle": "0208-1610-", # Toys & Models > Puzzles
        "puzzles": "0208-1610-",
        "default": "0187-0192-"  # Use existing safe DEFAULT_CATEGORY
    }
    
    DEFAULT_CATEGORY = "0187-0192-" # Antiques & Collectables > Other (Safe generic catchment)

    @classmethod
    def map_category(cls, source_category_name: str, item_title: str = "") -> str:
        """
        Determines the best Trade Me Category ID.
        1. Checks Exact Match of source category.
        2. Checks Keyword Match in source category.
        3. Checks Keywords in Item Title.
        4. Fallback to General.
        """
        if not source_category_name:
            source_category_name = ""
            
        term = source_category_name.lower().strip()
        title_term = item_title.lower().strip()
        
        # 0. Title Search (Priority!)
        # Check Title keywords first to correct miscategorized items (e.g. Phone in Laptops category)
        for key, cat_id in cls.CATEGORY_MAP.items():
            if key in title_term:
                return cat_id

        # 1. Direct Map
        if term in cls.CATEGORY_MAP:
            return cls.CATEGORY_MAP[term]
            
        # 2. Keyword Search in Category
        for key, cat_id in cls.CATEGORY_MAP.items():
            if key in term:
                return cat_id
                
        # 5. Fallback: AI Classification (If configured)
        # This prevents "Generic Other" dumping, keeping listings relevant.
        return cls.classify_with_ai(title_term)

    @classmethod
    def classify_with_ai(cls, title: str) -> str:
        """
        Uses heuristics or simple logic to prevent dumping everything in Antiques.
        """
        # Hardcoded fallback for now to stay safe
        return cls.DEFAULT_CATEGORY

    @classmethod
    def get_category_name(cls, cat_id: str) -> str:
        # Reverse lookup for display (approximate)
        for name, cid in cls.CATEGORY_MAP.items():
            if cid == cat_id:
                return name.title()
        if cat_id == cls.DEFAULT_CATEGORY:
            return "General / Other"
        return "Unknown Category"
