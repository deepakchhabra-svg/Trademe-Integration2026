# Pilot reality-mode note (Mission 4)
**NOEL_LEEMING is currently not supported** due to robots/image access constraints. The operator console blocks NL actions rather than pretending success.

# RetailOS – Trade Me Integration Platform – Master Requirements Document

**Consolidated and reconciled requirements (deduplicated, contradiction-resolved)**

## Status Summary

| Status | Count | Percentage |
|-------------------------------|-------|------------|
| ✅ DONE & Integrated | 198 | 47.4% |
| 🟡 PARTIAL/Orphaned | 156 | 37.3% |
| ❌ MISSING/Not Implemented| 64 | 15.3% |
| **Total Requirements** | **418** | **100%** |

## LEGEND

- **✅ DONE & INTEGRATED** – Working and accessible
- **🟡 PARTIAL/ORPHANED** – Coded but not integrated (e.g. not scheduled, not in UI)
- **❌ MISSING** – Not implemented (no code or functionality yet)

---

## MODULE 1: SCRAPING & DATA INGESTION (112 Requirements)

### 1.1 Core Architecture (20)

| ID | Requirement | Status | File/Notes |
|---------|-------------|--------|------------|
| SCR-001 | 3-Layer pattern (Scraper/Schema/Adapter) | ✅ | All scrapers |
| SCR-002 | Unlimited pagination (10,000 pages) | ✅ | run_pipeline.py:52 |
| SCR-003 | Concurrent processing (ThreadPoolExecutor, 15 workers) | ✅ | run_pipeline.py:223 |
| SCR-004 | Auto-retry with exponential backoff (30s/60s/90s) | ✅ | run_pipeline.py:65-96 |
| SCR-005 | 403 Forbidden detection & logging with timestamps | ✅ | run_pipeline.py:83 |
| SCR-006 | Captcha detection & extended backoff (60s) | ✅ | run_pipeline.py:99 |
| SCR-007 | Connection pooling | ✅ | HTTPX client reuse |
| SCR-008 | User-Agent rotation/spoofing | ✅ | Realistic headers |
| SCR-009 | Rate limiting protection | ✅ | Configurable delays |
| SCR-010 | State tracking (incremental runs) | 🟡 | Orphaned – implemented for CashConverters only (not universal) |
| SCR-011 | Progress reporting (every 50 items) | ✅ | run_pipeline.py:236-244 |
| SCR-012 | Live monitoring script | ✅ | scripts/monitor_live.py |
| SCR-013 | Curl-based fetching (403 bypass) | ✅ | CashConverters scraper, Universal adapter |
| SCR-014 | Selenium-based fetching (JS sites) | ✅ | Noel Leeming scraper |
| SCR-015 | HTTPX-based fetching (modern sites) | ✅ | OneCheq scraper |
| SCR-016 | Async/await architecture | ✅ | run_dual_site_pipeline.py |
| SCR-017 | Batch processing (configurable size) | ✅ | run_dual_site_pipeline.py:26 |
| SCR-018 | Error aggregation and reporting | ✅ | run_pipeline.py:86-91 |
| SCR-019 | Consecutive empty page detection (stop after 10) | ✅ | discover_category.py:80 |
| SCR-020 | Consecutive failure detection (stop after 5) | ✅ | discover_category.py:52 |

### 1.2 Image Handling (24)

| ID | Requirement | Status | File/Notes |
|---------|-------------|--------|------------|
| IMG-001 | Extract up to 4 images per product | 🟡 | OneCheq implemented, NoelLeeming (only 1 image) |
| IMG-002 | Full resolution images (not thumbnails) | 🟡 | OneCheq uses full size, NoelLeeming (using thumbnails) |
| IMG-003 | Physical download to local storage | 🟡 | OneCheq ✅, Missing for other scrapers (images not saved) |
| IMG-004 | Multi-image naming (SKU_1, SKU_2, ...) | ✅ | Implemented in adapter logic |
| IMG-005 | Remove Shopify size parameters (e.g. _400x400) | ✅ | OneCheq scraper |
| IMG-006 | Remove query parameters from image URLs | ✅ | OneCheq (cleans URLs) |
| IMG-007 | Image deduplication (avoid badges/icons) | ✅ | Filter logic (skips badge images) |
| IMG-008 | Image download success logging | ✅ | Logs file size/path |
| IMG-009 | Image download failure handling | ✅ | Logs error and continues |
| IMG-010 | Fallback to URLs if download fails | ✅ | Stores original image URLs |
| IMG-011 | Image hash deduplication (xxhash64/MD5) | ✅ | Implemented (api.py:32) |
| IMG-012 | PhotoHash cache table | ✅ | database.py (PhotoHash model) |
| IMG-013 | Idempotent photo upload (avoid duplicates) | ✅ | api.py:35 (checks hash cache first) |
| IMG-014 | Image directory structure (data/media/) | ✅ | utils/image_downloader.py |
| IMG-015 | Image file verification (exists on disk) | ✅ | trust.py:100 |
| IMG-016 | Placeholder image detection (placehold.co) | ✅ | trust.py:92 (filters placeholder images) |
| IMG-017 | Image downloader utility class | ✅ | utils/image_downloader.py |
| IMG-018 | Image size reporting (bytes downloaded) | ✅ | Logs file size |
| IMG-019 | Azure blob storage extraction (CashConverters) | ✅ | cash_converters/scraper.py:54-82 |
| IMG-020 | JSON-LD image extraction (Noel Leeming) | ✅ | noel_leeming/scraper.py:52-84 |
| IMG-021 | Shopify CDN image extraction (OneCheq) | ✅ | onecheq/scraper.py:218-239 |
| IMG-022 | OpenGraph image extraction (Universal adapter) | ✅ | universal/adapter.py:93 |
| IMG-023 | File size validation (min 1KB) | ✅ | utils/image_downloader.py:53 |
| IMG-024 | Extension detection (.jpg/.png/.webp) | ✅ | utils/image_downloader.py:22-26 |

### 1.3 Data Extraction (32)

