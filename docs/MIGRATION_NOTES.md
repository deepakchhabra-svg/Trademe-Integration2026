# Migration Notes - Refactoring Phase 1

## UI Changes
- **Canonical Enqueue Path**: Introduced `useEnqueue` hook in `services/web/src/app/_hooks/useEnqueue.ts`.
- **PipelineClient**: Refactored to use `useEnqueue` instead of defining its own `enqueue` function.
- **Vault Actions**: Refactored `vaults/live/[id]/Actions.tsx` and `vaults/enriched/[id]/Actions.tsx` to use `useEnqueue`.
- **Deprecated**: Direct `apiPostClient("/commands", ...)` or `apiPostClient("/ops/enqueue", ...)` in refactored components.

## Backend Changes
- **Shared Upserter**: Created `retail_os.core.product_upserter.ProductUpserter` to consolidate upsert logic.
- **OneCheq Adapter**: Refactored `retail_os/scrapers/onecheq/adapter.py` to delegate to `ProductUpserter`.
- **Operations Registry**: Created `docs/operations_registry.json` as the Single Source of Truth for operation definitions.
- **Documentation**: Added `scripts/generate_docs.py` to derive catalogs from the registry.

## API Refactoring (Phase 2)
- **Modularization**: Split `services/api/main.py` into dedicated routers:
    - `services/api/routers/ops.py`: Handles all `/ops/*` endpoints (enqueue, alerts, jobs, logs).
    - `services/api/routers/vaults.py`: Handles `/vaults/*` (raw, enriched, live).
- **Consolidation**:
    - `services/api/schemas.py`: Unified Pydantic models (e.g. `PageResponse`, `CommandCreateResponse`).
    - `services/api/utils.py`: Shared utilities (`_dt`, serialization helpers).
    - `services/api/dependencies.py`: Centralized authentication and role management (`Role`, `require_role`).
- **Cleanup**: Removed ~1000 lines of code from `main.py`, reducing complexity and improving maintainability.
- **Testing**: Added `scripts/smoke_test_integration.py` to verify basic connectivity and data flow in the new architecture.

## Next Steps
- Apply `ProductUpserter` to `cash_converters` and `noel_leeming` adapters.
- Consolidate text cleanings fully into `retail_os.utils.cleaning`.
- Verify full test suite pass.
- Complete validaton of "Backfill images" which now uses the shared upserter's image downloading logic.
