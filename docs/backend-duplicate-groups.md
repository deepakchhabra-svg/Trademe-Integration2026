# Backend Duplicate Analysis

## 1. Scraping & Orchestration (High Overlap)

### Group: OneCheq Scraping
**Entities:**
- `Worker: handle_scrape_oc` (Trigger: `SCRAPE_OC`)
- `Worker: handle_scrape_supplier` (Trigger: `SCRAPE_SUPPLIER` for OneCheq)
- `CLI: run_unified_pipeline.py` (Arg: `--suppliers OC`)
- `CLI: onecheq_full_backfill.py`

**Analysis:**
- `handle_scrape_oc` and `handle_scrape_supplier` both call `OneCheqAdapter.run_sync()`. These are redundant but `SCRAPE_SUPPLIER` is the generic/preferred forward path.
- `run_unified_pipeline.py` implements its own "Discovery -> Queue -> Scrape" loop using `OneCheqAdapter`'s `scrape_item` methods individually, rather than calling `run_sync`.
    - **Pros of CLI:** Fine-grained error handling, per-item reconciliation logic (`ReconciliationEngine`), better logging for manual runs.
    - **Pros of Worker:** Simple `run_sync` call, integrated with Command system/retries.
- `onecheq_full_backfill.py` duplicates the orchestration logic found in `Worker: handle_onecheq_full_backfill`.

**Recommendation:**
- Deprecate `SCRAPE_OC` command type in favor of `SCRAPE_SUPPLIER`.
- Refactor `run_unified_pipeline.py` to use `OneCheqAdapter` in a way that shares the "Batch Processing" logic with the Worker, or accept that CLI is for "Deep/Manual" runs and Worker is for "Routine/Lite" runs.
- Consolidate `handle_onecheq_full_backfill` logic into a shared service (e.g., `services.orchestration.onecheq`) callable by both Worker and CLI.

### Group: Noel Leeming Scraping
**Entities:**
- `Worker: handle_scrape_supplier` (Trigger: `SCRAPE_SUPPLIER` for Noel Leeming)
- `CLI: run_unified_pipeline.py` (Arg: `--suppliers NL`)
- `CLI: discover_noel_leeming.py`

**Analysis:**
- Similar to OneCheq. Worker calls `NoelLeemingAdapter.run_sync()`. CLI calls `discover_...` then `scrape_nl` loop.
- The CLI Pipeline includes "Reconciliation" (orphaned product detection) which the Worker `run_sync` does not appear to have (or is hidden inside adapter).

**Recommendation:**
- Standardize on `Adapter.run_sync()` if possible, or extract the "Discovery + Reconciliation" logic into a `PipelineService` used by both.

## 2. Enrichment (Overlap)

### Group: Product Enrichment
**Entities:**
- `Worker: handle_enrich_supplier` (Trigger: `ENRICH_SUPPLIER`)
- `CLI: run_enrichment_daemon.py`
- `CLI: enrich_products.py`

**Analysis:**
- `handle_enrich_supplier` contains inline loop logic for querying `SupplierProduct` and creating `InternalProduct`.
- `run_enrichment_daemon.py` likely imports from `enrich_products.py`.
- `enrich_products.py` contains valid batch processing logic.

**Recommendation:**
- Extract the "Enrich Batch" logic into `retail_os.core.enrichment.batch_processor` and call it from both Worker and CLI.
- Ensure "Cash Converters" blocking logic is consistent (Worker explicitly blocks it; check if CLI does).

## 3. Order Sync (Unified)

### Group: Sold Items Sync
**Entities:**
- `Worker: handle_sync_sold_items`
- `CLI: sync_sold_items.py`

**Analysis:**
- **Status: RESOLVED.**
- The CLI script `scripts/sync_sold_items.py` exposes `sync_sold_items_internal()`.
- The Worker imports this function.
- `retail_os.core.sync_sold_items` was deleted in previous refactor.
- Verification passed.

## 4. OneCheq Backfill (Exact Duplicate)

### Group: Full Backfill Orchestrator
**Entities:**
- `Worker: handle_onecheq_full_backfill`
- `CLI: onecheq_full_backfill.py`

**Analysis:**
- Both implement a multi-phase orchestrator (Scrape -> Images -> Enrich -> Validate).
- The logic is complex and duplicated (copy-pasted phase logic).
- Any change to the backfill procedure must be applied in two places.

**Recommendation:**
- **High Priority:** Extract the 4-phase backfill logic into a `BackfillOrchestrator` class in `retail_os.core.backfill`.
- Both Worker and CLI should instantiate this class.

