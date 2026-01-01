"""
Category Mapper Adapter.
Maps source categories (Cash Converters, Noel Leeming) to Trade Me Category IDs.
"""

from retail_os.core.trademe_categories import TradeMeCategories

class CategoryMapper:
    """
    Operator-grade rule:
    - Mapping must be deterministic and conservative (no "AI guessing" / no fuzzy free-text scoring).
    - If we can't map confidently, return DEFAULT_CATEGORY (which downstream treats as BLOCKED).
    """

    # Safe generic catchment (still BLOCKED for publish if it remains the default).
    DEFAULT_CATEGORY = "0187-0192-"  # Antiques-collectables > Other

    # Deterministic keyword mappings using official Trade Me taxonomy IDs (4-digit padded segments).
    CATEGORY_MAP: dict[str, str] = {
        # Computers > Laptops > Other  (Full Code 2-356-807)
        "laptop": "0002-0356-0807-",
        "laptops": "0002-0356-0807-",
        "notebook": "0002-0356-0807-",
        "macbook": "0002-0356-0807-",
        "chromebook": "0002-0356-0807-",
        "gaming laptop": "0002-0356-0807-",
        # Computers > Tablets-Ebook-readers > Tablets (Full Code 2-9844-4720)
        "tablet": "0002-9844-4720-",
        "tablets": "0002-9844-4720-",
        "ipad": "0002-9844-4720-",
        # Mobile-phones > Mobile-phones > Other (Full Code 344-422-510)
        "phone": "0344-0422-0510-",
        "phones": "0344-0422-0510-",
        "mobile phone": "0344-0422-0510-",
        "mobile phones": "0344-0422-0510-",
        "iphone": "0344-0422-0430-0431-",  # iPhone > iPhone (Full Code 344-422-430-431)
        # Building-renovation > Tools > Power-tools > Drills-screwdrivers (Full Code 5964-5999-6015-6016)
        "drill": "5964-5999-6015-6016-",
        "drills": "5964-5999-6015-6016-",
        "drill driver": "5964-5999-6015-6016-",
        "screwdriver": "5964-5999-6015-6016-",
        # Toys-models > Games-puzzles-tricks > Puzzles > Other (Full Code 347-920-6792-6795)
        "puzzle": "0347-0920-6792-6795-",
        "puzzles": "0347-0920-6792-6795-",
        "jigsaw": "0347-0920-6792-6795-",
        "jigsaws": "0347-0920-6792-6795-",
        # Health-beauty > Bath-shower > Body-wash (Full Code 4798-4808-4814)
        "body wash": "4798-4808-4814-",
        "bodywash": "4798-4808-4814-",
        "shower gel": "4798-4808-4814-",
        "cleanser": "4798-4808-4814-",
    }

    @classmethod
    def map_category(cls, source_category_name: str, item_title: str = "", item_description: str = "") -> str:
        """
        Determines the best Trade Me Category ID.
        1. Checks Exact Match of source category.
        2. Checks Keyword Match in source category.
        3. Checks Keywords in Item Title.
        4. Fallback to General.
        """
        if not source_category_name:
            source_category_name = ""
            
        term = (source_category_name or "").lower().strip()
        title_term = (item_title or "").lower().strip()
        desc_term = (item_description or "").lower().strip()
        
        # 0. Title Search (Priority!)
        # Check Title keywords first to correct miscategorized items (e.g. Phone in Laptops category)
        # 0) Phrase-first match (title/description), then source category.
        # Keep this deterministic and conservative.
        for key, cat_id in cls.CATEGORY_MAP.items():
            if key in title_term or key in desc_term:
                return cat_id

        # 1. Direct Map
        if term in cls.CATEGORY_MAP:
            return cls.CATEGORY_MAP[term]
            
        # 2. Keyword Search in Category
        for key, cat_id in cls.CATEGORY_MAP.items():
            if key in term:
                return cat_id
                
        # 5) Final fallback (blocked).
        return cls.classify_with_ai(title_term)

    @classmethod
    def classify_with_ai(cls, title: str) -> str:
        """
        Legacy name: deterministic fallback.
        """
        return cls.DEFAULT_CATEGORY

    @classmethod
    def get_category_name(cls, cat_id: str) -> str:
        official = TradeMeCategories.name(cat_id)
        if official:
            return official
        if cat_id == cls.DEFAULT_CATEGORY:
            return "General / Other"
        return "Unknown Category"