| ID | Requirement | Status | File/Notes |
|---------|-------------|--------|------------|
| EXT-001 | Title extraction | ✅ | All scrapers |
| EXT-002 | Description extraction | ✅ | All scrapers (variable quality) |
| EXT-003 | Price extraction with regex | ✅ | Handles $, commas |
| EXT-004 | SKU extraction (from URL or page) | ✅ | All scrapers |
| EXT-005 | Brand extraction | 🟡 | OneCheq ✅, CashConverters ❌, NoelLeeming ✅ |
| EXT-006 | Condition detection (New/Used/Refurbished) | 🟡 | OneCheq ✅, CashConverters/NoelLeeming ❌ |
| EXT-007 | Stock status detection | ✅ | All scrapers |
| EXT-008 | Warranty information | ❌ | Not extracted by any scraper |
| EXT-009 | EAN/Barcode extraction | 🟡 | NoelLeeming (via GTM JSON), others ❌ |
| EXT-010 | Specifications extraction (structured JSON) | ✅ | CashConverters, OneCheq (GTM/Shopify data) |
| EXT-011 | Store name extraction | 🟡 | CashConverters ✅, others hardcoded (not truly extracted) |
| EXT-012 | Store location extraction | 🟡 | CashConverters ✅, others hardcoded |
| EXT-013 | Category extraction | 🟡 | CashConverters ✅, NoelLeeming ✅, OneCheq ✅ |
| EXT-014 | Scraped timestamp | 🟡 | CashConverters only (others not capturing) |
| EXT-015 | Product URL capture | ✅ | All scrapers |
| EXT-016 | Reserve price (for auctions) | 🟡 | CashConverters when applicable (not in others) |
| EXT-017 | Buy Now price (immediate purchase price) | ✅ | All scrapers |
| EXT-018 | Current price (vs original price) | 🟡 | CashConverters only |
| EXT-019 | Collection rank (position on site) | ✅ | OneCheq, NoelLeeming |
| EXT-020 | Product ID extraction from URL | ✅ | All scrapers |
| EXT-021 | Label–value pair parsing (CashConverters) | ✅ | cash_converters/scraper.py:41-52 |
| EXT-022 | Money parsing with regex (prices parsing) | ✅ | cash_converters/scraper.py:26-39 |
| EXT-023 | GTM data parsing (Noel Leeming) | ✅ | noel_leeming/scraper.py:208-220 |
| EXT-024 | Shopify product JSON parsing (OneCheq) | ✅ | OneCheq scraper (Shopify API) |
| EXT-025 | Deep scraping (visit detail pages for more data) | ✅ | NoelLeeming adapter option |
| EXT-026 | Pagination discovery (Shopify ?page=N) | ✅ | OneCheq (finds all pages via parameter) |
| EXT-027 | Pagination discovery (Selenium scrolling) | ✅ | NoelLeeming (gep-searchpagination) |
| EXT-028 | Model number extraction | 🟡 | CashConverters (partial, from description text) |
| EXT-029 | H1 title extraction (page main header) | ✅ | cash_converters/scraper.py:87 |
| EXT-030 | OG:title meta tag extraction | ✅ | cash_converters/scraper.py:92 |
| EXT-031 | Fallback to HTML \<title\> tag if needed | ✅ | cash_converters/scraper.py:99 |
| EXT-032 | Whitespace normalization in extracted text | ✅ | All scrapers (trims/cleans whitespace) |

### 1.4 Unified Schema (16)

| ID | Requirement | Status | File/Notes |
|---------|-------------|--------|------------|
| SCH-001 | UnifiedProduct schema (TypedDict, 47 fields) | ✅ | unified_schema.py (master data model) |
| SCH-002 | Normalizer per supplier | ✅ | normalize_X_row() functions for each supplier |
| SCH-003 | Core identifiers (3 fields) | ✅ | Fields: source_id, source, url |
| SCH-004 | Product info fields (4 fields) | ✅ | Fields: title, description, brand, condition |
| SCH-005 | Pricing fields (6 fields) | 🟡 | Some values hardcoded (not all dynamic) |
| SCH-006 | Image fields (4 fields) | ✅ | Fields: photo1–photo4 |
| SCH-007 | Metadata fields (6 fields) | 🟡 | Warranty info missing (not captured) |
| SCH-008 | Store info fields (2 fields) | ✅ | Fields: store_name, store_location |
| SCH-009 | Category mapping fields | 🟡 | Partial – has source_category, category, but mapping not complete |
| SCH-010 | Type safety enforcement (TypedDict validation) | ✅ | Enforced via Python TypedDict |
| SCH-011 | Ranking fields | ✅ | Fields for collection_rank, collection_page |
| SCH-012 | Specs dictionary field (JSON specs) | ✅ | Stores specifications JSON blob |
| SCH-013 | Noel Leeming row normalizer | ✅ | unified_schema.py:81 (specific function) |
| SCH-014 | Cash Converters row normalizer | ✅ | unified_schema.py:117 |
| SCH-015 | OneCheq row normalizer | ✅ | unified_schema.py:147 |
| SCH-016 | Field name constants (for schema keys) | ✅ | UNIFIED_FIELDNAMES set |

### 1.5 Adapter Layer (20)

| ID | Requirement | Status | File/Notes |
|---------|-------------|--------|------------|
| ADP-001 | Adapter class per supplier (modular adapters) | ✅ | Implemented (OneCheq, CashConverters, NoelLeeming, Universal) |
| ADP-002 | run_sync() orchestration method | ✅ | Present in all adapters (standard interface) |
| ADP-003 | SEO enhancement integration (description SEO) | ✅ | All adapters call build_seo_description |
| ADP-004 | Image download integration | 🟡 | OneCheq fully downloads images, others only partial integration |
| ADP-005 | Snapshot hashing (change detection via MD5) | ✅ | Uses MD5 of title\|price\|status |
| ADP-006 | Audit logging (price changes) | ✅ | Implemented in all adapters |
| ADP-007 | Audit logging (title changes) | ✅ | Implemented in all adapters |
| ADP-008 | Reconciliation engine integration | ✅ | All adapters invoke reconciliation checks |
| ADP-009 | Safety guard integration (policy/trust) | ✅ | All adapters invoke safety checks |
| ADP-010 | Self-healing links (fix broken foreign keys) | ✅ | OneCheq adapter (auto-relinks orphans) |
| ADP-011 | Auto-create InternalProduct records | ✅ | All adapters (if needed) |
| ADP-012 | Upsert logic (create vs update decisions) | ✅ | All adapters handle insert or update |
| ADP-013 | Streaming architecture (generator-based pipeline) | ✅ | OneCheq adapter yields results streamingly |
| ADP-014 | Unlimited pages support (pages<=0 means all) | ✅ | All adapters (treat pages=0 as no limit) |
| ADP-015 | Collection parameter support (category collections) | ✅ | OneCheq, NoelLeeming adapters support collection filtering |
| ADP-016 | Deep scrape option (visit product detail pages) | ✅ | NoelLeeming adapter (deep_scrape flag) |
| ADP-017 | Supplier auto-creation (on-the-fly new supplier) | ✅ | Universal adapter (creates supplier entry from domain) |
| ADP-018 | URL-hash SKU generation (for unstructured sites) | ✅ | Universal adapter (derives SKU from URL hash) |
| ADP-019 | Domain-based supplier naming | ✅ | Universal adapter uses domain as supplier name |
| ADP-020 | Multi-image download loop | ✅ | OneCheq, NoelLeeming adapters iterate all images |

