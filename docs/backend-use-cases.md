# Backend Use Case Catalog

## 1. HTTP API (FastAPI)
**Entry Point:** `services/api/main.py`

| Use Case | Method / URI | Auth Mode | Description |
| :--- | :--- | :--- | :--- |
| **Health Check** | `GET /health` | Public | Probes DB connection and returns service health status. |
| **Media Server** | `GET /media/{rel_path}` | Token (Listing) | Serves protected local media files (`data/media/*`) to authenticated clients. |
| **Identity Debug** | `GET /whoami` | Public/Header | Debug endpoint returning current Role and RBAC configuration. |
| **Operator Inbox** | `GET /ops/inbox` | Role (Power) | Returns counts/groups of items requiring human attention (Human Required commands, Failed Jobs). |
| **Ops Summary** | `GET /ops/summary` | Role (Power) | High-level KPI dashboard (Command counts, Vault totals, Listing states). |
| **Pipeline Summary** | `GET /ops/pipeline_summary` | Role (Power) | Per-supplier pipeline status (Raw -> Enriched -> Draft -> Live) and top blockers. |
| **Supplier Detail** | `GET /ops/suppliers/{id}/pipeline` | Role (Power) | Detailed view of a supplier's pipeline + active command list. |
| **Account Health** | `GET /trademe/account_summary` | Role (Power) | Live check of Trade Me API connectivity and Account Balance. |
| **LLM Health** | `GET /llm/health` | Role (Power) | Diagnostics for the configured LLM provider. |
| **Validate Drafts** | `POST /trademe/validate_drafts` | Role (Power) | Batch validates pending drafts against real Trade Me API regulations. |

## 2. Queue Consumers (Worker)
**Entry Point:** `retail_os/trademe/worker.py` (CommandWorker)

| Command Type | Use Case | Description | Side Effects |
| :--- | :--- | :--- | :--- |
| `PUBLISH_LISTING` | **Publish Listing** | "Golden Path" publishing. Validates, uploads images, creates TM listing. Supports `dry_run`. | DB Updates (TradeMeListing), API Calls (Photo Upload, Publish), File Read. |
| `UPDATE_PRICE` | **Update Price** | Updates price of a live listing. | API Call (Price Update), DB Update (TradeMeListing, PriceHistory). |
| `WITHDRAW_LISTING` | **Withdraw Listing** | Withdraws a live listing from Trade Me. | API Call (Withdraw), DB Update (TradeMeListing state). |
| `SCRAPE_SUPPLIER` | **Scrape Supplier** | Generic scraper runner. Dispatches to specific adapters (OneCheq, Noel Leeming). | Updates `SupplierProduct` table, DB Logs. |
| `SCRAPE_OC` | **Scrape OneCheq** | Specific OneCheq scraper trigger (Legacy/Specific). | Updates `SupplierProduct` table. |
| `ENRICH_SUPPLIER` | **Enrich Supplier** | Enriches raw supplier products using LLM. | Updates `SupplierProduct` (enriched fields), `InternalProduct` creation. |
| `SYNC_SOLD_ITEMS` | **Sync Orders** | Polling "Heartbeat". Fetches sold items, creates Orders. | Creates `Order` rows, Updates `TradeMeListing` stock/state. |
| `SYNC_SELLING_ITEMS` | **Sync Live Items** | Syncs "Selling" list from TM to DB for state reconciliation. | Updates `TradeMeListing` (actual_price, actual_state). |
| `ONECHEQ_FULL_BACKFILL` | **OneCheq Backfill** | Orchestrates full backfill: Scrape -> Image -> Enrich -> Validate. | Massive DB updates, Image downloads. |
| `BACKFILL_IMAGES_...` | **Image Backfill** | Downloads missing images for OneCheq products. | File writes (`data/media`), DB updates. |
| `VALIDATE_LAUNCHLOCK`| **Validate LaunchLock**| Runs LaunchLock validation suite on products. | DB Updates (Validation Status). |

## 3. Scheduled Jobs
**Entry Point:** `retail_os/core/scheduler.py`

| Job ID | Frequency | Use Case | Command Enqueued |
| :--- | :--- | :--- | :--- |
| `scrape_all` | ~60 min | **Routine Scrape** | `SCRAPE_SUPPLIER` (for each enabled supplier). |
| `enrich_all` | ~60 min | **Routine Enrich** | `ENRICH_SUPPLIER` (for each enabled supplier). |
| `sync_orders` | ~5-10 min | **Order Sync** | `SYNC_SOLD_ITEMS` (Critical Fulfillment). |
| `sync_trademe`| ~30 min | **State Sync** | `SYNC_SELLING_ITEMS` (Marketplace Truth). |

## 4. CLI Scripts
**Entry Point:** `scripts/*.py`

| Script | Use Case | Args | Notes |
| :--- | :--- | :--- | :--- |
| `run_unified_pipeline.py` | **Run Unified Pipeline** | `--suppliers`, `--limit`, `--batch-size` | Async orchestrator for Discovery -> Scrape -> Upsert. Supports OneCheq, CashConverters, Noel Leeming. |
| `sync_sold_items.py` | **Sync Orders (CLI)** | *None* | Standalone runner for Sold Items sync. Shares logic with Worker. |
| `run_enrichment_daemon.py`| **Enrichment Daemon** | *None* | Long-running process to enrich pending products. |
| `batch_production_simple.py`| **Batch Lister** | `--limit`, `--dry-run` | Simple batch listing tool (likely legacy/simplified). |
| `onecheq_*.py` | **OneCheq Utilities** | *Various* | Specific maintenance tasks (Full backfill, Image backfill). |
| `migrate_database.py` | **DB Migration** | *None* | Applies schema changes. |
