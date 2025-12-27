# RetailOS Autopilot – Job Card (Phases, Missions, Requirement Mapping)

This is the single execution plan for turning this repo into a **working, non-orphaned** autopilot system.

## Rules of engagement
- Every feature must have:
  - **Requirement IDs** (existing from `docs/REQUIREMENTS.md` or newly added “implicit” IDs)
  - **API endpoint** (FastAPI) if user-visible or testable
  - **UI surface** (Next.js) if operator-visible
  - **Worker command** (DB-backed) if it causes side-effects
  - **E2E test** (Playwright) if it’s part of MVP mission flow
- Nothing “pretty but fake”: UI only exposes features that are truly wired end-to-end.

## Phases (high level)
- **Phase 0 (Plan + Matrix)**: feature-to-requirement matrix + mission acceptance tests
- **Phase 1 (Backbone)**: scrape/adapters + reconciliation + gates + worker command contract
- **Phase 2 (API)**: FastAPI endpoints wired to existing domain code and command queue
- **Phase 3 (Web UI)**: Next.js MVP console wired to API only
- **Phase 4 (Autopilot scheduling)**: real scheduler service controlled by DB settings
- **Phase 5 (Browser agent tests)**: Playwright suite verifying MVP missions
- **Phase 6 (Performance)**: thousands-of-listings hardening (pagination/indexing/batching)

---

## Mission flows (MVP acceptance tests)

### Mission A: Ingest + reconcile supplier truth (Dropship critical path)
- **Goal**: ingest supplier catalog and reliably mark missing/removed items without catastrophic delists.
- **Requirement IDs**: SCR-001..SCR-020, EXT-* (extraction), IMG-* (images), ADP-005..ADP-014, REC-001..REC-010, OPS-002
- **Acceptance**:
  - Can enqueue `SCRAPE_SUPPLIER` for OneCheq/CashConverters/NoelLeeming
  - DB shows `supplier_products` updated with `last_scraped_at`, `sync_status`
  - Reconciliation transitions: PRESENT → MISSING_ONCE → REMOVED and heals back to PRESENT
  - Withdraw commands are enqueued for confirmed removals (only if safe to reconcile)

### Mission B: Enrichment pipeline produces listing-ready copy
- **Goal**: consistent enriched title/description used by listing builder.
- **Requirement IDs**: AI-001..AI-007, PRM-001..PRM-007, STD-001..STD-015, REB-001..REB-011, UI-006, OPS-008
- **Acceptance**:
  - Can enqueue an `ENRICH_SUPPLIER`/`ENRICH_PRODUCTS` command
  - `SupplierProduct.enriched_title/enriched_description` populated and stable on re-run (idempotent)
  - Publish payload prefers enriched fields

### Mission C: Gatekeeping blocks unsafe launches (inviolable)
- **Goal**: no publish without passing trust/policy/margin/image guard.
- **Requirement IDs**: TRU-001..TRU-017, POL-001..POL-010, PRC-001..PRC-008, IMG-G01..IMG-G09
- **Acceptance**:
  - `PUBLISH_LISTING` is blocked (HUMAN_REQUIRED) if gates fail, with clear reason
  - Dry-run publish always available (safe)

### Mission D: Dry-run publish creates verifiable “listing snapshot”
- **Goal**: prove end-to-end pipeline without spending money.
- **Requirement IDs**: LST-011, UI-013, UI-034
- **Acceptance**:
  - Dry-run publish creates/updates a `TradeMeListing` with `actual_state=DRY_RUN`
  - `payload_snapshot` + `payload_hash` stored

### Mission E: Real publish + withdraw (operator controlled)
- **Goal**: real publishing works and delisting works reliably.
- **Requirement IDs**: TM-001..TM-011, LST-001..LST-008, TM-007, REC-003
- **Acceptance**:
  - Publish to Trade Me succeeds (when creds available)
  - Withdraw command withdraws a live listing

### Mission F: Orders sync shows operational truth
- **Goal**: sold items sync + order records.
- **Requirement IDs**: ORD-001..ORD-008, OPS-003
- **Acceptance**:
  - Can run order sync and see orders in UI

### Mission G: Fulfillment orchestration (supplier backorder + driver purchase)
- **Goal**: support multiple fulfillment modes and keep Trade Me/customer informed at each step (where API supports it).
- **Requirement IDs**: ORD-001..ORD-008 (foundation), CS-001..CS-003 (messaging/feedback – future), IMP-FUL-*
- **Acceptance**:
  - Orders flow into a **fulfillment queue** with an explicit state machine (RECEIVED → VERIFIED → PURCHASED/ASSIGNED → IN_TRANSIT → SHIPPED/DELIVERED + exception states)
  - Driver purchases can be recorded with **amount + receipt evidence**, and costs can be allocated across one or many orders
  - Profit reporting distinguishes **confirmed** vs **unconfirmed** profit when landed cost is missing
  - Status update drafts/logs exist even if Trade Me messaging endpoints are unavailable

---

## “Implicit” requirements (added for autopilot viability)
- **IMP-SEC-001**: Auth/RBAC for admin console (post-MVP if needed)
- **IMP-OBS-001**: Structured logs + command audit trail visible in UI
- **IMP-IDEM-001**: Idempotency across all side-effect commands
- **IMP-PERF-001**: Read pagination + indexes + batch writes for thousands of listings
- **IMP-SAFE-001**: Kill switch + supplier pause + reconcile safety rails
- **IMP-FUL-001**: Fulfillment task system (purchase/driver/ship tasks) with SLAs and audit trail
- **IMP-FUL-002**: Driver purchase events with receipt evidence + cost allocation to orders
- **IMP-FIN-001**: Profit is “locked” until true landed cost is confirmed (no fake margin reporting)