---

## MODULE 2: AI & ENRICHMENT (52 Requirements)

### 2.1 LLM Integration (15)

| ID | Requirement | Status | File/Notes |
|---------|-------------|--------|------------|
| AI-001 | OpenAI GPT-4.0 integration | ✅ | llm_enricher.py:80 |
| AI-002 | Google Gemini 2.5 Flash integration | ✅ | llm_enricher.py:96 |
| AI-003 | API key hot-reloading (@property usage) | ✅ | llm_enricher.py:16 |
| AI-004 | Provider auto-detection (choose OpenAI vs Gemini) | ✅ | Checks environment variables |
| AI-005 | Rate limit handling (HTTP 429 retry) | ✅ | llm_enricher.py:106 |
| AI-006 | Timeout handling (20s) | ✅ | llm_enricher.py:91 |
| AI-007 | Fail-safe fallback to Standardizer (if LLM fails) | ✅ | llm_enricher.py:37 |
| AI-008 | Error message preservation in output | ✅ | Passes API error into description field |
| AI-009 | Token usage tracking (count tokens per call) | ❌ | Not implemented |
| AI-010 | Cost estimation of LLM calls | ❌ | Not implemented |
| AI-011 | Batch processing support | ❌ | Not implemented (calls are sequential only) |
| AI-012 | LLM response caching (avoid re-calls) | ❌ | Not implemented |
| AI-013 | Smart template fallback (category-specific prompts) | ✅ | enrich_products.py:56-146 |
| AI-014 | Category detection from title (for enrichment) | ✅ | Covers jewelry, electronics, tools, etc. (keyword matching) |
| AI-015 | Spec field prioritization by category | ✅ | enrich_products.py:82-107 (different spec handling per category) |

### 2.2 Prompt Engineering (8)

| ID | Requirement | Status | File/Notes |
|---------|-------------|--------|------------|
| PRM-001 | Professional copywriter persona in prompts | ✅ | Uses persona "Premium Retail Copywriter" |
| PRM-002 | Structured output format instructions | ✅ | Prompt yields Hook/Features/Condition/Specs sections |
| PRM-003 | Source-of-truth instruction (use raw description for facts) | ✅ | Prompt explicitly instructs using original text as truth |
| PRM-004 | Marketing fluff removal instruction | ✅ | Prompt tells model to ignore promotional language ("We pawn..." etc.) |
| PRM-005 | Temperature control (set to 0.2) | ✅ | Low creativity for consistency |
| PRM-006 | Max tokens limit in prompt | ✅ | Ensures response length is bounded |
| PRM-007 | System vs. user message role separation | ✅ | Uses OpenAI API roles properly |
| PRM-008 | Few-shot examples in prompts | ❌ | Not included in current prompts |

### 2.3 Semantic Standardizer (15)

| ID | Requirement | Status | File/Notes |
|---------|-------------|--------|------------|
| STD-001 | Banned topics dictionary (20+ topics) | ✅ | standardizer.py:13 (extensive blacklist of topics) |
| STD-002 | Banned sentence starters list | ✅ | e.g. sentences starting with "We", "Our", "I" filtered |
| STD-003 | Marketing sentence detection heuristic | ✅ | standardizer.py:29 (detects overly promotional tone) |
| STD-004 | Phone number detection (regex) | ✅ | NZ phone number patterns |
| STD-005 | Address detection (regex) | ✅ | Common address patterns (street, PO box, etc.) |
| STD-006 | Bullet point normalization (* → •) | ✅ | standardizer.py:69 (uniform bullet style) |
| STD-007 | Sentence-level surgical filtering | ✅ | Removes only disallowed sentences, keeps rest |
| STD-008 | All-caps text fix (auto-capitalization) | ✅ | standardizer.py:102 (capitalize as needed) |
| STD-009 | Whitespace normalization | ✅ | Uses norm_ws() function to clean spacing |
| STD-010 | Primary filter integration (use standardizer as main step) | 🟡 | Currently only used as fallback (not primary pipeline) |
| STD-011 | Paragraph vs. list detection (format context) | ✅ | Differentiates narrative text vs lists for proper handling |
| STD-012 | Empty line removal in output | ✅ | Strips unnecessary blank lines |
| STD-013 | Substring match for banned topics | ✅ | Flags any mention of banned phrases |
| STD-014 | Word tokenization for analysis | ✅ | Uses regex-based word extraction |
| STD-015 | Output assembly with double newlines | ✅ | Ensures clean formatting of final text |

### 2.4 Boilerplate Detector (5)

| ID | Requirement | Status | File/Notes |
|---------|-------------|--------|------------|
| BPD-001 | Automatic boilerplate pattern detection | ✅ | boilerplate_detector.py:24 (scans text for repeated boilerplate) |
| BPD-002 | Frequency threshold (<=5% of items) | ✅ | Configurable threshold for flagging boilerplate text |
| BPD-003 | Sentence splitting (regex-based) | ✅ | Splits content into sentences for analysis |
| BPD-004 | Minimum sentence length filter (15 chars) | ✅ | boilerplate_detector.py:45 (ignores very short lines) |
| BPD-005 | Integration in marketplace adapter pipeline | ✅ | marketplace_adapter.py:44-48 (called during listing prep) |

### 2.5 Image Guard (Vision AI) (9)

| ID | Requirement | Status | File/Notes |
|---------|-------------|--------|------------|
| IMG-G01 | Gemini Vision 1.5 integration (image analysis) | ✅ | image_guard.py:66 (calls Vision API) |
| IMG-G02 | Marketing vs. product image classification | ✅ | Prompt-based image classification (distinguish stock marketing images) |
| IMG-G03 | Image hash caching (to avoid re-analysis) | ✅ | Uses MD5 hash to skip repeat images |
| IMG-G04 | JSON response parsing | ✅ | Parses Vision API JSON and cleans markdown |
| IMG-G05 | Integration in marketplace adapter | ✅ | marketplace_adapter.py:94-103 (auto-called in listing flow) |
| IMG-G06 | File existence check before analysis | ✅ | image_guard.py:52 (only analyzes if file exists on disk) |
| IMG-G07 | Error handling for API failures | ✅ | Returns safe default (does not block listing) |
| IMG-G08 | Confidence score extraction | ✅ | Parses JSON to get confidence levels |
| IMG-G09 | Fallback to accept image on error | ✅ | Defaults to "accept" if Vision analysis fails |

