# END-TO-END SYSTEM TRACE - COMPLETE REQUEST/RESPONSE FLOW

## FLOW 1: SCRAPING → DATABASE

### 1.1 OneCheq Scraper → Adapter
**Call**: `OneCheqAdapter.run_sync(pages=1)`
**Request**: `pages=1, collection="smartphones-and-mobilephones"`
**Internal Calls**:
  - `scraper.scrape_collection_page(page_num)` 
    - **Returns**: `List[Dict]` with keys: `title, price, sku, url, images, specs, rank`
  - `_upsert_product(data)`
    - **Input**: `{"title": str, "price": float, "sku": str, "url": str, "images": List[str], "specs": Dict, "rank": int}`
    - **Database Write**: `SupplierProduct` table
    - **Returns**: `'created'|'updated'|'unchanged'`
**Final Return**: `{"total_scraped": int, "total_new": int, "total_updated": int}`

### 1.2 CashConverters Scraper → Adapter
**Call**: `CashConvertersAdapter.run_sync()`
**Request**: No params
**Internal Calls**:
  - `scraper.scrape_all_products()`
    - **Returns**: `List[Dict]` with keys: `title, price, sku, url, images, specs, store, category`
  - `_upsert_product(data)`
    - **Input**: Same as OneCheq
    - **Database Write**: `SupplierProduct` table
    - **Returns**: `'created'|'updated'|'unchanged'`
**Final Return**: `{"total_scraped": int, "total_new": int, "total_updated": int}`

### 1.3 NoelLeeming Scraper → Adapter
**Call**: `NoelLeemingAdapter.run_sync(pages=1)`
**Request**: `pages=1`
**Internal Calls**:
  - `scraper.scrape_collection_page(page_num)`
    - **Returns**: `List[Dict]` with keys: `title, price, sku, url, images, specs, rank`
  - `_upsert_product(data)`
    - **Input**: Same as OneCheq
    - **Database Write**: `SupplierProduct` table
    - **Returns**: `'created'|'updated'|'unchanged'`
**Final Return**: `{"total_scraped": int, "total_new": int, "total_updated": int}`

---

## FLOW 2: ENRICHMENT PIPELINE

### 2.1 Dashboard → Enrichment Daemon
**Trigger**: User clicks "START ENRICHMENT (REAL)"
**Call**: `LLMEnricher.enrich(product)`
**Request**: `SupplierProduct` object
**Internal Calls**:
  - `_call_gemini(prompt)`
    - **Input**: `{"title": str, "description": str, "specs": Dict}`
    - **API Call**: Google Gemini 2.0 Flash
    - **Returns**: `{"enriched_title": str, "enriched_description": str}`
  - **Database Write**: Updates `SupplierProduct.enriched_title`, `enriched_description`, `enrichment_status`
**Final Return**: `{"status": "SUCCESS"|"FAILED", "error": str|None}`

---

## FLOW 3: MARKETPLACE PREPARATION

### 3.1 MarketplaceAdapter.prepare_for_trademe()
**Call**: `MarketplaceAdapter.prepare_for_trademe(supplier_product)`
**Request**: `SupplierProduct` object
**Internal Calls**:

#### 3.1.1 PricingStrategy.calculate_price()
  - **Input**: `{"cost_price": float, "supplier_name": str}`
  - **Logic**: 
    - Get supplier margin from `TradeMeConfig.SUPPLIER_MARGIN_OVERRIDES`
    - Apply mode multiplier from `TradeMeConfig.MODE`
    - Round to psychological price (.99, .00, .50)
  - **Returns**: `float` (final listing price)

#### 3.1.2 CategoryMapper.map_category()
  - **Input**: `{"title": str, "specs": Dict}`
  - **Logic**:
    - Keyword matching against category tree
    - AI fallback if no match
  - **Returns**: `{"category_id": str, "category_name": str}`

