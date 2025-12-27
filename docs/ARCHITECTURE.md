# Architecture Overview - Trade Me Integration

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        RETAIL OS PLATFORM                        │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│   SCRAPER LAYER  │ ───▶ │ ENRICHMENT LAYER │ ───▶ │  LISTING LAYER   │
└──────────────────┘      └──────────────────┘      └──────────────────┘
        │                         │                          │
        ▼                         ▼                          ▼
┌──────────────────────────────────────────────────────────────────┐
│                      CORE DATABASE (SQLite)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │   Supplier   │  │   Internal   │  │   TradeMe    │           │
│  │   Products   │─▶│   Products   │─▶│   Listings   │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  DASHBOARD LAYER │
                    │   (Streamlit)    │
                    └──────────────────┘
```

## 📦 Component Details

### 1. Scraper Layer

**Purpose**: Extract product data from supplier websites

**Components**:
- `retail_os/scrapers/cash_converters/` - Cash Converters scraper
- `retail_os/scrapers/noel_leeming/` - Noel Leeming scraper
- `retail_os/scrapers/universal/` - Generic adapter for new sites

**Key Features**:
- Concurrent scraping with configurable workers
- Automatic pagination handling
- Image download and storage
- Error handling and retry logic
- Rate limiting and backoff

**Data Flow**:
```
Supplier Website → HTTP Request → HTML Parser → Product Extractor → Database (SupplierProduct)
                                                                   → Image Download (data/media/)
```

**Technologies**:
- `httpx` - Async HTTP client
- `selectolax` - Fast HTML parsing
- `beautifulsoup4` - Fallback HTML parsing

### 2. Enrichment Layer

**Purpose**: Enhance raw product data with AI-generated descriptions and metadata

**Components**:
- `retail_os/core/llm_enricher.py` - LLM integration
- `retail_os/core/boilerplate_detector.py` - Remove generic text
- `retail_os/core/standardizer.py` - Normalize data
- `retail_os/core/validator.py` - Quality checks

**Key Features**:
- LLM-powered description generation
- Template fallback for rate limit scenarios
- Quality scoring (0-100)
- Boilerplate detection and removal
- Category suggestion

**Data Flow**:
```
SupplierProduct → Boilerplate Removal → LLM Enrichment → Validation → InternalProduct
                                      ↓
                                  Template Fallback (if LLM fails)
```

**Technologies**:
- OpenAI API / Google Gemini
- Custom template engine
- Quality scoring algorithms

### 3. Listing Layer

**Purpose**: Publish products to Trade Me marketplace

**Components**:
- `retail_os/trademe/` - Trade Me API integration
- `retail_os/core/marketplace_adapter.py` - Platform abstraction
- `retail_os/core/category_mapper.py` - Category mapping
- `retail_os/core/image_guard.py` - Image validation

**Key Features**:
- Automated listing creation
- Photo upload with deduplication
- Category discovery and mapping
- Lifecycle management (NEW → PROVING → STABLE → FADING → KILL)
- Metrics tracking (views, watches, sales)

**Data Flow**:
```
InternalProduct → Category Mapping → Photo Upload → Listing Creation → TradeMeListing
                                   ↓
                              PhotoHash (deduplication)
```

**Technologies**:
- Trade Me API (OAuth 1.0a)
- `requests_oauthlib` - OAuth handling
- Image processing and validation

### 4. Core Database

**Purpose**: Central data store for all system state

**Schema**:

```sql
-- Supplier definitions
suppliers
  ├── id (PK)
  ├── name (unique)
  ├── base_url
  └── is_active

-- Raw scraped products
supplier_products
  ├── id (PK)
  ├── supplier_id (FK → suppliers)
  ├── external_sku (unique per supplier)
  ├── title, description, price
  ├── image_urls (JSON)
  ├── specs (JSON)
  ├── enriched_title, enriched_description
  ├── quality_score
  └── timestamps

-- Canonical products (deduplicated)
internal_products
  ├── id (PK)
  ├── sku (unique)
  ├── title
  └── primary_supplier_product_id (FK)

-- Trade Me listings
trademe_listings
  ├── id (PK)
  ├── internal_product_id (FK)
  ├── tm_listing_id (Trade Me ID)
  ├── state (NEW, PROVING, STABLE, FADING, KILL)
  ├── view_count, watch_count
  ├── is_sold
  └── timestamps

-- Time-series metrics
listing_metrics
  ├── id (PK)
  ├── listing_id (FK)
  ├── captured_at
  ├── view_count, watch_count
  └── is_sold

-- Command queue (async operations)
system_commands
  ├── id (PK)
  ├── type (PUBLISH_LISTING, UPDATE_LISTING, etc.)
  ├── payload (JSON)
  ├── status (PENDING, EXECUTING, SUCCEEDED, FAILED)
  └── timestamps

-- Photo deduplication
photo_hashes
  ├── hash (PK)
  ├── tm_photo_id
  └── created_at