---

## MODULE 3: QUALITY & TRUST (48 Requirements)

### 3.1 Trust Engine (17)

| ID | Requirement | Status | File/Notes |
|---------|-------------|--------|------------|
| TRU-001 | Trust score calculation (0–100%) | ✅ | trust.py:26 (composite scoring of product) |
| TRU-002 | Product-level trust report (detail) | ✅ | Generates breakdown of trust factors |
| TRU-003 | Content Rebuilder integration (trust checks in rebuild) | ✅ | Trust engine checks content for banned patterns during rebuild |
| TRU-004 | Physical image verification (file exists) | ✅ | os.path.exists check for downloaded images |
| TRU-005 | Placeholder image detection | ✅ | Blocks placeholder domains (e.g. placehold.co) |
| TRU-006 | Missing spec penalty (caps score at 60%) | ✅ | trust.py:76 (deducts points for missing specs) |
| TRU-007 | Price validation (block $0 or null price) | ✅ | trust.py:113 (zero price = auto-block) |
| TRU-008 | Trust label assignment (TRUSTED/WARNING/BLOCKED) | ✅ | Label based on score thresholds |
| TRU-009 | Dashboard integration (display score) | 🟡 | NOT DISPLAYED in UI (trust scores computed but not shown) |
| TRU-010 | Supplier-level trust score aggregation | ✅ | Aggregates average trust per supplier |
| TRU-011 | Trust threshold configuration (e.g. 95%) | ✅ | Threshold is configurable (what is considered trusted) |
| TRU-012 | Blockers list (reasons for trust failure) | ✅ | Provides list of blocking issues |
| TRU-013 | Warnings list (non-fatal issues) | ✅ | Provides list of warning issues |
| TRU-014 | is_trusted() helper method | ✅ | Returns boolean if product passes trust threshold |
| TRU-015 | get_product_trust_report() method | ✅ | Returns full trust analysis report |
| TRU-016 | Integration in batch production script | ✅ | batch_production_launch.py:51 (trust check before listing) |
| TRU-017 | CSV export of trusted products | ✅ | batch_production_launch.py:89-98 |

### 3.2 Policy Engine (10)

| ID | Requirement | Status | File/Notes |
|---------|-------------|--------|------------|
| POL-001 | Banned phrases check (at least 6 phrases) | ✅ | policy.py:21 (list of prohibited phrases) |
| POL-002 | Zero-price blocker (no free items) | ✅ | Hard failure if price == 0 |
| POL-003 | Missing images blocker | ✅ | Hard failure if no images attached |
| POL-004 | Short description blocker (<50 chars) | ✅ | policy.py:52 (fails if description too short) |
| POL-005 | Out-of-stock blocker | ✅ | Hard failure if stock_level indicates none |
| POL-006 | Trust gate integration (supplier trust check) | ✅ | Blocks listing if supplier trust is below threshold |
| POL-007 | PolicyResult dataclass (blockers/warnings) | ✅ | Holds results of policy evaluation |
| POL-008 | Policy.evaluate() method (entry point) | ✅ | Main method to evaluate all policy rules |
| POL-009 | Supplier data validation (FK existence) | ✅ | Verifies supplier and product link exists |
| POL-010 | Integration in listing flow (enforce policy) | 🟡 | Code exists but not actively enforced (policy checks run but not blocking listing) |

### 3.3 Content Rebuilder (11)

| ID | Requirement | Status | File/Notes |
|---------|-------------|--------|------------|
| REB-001 | Template-based content reconstruction | ✅ | rebuilder.py (uses preset template for descriptions) |
| REB-002 | Prohibited pattern detection in content | ✅ | Filters out banned content during rebuild |
| REB-003 | Spec formatting (bullet list of specs) | ✅ | Outputs specifications as a formatted bullet list |
| REB-004 | Condition statement injection | ✅ | Adds product condition info into description |
| REB-005 | Warranty statement injection | ✅ | Adds warranty info if available |
| REB-006 | "Hook" generation (catchy opening line) | ✅ | Generates a catchy first line for description |
| REB-007 | rebuild() method (main entry point) | ✅ | Main function to rebuild content |
| REB-008 | Integration in batch script (mass listing) | ✅ | batch_production_launch.py:43 calls rebuilder |
| REB-009 | De-duplication logic (content keys) | ✅ | rebuilder.py:76-92 (ensures no duplicate lines for identical content) |
| REB-010 | De-duplication logic (spec keys/values) | ✅ | rebuilder.py:118-126 (removes duplicate specs) |
| REB-011 | is_clean flag (content quality) | ✅ | Returns boolean indicating if content is free of issues |

### 3.4 Reconciliation & Safety (10)

| ID | Requirement | Status | File/Notes |
|---------|-------------|--------|------------|
| REC-001 | Orphan detection (missing supplier items) | ✅ | reconciliation.py:26 (finds products that disappeared from supplier) |
| REC-002 | Two-strike system (MISSING_ONCE → REMOVED) | ✅ | reconciliation.py:38-46 (if missing twice, mark removed) |
| REC-003 | Auto-withdraw trigger (remove from Trade Me if orphan) | ✅ | Creates a WITHDRAW command when item is removed upstream |
| REC-004 | Healed items detection (reappear after missing) | ✅ | Logic to detect if previously missing item comes back in stock |
| REC-005 | Safety guard integration (ensure 90% success rate) | ✅ | safety.py:7 (ensures pipeline success >=90%, else triggers alert) |
| REC-006 | Minimum items threshold check | ✅ | Enforces minimum 5 items per supplier (to detect scraping issues) |
| REC-007 | Integration in all adapters | ✅ | All adapters call reconciliation to sync state |
| REC-008 | Audit logging for status changes | ✅ | reconciliation.py:98-108 (logs orphan→removed transitions) |
| REC-009 | Sync status column (PRESENT/MISSING_ONCE/REMOVED) | ✅ | Uses TradeMeListing.sync_status (enum) field in DB |
| REC-010 | process_orphans() method (batch entry point) | ✅ | Main reconciliation runner method |

---

## MODULE 4: TRADE ME INTEGRATION (45 Requirements)

### 4.1 API Integration (20)