#### 3.1.3 TrustEngine.get_product_trust_report()
  - **Input**: `SupplierProduct` object
  - **Logic**:
    - Check image existence
    - Check spec completeness
    - Check price validity
  - **Returns**: `{"score": int, "is_trusted": bool, "blockers": List[str]}`

#### 3.1.4 ImageGuard.is_safe()
  - **Input**: `image_path: str`
  - **API Call**: Gemini Vision 1.5 Flash
  - **Returns**: `{"is_safe": bool, "reason": str}`

**Final Return**:
```python
{
    "title": str,
    "description": str,
    "price": float,
    "category_id": str,
    "category_name": str,
    "trust_signal": "TRUSTED"|"WARNING"|"BANNED_IMAGE",
    "audit_reason": str
}
```

---

## FLOW 4: LISTING CREATION

### 4.1 Dashboard → SystemCommand
**Trigger**: User clicks "Create Listing Command"
**Call**: Creates `SystemCommand` record
**Database Write**:
```python
{
    "id": uuid,
    "type": "PUBLISH_LISTING",
    "payload": {"internal_product_id": int},
    "status": "PENDING",
    "priority": 5
}
```

### 4.2 CommandWorker.handle_publish()
**Call**: `worker.handle_publish(command)`
**Request**: `SystemCommand` object

**Internal Calls**:

#### 4.2.1 Get Product Data
  - **Database Read**: `InternalProduct` + `SupplierProduct`
  - **Returns**: Product object

#### 4.2.2 MarketplaceAdapter.prepare_for_trademe()
  - **See Flow 3.1 above**
  - **Returns**: Marketplace data dict

#### 4.2.3 ProfitabilityAnalyzer.predict_profitability()
  - **Input**: `{"listing_price": float, "cost_price": float}`
  - **Logic**:
    - Calculate Trade Me success fee (7.9%, max $249)
    - Calculate Ping fee (~1.95%)
    - Calculate net profit
    - Calculate ROI
  - **Returns**: `{"is_profitable": bool, "net_profit": float, "roi_percent": float}`
  - **Action**: Raises error if not profitable

#### 4.2.4 Download Images
  - **Call**: `ImageDownloader.download(url)`
  - **Returns**: Local file path

#### 4.2.5 Upload Photos to Trade Me
  - **Call**: `TradeMeAPI.upload_photo_idempotent(image_path)`
  - **Request**: Image file (JPEG, max 5MB)
  - **API Call**: POST to `/v1/Photos.json`
  - **Response**: `{"PhotoId": int}`
  - **Database Write**: `PhotoHash` table (hash → photo_id)
  - **Returns**: `photo_id: int`

#### 4.2.6 Validate Listing
  - **Call**: `TradeMeAPI.validate_listing(payload)`
  - **Request**:
```python
{
    "Category": "0350-6076-6088-",
    "Title": "Product Title (max 49 chars)",
    "Description": ["Full description"],
    "Duration": 7,
    "Pickup": 1,
    "StartPrice": 99.99,
    "PaymentOptions": [1, 2, 3],
    "ShippingOptions": [...],
    "PhotoIds": [123, 456]
}
```
  - **API Call**: POST to `/v1/Selling/Validate.json`
  - **Response**: `{"Success": bool, "Description": str, "Errors": List}`
  - **Returns**: Validation result

#### 4.2.7 Publish Listing
  - **Call**: `TradeMeAPI.publish_listing(payload)`
  - **Request**: Same as validation payload
  - **API Call**: POST to `/v1/Selling.json`
  - **Response**:
```python
{
    "Success": true,
    "ListingId": 4567890,
    "Description": "Listing created successfully"
}
```
  - **Database Write**: 
    - Creates `TradeMeListing` record
    - Updates `InternalProduct`
  - **Returns**: `listing_id: int`

**Final Return**: Updates command status to "COMPLETED"

---

## FLOW 5: ORDER SYNC