```

**Technologies**:
- SQLite with WAL mode (concurrent access)
- SQLAlchemy ORM
- Automatic migrations

### 5. Dashboard Layer

**Purpose**: Real-time monitoring and control interface

**Components**:
- `retail_os/dashboard/app.py` - Main dashboard
- `retail_os/dashboard/cockpit.py` - Control panel
- `retail_os/dashboard/premium_dashboard.py` - Enhanced UI

**Key Features**:
- Real-time metrics (products scraped, enriched, listed)
- Lifecycle state visualization
- Manual intervention controls
- Quality score distribution
- Error log viewer
- Command queue monitoring

**Technologies**:
- Streamlit
- Pandas (data manipulation)
- Plotly (charts)

## 🔄 Data Flow - End to End

### Full Pipeline Flow

```
1. SCRAPING
   Supplier Website → Scraper → SupplierProduct (DB) + Images (disk)

2. ENRICHMENT
   SupplierProduct → LLM Enricher → Updated SupplierProduct (enriched fields)

3. CANONICALIZATION
   SupplierProduct → InternalProduct (deduplicated, single source of truth)

4. LISTING
   InternalProduct → Category Mapper → Photo Uploader → Trade Me API → TradeMeListing

5. MONITORING
   TradeMeListing → Metrics Collector → ListingMetricSnapshot → Lifecycle Manager
                                                                        ↓
                                                                  State Transitions
                                                                  (NEW → PROVING → STABLE → FADING → KILL)

6. DASHBOARD
   All DB Tables → Streamlit → User Interface
```

### Async Command Pattern

For operations that may fail or need retry logic:

```
User Action → SystemCommand (PENDING) → Command Executor → Update Status
                                                          ↓
                                                    SUCCEEDED / FAILED
                                                          ↓
                                                    Retry Logic (if FAILED_RETRYABLE)
```

## 🎯 Design Patterns

### 1. Adapter Pattern
- Each scraper implements a common interface
- `UniversalAdapter` provides generic scraping logic
- Easy to add new suppliers

### 2. Strategy Pattern
- Different enrichment strategies (LLM vs Template)
- Pricing strategies
- Lifecycle strategies

### 3. Command Pattern
- All async operations go through `SystemCommand`
- Enables retry, logging, and audit trail

### 4. Repository Pattern
- Database access abstracted through SQLAlchemy models
- Easy to swap SQLite for PostgreSQL if needed

### 5. Observer Pattern
- Metrics collection observes listing state changes
- Dashboard observes database changes (via Streamlit rerun)

## 🔐 Security Architecture

### Authentication & Authorization
- Trade Me: OAuth 1.0a with consumer key/secret + access token
- Dashboard: Currently no auth (add Streamlit auth for production)

### Secrets Management
- Environment variables (`.env` file)
- Never committed to version control
- Recommend: Azure Key Vault or AWS Secrets Manager for production

### Data Protection
- Database: Local file (no external access)
- Images: Local storage (no CDN yet)
- Logs: May contain sensitive data, rotate regularly

## 📈 Scalability Considerations

### Current Limitations
- **SQLite**: Single-file database, limited concurrent writes
- **Local Storage**: Images stored on disk, no CDN
- **Single Instance**: No horizontal scaling

### Future Improvements
1. **Database**: Migrate to PostgreSQL for better concurrency
2. **Storage**: Use S3/Azure Blob for images
3. **Caching**: Add Redis for frequently accessed data
4. **Queue**: Use RabbitMQ/Celery for command processing
5. **Containerization**: Kubernetes for auto-scaling
6. **Monitoring**: Prometheus + Grafana for metrics

## 🧪 Testing Strategy

### Unit Tests
- Individual scrapers
- Enrichment logic
- Category mapping
- Image validation

### Integration Tests
- Full pipeline (scrape → enrich → list)
- Database operations
- Trade Me API integration

### End-to-End Tests
- Complete user workflows
- Dashboard functionality

## 📊 Performance Metrics

### Current Performance
- **Scraping**: ~15 items/min (with concurrency 15)
- **Enrichment**: ~10 items/min (LLM rate limited)
- **Listing**: ~5 items/min (Trade Me API limits)

### Bottlenecks
1. LLM API rate limits (enrichment)
2. Trade Me API rate limits (listing)
3. Supplier website rate limits (scraping)

### Optimization Strategies
- Batch processing
- Caching (category mappings, photo hashes)
- Concurrent workers (where allowed)
- Retry with exponential backoff

## 🔧 Configuration Management

### Environment Variables
- `CONSUMER_KEY`, `CONSUMER_SECRET` - Trade Me OAuth
- `ACCESS_TOKEN`, `ACCESS_TOKEN_SECRET` - Trade Me OAuth
- `DATABASE_URL` - Database connection string
- `LLM_API_KEY` - OpenAI/Gemini API key (if used)

### Feature Flags
- `USE_LLM_ENRICHMENT` - Enable/disable LLM
- `DRY_RUN_MODE` - Test without publishing
- `DEBUG_MODE` - Verbose logging

## 📝 Logging & Monitoring

### Log Levels
- **DEBUG**: Detailed scraping steps
- **INFO**: Pipeline progress, successful operations
- **WARNING**: Retryable errors, rate limits
- **ERROR**: Fatal errors, failed operations

### Log Locations
- `production_sync.log` - Main pipeline log
- `enrichment.log` - Enrichment operations
- `trademe.log` - Trade Me API calls

### Metrics Tracked
- Products scraped (total, per supplier)
- Products enriched (total, quality score distribution)
- Listings created (total, per state)
- Error rates (per component)
- API call rates (Trade Me, LLM)

---

**Last Updated**: December 2025