| ID | Requirement | Status | File/Notes |
|---------|-------------|--------|------------|
| TM-001 | OAuth 1.0a authentication (Trade Me API) | ✅ | trademe/api.py:28 |
| TM-002 | Create listing (POST /Selling.json) | ✅ | trademe/api.py:99 |
| TM-003 | Validate listing (POST /Selling/Validate.json) | ✅ | trademe/api.py:86 |
| TM-004 | Photo upload (POST /Photos.json) | ✅ | trademe/api.py:35 (Base64 image upload) |
| TM-005 | Idempotent photo upload with hash | ✅ | Uses image hash (xxhash64/MD5) to avoid duplicates |
| TM-006 | Get listing details (GET /Listings/{id}.json) | ✅ | trademe/api.py:115 |
| TM-007 | Withdraw listing (POST /Selling/Withdraw.json) | ✅ | trademe/api.py:155 |
| TM-008 | Get all selling items (GET /MyTradeMe/SellingItems.json) | ✅ | trademe/api.py:177 |
| TM-009 | Get sold items (GET /MyTradeMe/SoldItems.json) | ✅ | trademe/api.py:197 |
| TM-010 | Price display parser (text → float conversion) | ✅ | Regex parser for price strings |
| TM-011 | Timeout handling (30s) | ✅ | Applied to all HTTP requests |
| TM-012 | Retry logic for API calls | 🟡 | MAX_RETRIES defined but not actively used (no retry loop) |
| TM-013 | Error response handling (check API errors) | ✅ | Checks "Success" field in responses |
| TM-014 | Session reuse (persistent HTTP session) | ✅ | Uses requests.Session() for efficiency |
| TM-015 | Environment variable configuration (API keys in .env) | ✅ | Loads keys from environment (.env) |
| TM-016 | Date parsing (/Date(12345678)/ format) | ✅ | trademe/api.py:217 (regex conversion) |
| TM-017 | Client-side date filtering (from API results) | ✅ | trademe/api.py:211-221 (filters listings by date locally) |
| TM-018 | Auto-download image before upload | ✅ | worker.py:156-168 (fetches image file before API upload) |
| TM-019 | Photo ID extraction from API response | ✅ | trademe/api.py:44 (parses photo upload response) |
| TM-020 | Listing ID extraction from API response | ✅ | trademe/api.py:108 (parses listing creation response) |

### 4.2 Listing Management (14)

| ID | Requirement | Status | File/Notes |
|---------|-------------|--------|------------|
| LST-001 | Listing payload builder (compile all listing fields) | ✅ | worker.py:196-206 (constructs JSON payload) |
| LST-002 | Category mapping to Trade Me categories | ✅ | category_mapper.py (maps internal category to TM category) |
| LST-003 | Listing validation before publish (pre-check) | ✅ | trademe/api.validate_listing() used |
| LST-004 | Read-back verification (post-publish check) | ✅ | Uses get_listing_details() to verify listed item |
| LST-005 | Listing state tracking (Live/Withdrawn) | ✅ | Uses TradeMeListing.actual_state field |
| LST-006 | View count tracking | ✅ | View counts stored in DB |
| LST-007 | Watch count tracking | ✅ | Watch counts stored in DB |
| LST-008 | Listing metrics snapshots (historical metrics) | ✅ | ListingMetricSnapshot table stores snapshots |
| LST-009 | Automatic delisting (end listing when needed) | 🟡 | Logic exists (auto-delist in code) but no daemon/scheduler runs it |
| LST-010 | Bulk withdraw functionality | ❌ | Not implemented (no batch withdraw operation) |
| LST-011 | Dry-run mode for listing (no actual post) | ✅ | worker.py:219 (simulate listing without posting) |
| LST-012 | Title truncation (max 49 chars) | ✅ | worker.py:199 (ensures title <= 50 chars) |
| LST-013 | Desired vs actual state tracking | ✅ | Implements state triad (desired vs actual listing state) |
| LST-014 | Last-synced timestamp for listings | ✅ | Uses TradeMeListing.last_synced_at field |

### 4.3 Order Management (8)

| ID | Requirement | Status | File/Notes |
|---------|-------------|--------|------------|
| ORD-001 | Sold items synchronization script (Trade Me → local) | ✅ | scripts/sync_sold_items.py |
| ORD-002 | Create order records in database | ✅ | Inserts into Order table |
| ORD-003 | Update stock on sale (adjust inventory) | ✅ | Sets stock_level = 0 on sale |
| ORD-004 | Order status tracking (pending/completed) | ✅ | Tracks status (PENDING, COMPLETED) |
| ORD-005 | Buyer information capture | ✅ | Captures buyer_name, contact details (if available) |
| ORD-006 | Order reference (Trade Me order ID) | ✅ | Stores Trade Me order ID (tm_order_ref) |
| ORD-007 | Dashboard order display | ✅ | Orders tab in Streamlit dashboard (dashboard/app.py) |
| ORD-008 | Idempotency check (avoid duplicate orders) | ✅ | sync_sold_items.py:38 (skips already imported orders) |

### 4.4 Customer Service & Feedback (3)

| ID | Requirement | Status | File/Notes |
|---------|-------------|--------|------------|
| CS-001 | Buyer Q&A retrieval (fetch listing questions) | ❌ | No integration with Trade Me Questions API (not implemented) |
| CS-002 | Seller response to buyer questions (via API) | ❌ | Not implemented (no functionality to send answers) |
| CS-003 | Trade Me feedback sync (retrieve seller ratings) | ❌ | Not implemented (no feedback data handling in trademe/api.py) |

---

## MODULE 5: STRATEGY & LIFECYCLE (39 Requirements)

### 5.1 Pricing Strategy (15)

| ID | Requirement | Status | File/Notes |
|---------|-------------|--------|------------|
| PRC-001 | Cost-plus pricing engine (base cost + margin) | ✅ | strategy/pricing.py:19 (core pricing logic) |
| PRC-002 | Minimum margin enforcement (15% or $5) | ✅ | Configurable threshold |
| PRC-003 | Psychological price rounding (.99, .50 endings) | ✅ | pricing.py:41 (rounds prices to .99, .50, etc.) |
| PRC-004 | Price tier logic (different rules for <$20, $20–100, >$100) | ✅ | Implements tiered rounding strategies |
| PRC-005 | Margin validation (minimum 5% profit floor) | ✅ | pricing.py:75 (ensures margin >= 5%) |
| PRC-006 | calculate_price() method (pricing entry point) | ✅ | Main pricing function |
| PRC-007 | apply_psychological_rounding() helper | ✅ | Separate method for price rounding |
| PRC-008 | validate_margin() helper | ✅ | Safety check for profit margin |
| PRC-009 | Integration in listing flow (apply pricing automatically) | 🟡 | NOT CALLED – pricing engine exists but not invoked during listing creation |
| PRC-010 | Seasonal pricing multipliers (e.g. holiday markup) | ❌ | Not implemented (no seasonal price adjustments) |
| PRC-011 | Integration in Inventory Ops tools | ✅ | inventory_ops.py:45 (pricing engine used in bulk operations) |
| PRC-012 | Bulk pricing rule application (batch update) | ✅ | inventory_ops.py:13-63 (apply pricing rules to many items) |
| PRC-013 | Configurable margin percentages (per category or supplier) | ✅ | pricing.py:12-14 (margin can be set via config) |
| PRC-014 | Configurable minimum profit amount | ✅ | pricing.py:15 (absolute profit floor configurable) |
| PRC-015 | Competitive pricing analysis integration (market-based adjustments) | ❌ | Not implemented (no competitor price monitoring or dynamic adjustment) |

