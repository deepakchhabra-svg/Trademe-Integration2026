# Orphan list (Mission 3 cleanup)

This file records code that was **removed** because it was orphaned (dead/unreachable) or duplicated, and could mask real failures or confuse the operator flow.

## Removed

### Competitor scanning (disabled in pilot)

- **Why orphaned**: The worker handler `handle_scan_competitors()` immediately forced `HUMAN_REQUIRED` and raised, leaving a large unreachable implementation block below it.
- **What replaced it**: Nothing (feature explicitly out of pilot scope). Operator-grade portal should not expose dead/disabled actions.
- **Removed items**:
  - `retail_os/scrapers/competitor_scanner.py` (unused after removing unreachable worker code)
  - Unreachable code path inside `retail_os/trademe/worker.py` after `raise ValueError(...)`
  - Bulk endpoint `POST /ops/bulk/scan_competitors` in `services/api/main.py`
  - Bulk UI section "Competitor scan" in `services/web/src/app/ops/bulk/ui.tsx`
  - Queue label mapping for `SCAN_COMPETITORS` in `services/web/src/app/ops/queue/page.tsx`

## Notes

- Automated tests and build tooling are intentionally **not** listed as orphans.
- If additional features are declared out-of-scope for pilot, they should follow the same rule: remove from UI + remove dead backend paths (or make them real).

