"""
Unified product schema for multi-source scraping pipeline.

Defines the standard dictionary structure that all Adapters must produce 
before writing to the Database.
"""

from typing import TypedDict, Optional

# Standard field names across all sources
UNIFIED_FIELDNAMES = [
    # ===== Core Identifiers =====
    "source_listing_id",        # Source-specific product/listing ID (e.g. SKU)
    "source",                   # Source name (cashconverters, noel_leeming, etc.)
    "source_url",              # Original product URL
    
    # ===== Product Information =====
    "title",                   # Product title
    "description",             # Product description
    "brand",                   # Brand name
    "condition",               # Item condition (New, Used)
    
    # ===== Pricing =====
    "reserve_price",           # Reserve/starting price
    "buy_now_price",           # Buy now price
    "source_current_price",    # Original source price (for verification)
    "buy_now_only",            # Yes/No
    "allow_buy_now",           # Yes/No
    
    # ===== Categorization =====
    "source_category",         # Original source category path
    "category",                # Mapped TradeMe category ID
    
    # ===== Location & Store =====
    "store_name",              # Store/seller name
    "store_location",          # Store location
    
    # ===== Images =====
    "photo1", "photo2", "photo3", "photo4",
    
    # ===== Metadata =====
    "warranty",                # Warranty info
    "ean",                     # EAN/barcode
    "source_status",           # Active/Sold/Hidden
    "scraped_at",              # ISO timestamp
    "price_match_verified",    # Yes/No
]

class UnifiedProduct(TypedDict, total=False):
    """TypedDict for unified product schema."""
    source_listing_id: str
    source: str
    source_url: str
    title: str
    description: str
    brand: str
    condition: str
    reserve_price: str
    buy_now_price: str
    source_current_price: str
    buy_now_only: str
    allow_buy_now: str
    source_category: str
    category: str
    store_name: str
    store_location: str
    photo1: str
    photo2: str
    photo3: str
    photo4: str
    warranty: str
    ean: str
    source_status: str
    scraped_at: str
    price_match_verified: str
    
    # Ranking Metadata
    collection_rank: int
    collection_page: int

def normalize_noel_leeming_row(nl_row: dict) -> UnifiedProduct:
    """Convert Noel Leeming V1 scraper raw output to UnifiedProduct."""
    price = str(nl_row.get("price", 0.0))
    
    return {
        "source_listing_id": str(nl_row.get("source_listing_id", nl_row.get("source_id", ""))),
        "source": "noel_leeming",
        "source_url": nl_row.get("url", ""),
        "title": nl_row.get("title", ""),
        "description": nl_row.get("description", nl_row.get("title", "")), 
        "brand": nl_row.get("brand", ""),
        "condition": "New",
        "reserve_price": "",
        "buy_now_price": price,
        "source_current_price": price,
        "buy_now_only": "Yes",
        "allow_buy_now": "No",
        "source_category": str(nl_row.get("category", "")),
        "category": "",
        "store_name": "Noel Leeming",
        "store_location": "New Zealand",
        "photo1": nl_row.get("photo1", nl_row.get("image_url", "")),
        "photo2": nl_row.get("photo2", ""),
        "photo3": nl_row.get("photo3", ""),
        "photo4": nl_row.get("photo4", ""),
        "warranty": "",
        "ean": str(nl_row.get("ean", "")),
        "source_status": "Active",
        "scraped_at": "", 
        "price_match_verified": "No",
        
        # Extra fields (passed through for Adapter)
        "collection_rank": nl_row.get("noel_leeming_rank"),
        "collection_page": nl_row.get("page_number"),
    }

# NOTE: normalize_cash_converters_row was removed - CashConvertersAdapter uses its own
# normalize_row() method for better encapsulation.

def normalize_onecheq_row(oc_row: dict) -> UnifiedProduct:
    """Convert OneCheq scraper output to UnifiedProduct."""
    price = str(oc_row.get("buy_now_price", 0.0))
    
    return {
        "source_listing_id": str(oc_row.get("source_id", "")),
        "source": "onecheq",
        "source_url": oc_row.get("source_url", ""),
        "title": oc_row.get("title", ""),
        "description": oc_row.get("description", oc_row.get("title", "")),  # Fallback to title
        "brand": oc_row.get("brand", ""),
        "condition": oc_row.get("condition", "Used"),
        "reserve_price": "",
        "buy_now_price": price,
        "source_current_price": price,
        "buy_now_only": "Yes",
        "allow_buy_now": "Yes",
        "source_category": "",
        "category": "",
        "store_name": "OneCheq",
        "store_location": "New Zealand",
        "photo1": oc_row.get("photo1", ""),
        "photo2": oc_row.get("photo2", ""),
        "photo3": oc_row.get("photo3", ""),
        "photo4": oc_row.get("photo4", ""),
        # Pass through structured specs for enrichment/publish quality.
        # Stored in SupplierProduct.specs by the adapter.
        "specs": oc_row.get("specs") or {},
        "warranty": "",
        "ean": "",
        "source_status": oc_row.get("source_status", "Available"),
        "scraped_at": "",  # Filled by Adapter if needed
        "price_match_verified": "No",
        
        # Extra fields (passed through for Adapter)
        "collection_rank": oc_row.get("collection_rank"),
        "collection_page": oc_row.get("collection_page"),
    }