### 5.2 Lifecycle Management (16)

| ID | Requirement | Status | File/Notes |
|---------|-------------|--------|------------|
| LIF-001 | State machine for listings (NEW→PROVING→STABLE→FADING→KILL) | ✅ | strategy/lifecycle.py (defines state transitions) |
| LIF-002 | evaluate_listing() method (state decision logic) | ✅ | Analyzes listing metrics to recommend state changes |
| LIF-003 | NEW state logic (0–7 days in system) | ✅ | Time-based logic for new listings |
| LIF-004 | PROVING state logic (views threshold trigger) | ✅ | Moves to STABLE if views exceed threshold |
| LIF-005 | STABLE state logic (consistent performance) | ✅ | Checks velocity (views/day) to stay stable |
| LIF-006 | FADING state logic (declining engagement) | ✅ | Detects downward trend in views/sales |
| LIF-007 | KILL state logic (no engagement cutoff) | ✅ | Defines criteria for end-of-life (no views or sales) |
| LIF-008 | Repricing recommendation (for FADING items) | ✅ | Suggests 10% price drop for FADING items |
| LIF-009 | suggest_reprice() method (price suggestion) | ✅ | Returns new price based on strategy (used for FADING) |
| LIF-010 | Lifecycle runner script | ✅ | scripts/run_lifecycle.py (executes lifecycle checks) |
| LIF-011 | Integration in dashboard (show lifecycle state) | 🟡 | NOT DISPLAYED – lifecycle states/calculations not shown in UI |
| LIF-012 | Automated execution (scheduled lifecycle runs) | 🟡 | NOT SCHEDULED – script exists but no scheduled job (manual run only) |
| LIF-013 | Auto-kill command creation (schedule removal) | ✅ | run_lifecycle.py:36-44 (creates remove commands for KILL state) |
| LIF-014 | Auto-reprice command creation | ✅ | run_lifecycle.py:56-63 (creates price update commands for FADING state) |
| LIF-015 | ListingState enum (all lifecycle states) | ✅ | Defined in database.py:19-25 (NEW, PROVING, STABLE, etc.) |
| LIF-016 | lifecycle_state field on TradeMeListing | ✅ | Added to TradeMeListing table to store lifecycle state |

### 5.3 Metrics Engine (8)

