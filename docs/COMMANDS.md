## System commands: what is implemented vs future

This repo uses a DB-backed command queue (`SystemCommand`) executed by `CommandWorker` (`retail_os/trademe/worker.py`).

### Implemented (executed by worker today)
- **`SCRAPE_SUPPLIER`**: Runs supplier scraper (CC/OC/NL) and writes to DB.
- **`ENRICH_SUPPLIER`**: Runs enrichment batch (AI or deterministic based on `enrichment.policy`).
- **`PUBLISH_LISTING`**:
  - `dry_run=true`: builds payload + stores `ListingDraft` + `TradeMeListing.actual_state=DRY_RUN` (no Trade Me call).
  - `dry_run=false`: performs real publish (Trade Me) with guardrails + trust/profit gates.
- **`WITHDRAW_LISTING`**: Withdraws a Trade Me listing (used by reconciliation for REMOVED items).
- **`UPDATE_PRICE`**: Updates listing price on Trade Me and records price history.
- **`RESET_ENRICHMENT`**: Re-queues a supplier product for enrichment.
- **`SCAN_COMPETITORS`**: Scans market for lowest competitor and can enqueue `UPDATE_PRICE` (throttled by `competitor.policy`).
- **`SYNC_SOLD_ITEMS`**: Pulls sold items and creates `Order` records.
- **`SYNC_SELLING_ITEMS`**: Pulls current selling items and stores metric snapshots.

### Not implemented (placeholders / future)
There are UI skeletons for fulfillment workflows (`/fulfillment/*`) that are intentionally **not wired** yet:
- packing + shipping labels + tracking updates
- buyer/customer comms automation
- cancellations/returns/refunds automation
- fraud/risk/blacklist checks

These will require additional DB models + Trade Me endpoints + workflow state machines.