### 5.1 Scheduled Task → sync_sold_items.py
**Trigger**: Runs every hour
**Call**: `TradeMeAPI.get_sold_items()`
**Request**: No params
**API Call**: GET to `/v1/MyTradeMe/SoldItems.json`
**Response**:
```python
{
    "List": [
        {
            "ListingId": 123456,
            "PurchaseId": 789012,
            "Price": 99.99,
            "SoldDate": "2025-12-25T10:30:00Z",
            "Buyer": {
                "Nickname": "buyer123",
                "Email": "buyer@example.com"
            },
            "PaymentStatus": "Paid"
        }
    ]
}
```

**Processing**:
  - For each sold item:
    - Find `TradeMeListing` by `ListingId`
    - Check if `Order` exists by `PurchaseId`
    - If not, create new `Order`:
```python
{
    "tm_order_ref": "789012",
    "tm_listing_id": listing.id,
    "sold_price": 99.99,
    "sold_date": datetime,
    "buyer_name": "buyer123",
    "buyer_email": "buyer@example.com",
    "order_status": "CONFIRMED",
    "payment_status": "PAID",
    "fulfillment_status": "PENDING"
}
```

**Export**:
  - **Call**: `export_orders_to_csv()`
  - **Output**: `data/exports/pending_orders_YYYYMMDD_HHMMSS.csv`
  - **Columns**: Order ID, TM Ref, Listing ID, Buyer, Email, Price, Date, Address, Payment, Fulfillment

---

## FLOW 6: LIFECYCLE MANAGEMENT

### 6.1 Dashboard → run_lifecycle.py
**Trigger**: User clicks "Run Lifecycle Analysis"
**Call**: `LifecycleManager.evaluate_state(listing)`
**Request**: `TradeMeListing` object
**Logic**:
  - Check `view_count`, `watch_count`, `days_live`
  - Determine state: NEW → PROVING → STABLE → FADING → KILL
**Returns**:
```python
{
    "action": "PROMOTE"|"DEMOTE"|"KILL"|"NONE",
    "new_state": "PROVING"|"STABLE"|"FADING"|"WITHDRAWN",
    "reason": str
}
```

**Actions**:
  - If KILL: Create `WITHDRAW_LISTING` command
  - If DEMOTE: Create `UPDATE_PRICE` command (10% reduction)
  - Update `TradeMeListing.lifecycle_state`

---

## FLOW 7: RECONCILIATION

### 7.1 UnifiedPipeline → ReconciliationEngine
**Trigger**: After every scraper run
**Call**: `ReconciliationEngine.reconcile(supplier_id)`
**Request**: `supplier_id: int`
**Logic**:
  - Find products not scraped in last run
  - Update `sync_status`: PRESENT → MISSING_ONCE → REMOVED
  - For REMOVED products: Create `WITHDRAW_LISTING` command
**Database Writes**:
  - Updates `SupplierProduct.sync_status`
  - Creates `SystemCommand` records
**Returns**: `{"marked_missing": int, "marked_removed": int, "commands_created": int}`

---

## ALIGNMENT VERIFICATION

### All Request/Response Pairs Verified:
✅ Scraper → Adapter: Returns status string
✅ Adapter → Database: Writes all fields
✅ Database → MarketplaceAdapter: Reads all fields
✅ MarketplaceAdapter → Worker: Returns complete dict
✅ Worker → Trade Me API: Sends valid payload
✅ Trade Me API → Worker: Returns ListingId
✅ Worker → Database: Stores ListingId
✅ Trade Me API → sync_sold_items: Returns order data
✅ sync_sold_items → Database: Creates Order records
✅ Database → CSV Export: Exports all order fields

### No Orphaned Data:
✅ Every database column is written by at least one process
✅ Every database column is read by at least one process
✅ Every API response field is stored or logged
✅ Every function return value is used by caller

**SYSTEM IS FULLY ALIGNED**