| ID | Requirement | Status | File/Notes |
|---------|-------------|--------|------------|
| MET-001 | Views-per-day velocity calculation | ✅ | strategy/metrics.py:14 (calculates daily views rate) |
| MET-002 | Store-wide aggregates (global metrics) | ✅ | metrics.py (calculate_store_metrics() totals) |
| MET-003 | Listing-specific metrics (performance stats) | ✅ | metrics.py (calculate_listing_velocity() per item) |
| MET-004 | Metrics snapshot storage (historical record) | ✅ | Uses ListingMetricSnapshot table to save snapshots |
| MET-005 | Dashboard integration (display metrics) | 🟡 | NOT DISPLAYED – no UI element shows velocity or metrics |
| MET-006 | Trend analysis (detect performance trends) | ❌ | Not implemented (no trending analysis beyond basic velocity) |
| MET-007 | Integration in Lifecycle Manager | ✅ | Metrics used to inform lifecycle state decisions (views threshold, velocity) |
| MET-008 | Lifecycle analysis in Inventory Ops | ✅ | inventory_ops.py:122-153 (bulk analysis of listings' lifecycle status) |

---

## MODULE 6: DASHBOARD & UI (34 Requirements)

### 6.1 Core Dashboard (15)

| ID | Requirement | Status | File/Notes |
|---------|-------------|--------|------------|
| UI-001 | 3-Tier vault display (Raw/Sanitized/Marketplace views) | ✅ | Implemented (three data views in UI) |
| UI-002 | Vault metrics (4 summary cards) | ✅ | Real-time counts displayed (total items, etc.) |
| UI-003 | Search & filters across products | ✅ | Implemented in all 3 vaults (search bar, filter controls) |
| UI-004 | Pagination controls (page through listings) | ✅ | Configurable items per page |
| UI-005 | Manual scraper triggers (buttons) | ✅ | 3 "Sync" buttons to trigger scrapes for each source |
| UI-006 | AI enrichment button (trigger LLM enrichment) | ✅ | Fully functional backend call to enrichment |
| UI-007 | Order management tab (orders view) | ✅ | Displays real Trade Me orders in UI |
| UI-008 | CSV export (download listings data) | ✅ | Available for all 3 vaults |
| UI-009 | Enrichment comparison view (side-by-side) | ✅ | Shows Raw vs Enriched description for comparison |
| UI-010 | Professional styling (OneCheq navy/amber theme) | ✅ | Custom CSS applied |
| UI-011 | Responsive layout (desktop/mobile friendly) | ✅ | Utilizes Streamlit columns, responsive design |
| UI-012 | Empty state handling (no data messages) | ✅ | User-friendly messages when tables are empty |
| UI-013 | Product inspector view (detailed modal/popup) | ✅ | Added feature for detailed product view |
| UI-014 | Supplier filter (dropdown by source) | ✅ | Can filter listings by supplier name |
| UI-015 | Enrichment status filter | ✅ | Filter by enrichment status (PENDING/SUCCESS/FAILED) |

### 6.2 Missing Dashboard Features (19)

| ID | Requirement | Status | File/Notes |
|---------|-------------|--------|------------|
| UI-016 | Trust score display (product trust metric in UI) | 🟡 | ORPHANED – trust engine exists (trust.py), but scores not shown on dashboard |
| UI-017 | Profit & loss dashboard (financial summary) | ❌ | Not implemented – no analytics tab for profit/cost |
| UI-018 | Margin breakdown by category (analytics) | ❌ | Not implemented (no UI for per-category margin) |
| UI-019 | Performance charts (velocity over time) | ❌ | Not implemented – metrics.py computes velocity but not visualized |
| UI-020 | Universal URL input (ad-hoc scraping via URL) | ❌ | Not implemented – no UI to trigger the Universal adapter for custom URLs |
| UI-021 | Lifecycle state visualization (in UI) | ❌ | Not implemented – lifecycle.py results not displayed |
| UI-022 | Pricing strategy display (show pricing recommendations) | ❌ | Not implemented – pricing.py outputs not shown |
| UI-023 | Top performers widget (best-selling or most-viewed) | ❌ | Not implemented – no UI component for top products |
| UI-024 | Failing products widget (low performers) | ❌ | Not implemented – no UI for underperforming items |
| UI-025 | Revenue vs. cost chart (profitability graph) | ❌ | Not implemented – profit data in DB but no chart in UI |
| UI-026 | Supplier performance comparison (analytics) | ❌ | Not implemented – no dashboard comparison between suppliers |
| UI-027 | Audit log viewer (show system audit logs) | ❌ | Not implemented – AuditLog table not exposed in UI |
| UI-028 | System health dashboard (status indicators) | 🟡 | Orphaned – healthcheck.py exists but not integrated into UI |
| UI-029 | Bulk pricing rule UI (mass price updates) | ❌ | Not implemented – inventory_ops.py has logic, not exposed in UI |
| UI-030 | Lifecycle analysis UI (strategy recommendations) | ❌ | Not implemented – inventory_ops.py outputs not exposed in UI |
| UI-031 | Quality tab (content rebuilder tools) | ✅ | Implemented (Quality tab using tabs/quality.py) |
| UI-032 | Live URL scraping in Quality tab | ✅ | Implemented (tabs/quality.py:24 allows on-demand scraping by URL) |
| UI-033 | Image display in Quality tab | ✅ | Implemented (tabs/quality.py:56-66 shows images) |
| UI-034 | Trade Me buyer preview (how listing appears to buyer) | ✅ | Implemented (tabs/quality.py:129-133 shows formatted listing preview) |

---

## MODULE 7: OPERATIONS & DEVOPS (44 Requirements)

### 7.1 Automation & Scheduling (9)

| ID | Requirement | Status | File/Notes |
|---------|-------------|--------|------------|
| OPS-001 | Windows Task Scheduler setup (production scheduling) | ❌ | CRITICAL GAP – no OS-level scheduled tasks configured |
| OPS-002 | Scraper schedule (run every 4 hours) | 🟡 | Script exists (run_pipeline.py), not scheduled to run automatically |
| OPS-003 | Order sync schedule (run every 1 hour) | 🟡 | Script exists (sync_sold_items.py), not scheduled |
| OPS-004 | Lifecycle review schedule (daily run) | 🟡 | Script exists (run_lifecycle.py), not scheduled |
| OPS-005 | Backup schedule (daily backups) | 🟡 | Script exists (backup.ps1), not scheduled |
| OPS-006 | Auto-delist daemon (timed listing removals) | 🟡 | Logic exists (auto-delist in code) but no background service running |
| OPS-007 | Health check schedule (periodic monitoring) | 🟡 | Script exists (healthcheck.py), not scheduled |
| OPS-008 | Enrichment daemon (continuous enrichment process) | 🟡 | Script exists (run_enrichment_daemon.py), not scheduled |
| OPS-009 | Command worker daemon (queued task processor) | 🟡 | Script exists (run_command_worker.py), not scheduled |

### 7.2 Monitoring & Health (9)

| ID | Requirement | Status | File/Notes |
|---------|-------------|--------|------------|
| MON-001 | Health check script (system self-test) | ✅ | scripts/healthcheck.py (checks critical services) |
| MON-002 | Database connectivity check | ✅ | Healthcheck verifies DB connection |
| MON-003 | API credentials check (Trade Me API keys) | ✅ | Healthcheck attempts Trade Me API call |
| MON-004 | Disk space check (storage monitoring) | ✅ | Healthcheck warns if disk space low |
| MON-005 | Log error analysis (scan logs for errors) | ✅ | Healthcheck parses recent logs for errors |
| MON-006 | Live monitoring dashboard (real-time log view) | ✅ | Implemented via monitor_live.py (real-time monitoring UI) |
| MON-007 | Real-time stats parsing (scrape/enrich progress) | ✅ | monitor_live.py parses production_sync.log for live stats |
| MON-008 | Error rate monitoring/alerting | ❌ | No alerting system (errors are logged but no automated alerts) |
| MON-009 | Email alert notifications (on critical failures) | ❌ | No email/SMS integration for alerts (no notification system) |

### 7.3 Backup & Recovery (7)

| ID | Requirement | Status | File/Notes |
|---------|-------------|--------|------------|
| BAK-001 | Automated backup script (full backup routine) | ✅ | scripts/backup.ps1 (invokes backup process) |
| BAK-002 | Database backup (data export) | ✅ | Backs up SQLite DB (file copy mechanism) |
| BAK-003 | Media files backup | ✅ | Compresses image directory for backup |
| BAK-004 | Backup retention policy (e.g. 7 days) | ✅ | Backup script auto-deletes old backups |
| BAK-005 | Backup manifest generation (log of backups) | ✅ | Produces JSON manifest of backup contents |
| BAK-006 | Backup size reporting | ✅ | Logs total backup size |
| BAK-007 | Automated restoration process | ❌ | Not implemented (no restore script or procedure) |

### 7.4 Database Management (6)

| ID | Requirement | Status | File/Notes |
|---------|-------------|--------|------------|
| DB-001 | Self-healing database links (fix broken references) | ✅ | scripts/db_doctor.py (repairs broken foreign keys) |
| DB-002 | Orphan detection (broken foreign keys) | ✅ | db_doctor.py:27-40 (finds missing linked records) |
| DB-003 | Automatic link repair (for orphaned records) | ✅ | db_doctor.py:32-38 (relinks or removes orphans) |
| DB-004 | Migration scripts for schema changes | 🟡 | Partial – some ad-hoc migration scripts exist, but not comprehensive |
| DB-005 | Database reset script (clean slate) | ✅ | scripts/reset_database.py (wipes and reinitializes DB) |
| DB-006 | WAL mode enabled (SQLite write-ahead logging) | ✅ | database.py:221-225 (sets SQLite to WAL mode for performance) |

### 7.5 Validation & Quality (5)

| ID | Requirement | Status | File/Notes |
|---------|-------------|--------|------------|
| VAL-001 | Random product validation (spot-check content) | ✅ | scripts/validator.py (randomly picks products to validate) |
| VAL-002 | Live data comparison (re-fetch and compare) | ✅ | Validator re-fetches product pages live to compare with stored data |
| VAL-003 | Price drift detection (identify price changes) | ✅ | validator.py:73-76 (flags if live price deviates from stored price) |
| VAL-004 | Validation score calculation (data quality score) | ✅ | validator.py:94 (scores each product's data freshness/accuracy) |
| VAL-005 | Validation report generation (detailed results) | ✅ | Returns detailed report of validation findings |

### 7.6 Docker & Deployment (8)

| ID | Requirement | Status | File/Notes |
|---------|-------------|--------|------------|
| DOC-001 | Dockerfile for app (Python 3.12-slim base) | ✅ | Dockerfile exists (production container setup) |
| DOC-002 | System dependencies in Docker (curl, build-essential, etc.) | ✅ | Dockerfile:11-14 (installs required OS packages) |
| DOC-003 | Docker Compose configuration (multi-service) | ✅ | docker-compose.yml defines services |
| DOC-004 | Volume mounts (persist data & code) | ✅ | docker-compose.yml:10-14 (mounts data, code directories) |
| DOC-005 | Environment variable injection | ✅ | docker-compose.yml:15-21 (passes env vars to container) |
| DOC-006 | Health check endpoint (container healthcheck) | ✅ | docker-compose.yml:24-28 (defines healthcheck for container) |
| DOC-007 | Bootstrap script (initial setup automation) | ✅ | scripts/bootstrap.ps1 (script to initialize environment) |
| DOC-008 | CI/CD pipeline setup (continuous integration & deployment) | ❌ | Not implemented – no automated build/test/deploy pipeline (manual only) |

---

## MODULE 8: DATABASE SCHEMA (44 Requirements)

### 8.1 Suppliers Table (4)

| ID | Requirement | Status | File/Notes |
|---------|-------------|--------|------------|
| DB-S01 | id (primary key) | ✅ | database.py:32 |
| DB-S02 | name (unique, not null) | ✅ | database.py:33 |
| DB-S03 | base_url | ✅ | database.py:34 |
| DB-S04 | is_active (boolean flag) | ✅ | database.py:35 |

### 8.2 SupplierProducts Table (15)

| ID | Requirement | Status | File/Notes |
|---------|-------------|--------|------------|
| DB-SP01 | id (primary key) | ✅ | database.py:43 |
| DB-SP02 | supplier_id (foreign key → Suppliers) | ✅ | database.py:44 |
| DB-SP03 | external_sku (not null) | ✅ | database.py:45 |
| DB-SP04 | title | ✅ | database.py:48 |
| DB-SP05 | description (text) | ✅ | database.py:49 |
| DB-SP06 | cost_price (float) | ✅ | database.py:50 |
| DB-SP07 | stock_level (integer) | ✅ | database.py:51 |
| DB-SP08 | product_url | ✅ | database.py:52 |
| DB-SP09 | images (JSON array or URLs) | ✅ | database.py:53 |
| DB-SP10 | specs (JSON) | ✅ | database.py:54 |
| DB-SP11 | enrichment_status (status flag) | ✅ | database.py:57 |
| DB-SP12 | enriched_title | ✅ | database.py:59 |
| DB-SP13 | enriched_description | ✅ | database.py:60 |
| DB-SP14 | collection_rank (integer rank in source) | ✅ | database.py:68 |
| DB-SP15 | Unique constraint on (supplier_id, external_sku) | ✅ | database.py:74-76 |

### 8.3 InternalProducts Table (4)

| ID | Requirement | Status | File/Notes |
|---------|-------------|--------|------------|
| DB-IP01 | id (primary key) | ✅ | database.py:82 |
| DB-IP02 | sku (unique, not null) | ✅ | database.py:83 |
| DB-IP03 | title | ✅ | database.py:84 |
| DB-IP04 | primary_supplier_product_id (FK to SupplierProducts) | ✅ | database.py:87 |

### 8.4 TradeMeListings Table (12)

| ID | Requirement | Status | File/Notes |
|---------|-------------|--------|------------|
| DB-TM01 | id (primary key) | ✅ | database.py:96 |
| DB-TM02 | internal_product_id (FK) | ✅ | database.py:97 |
| DB-TM03 | tm_listing_id (Trade Me ID, unique) | ✅ | database.py:98 |
| DB-TM04 | desired_price (float) | ✅ | database.py:101 |
| DB-TM05 | actual_price (float) | ✅ | database.py:102 |
| DB-TM06 | desired_state (enum) | ✅ | database.py:104 |
| DB-TM07 | actual_state (enum) | ✅ | database.py:105 |
| DB-TM08 | last_synced_at (datetime) | ✅ | database.py:107 |
| DB-TM09 | lifecycle_state (enum) | ✅ | database.py:110 |
| DB-TM10 | is_locked (boolean) | ✅ | database.py:111 |
| DB-TM11 | view_count (integer) | ✅ | database.py:114 |
| DB-TM12 | watch_count (integer) | ✅ | database.py:115 |

### 8.5 Other Tables (9)

| ID | Requirement | Status | File/Notes |
|---------|-------------|--------|------------|
| DB-OT01 | ListingMetricSnapshot table (6 columns) | ✅ | database.py:121-133 |
| DB-OT02 | Order table (8 columns) | ✅ | database.py:135-149 |
| DB-OT03 | SystemCommand table (9 columns) | ✅ | database.py:151-167 |
| DB-OT04 | AuditLog table (7 columns) | ✅ | database.py:169-179 |
| DB-OT05 | ResourceLock table (6 columns) | ✅ | database.py:181-194 |
| DB-OT06 | ListingDraft table (5 columns) | ✅ | database.py:196-206 |
| DB-OT07 | PhotoHash table (3 columns) | ✅ | database.py:208-214 |
| DB-OT08 | CommandStatus enum (7 states) | ✅ | database.py:10-17 |
| DB-OT09 | ListingState enum (6 states) | ✅ | database.py:19-25 |

---

## Notes

Requirements marked as **🟡 PARTIAL or ORPHANED** indicate features that have been developed in code but are not fully integrated into the live system (e.g. not exposed in the UI or not on an automation schedule). 

Requirements marked as **❌ MISSING** are acknowledged as needed but have no implementation yet – these gaps may warrant future development.

Every requirement above is tagged with a unique ID to facilitate tracking; all future tasks and sprint items should trace back to these requirement IDs, making this document the **single source of truth** for project scope and progress.
