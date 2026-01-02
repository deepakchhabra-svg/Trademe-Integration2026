# Cleanup & Refactoring Candidates (Dead Code)

## Dead Normalizers
The following normalizers are identified as potentially dead or needing refactoring for encapsulation:

1.  **`normalize_cash_converters_row`**
    *   **Status**: Removed/Deprecated.
    *   **Reference**: `retail_os/core/unified_schema.py` (Lines 15-16 comment).
    *   **Action**: Ensure no legacy imports remain.

2.  **`normalize_noel_leeming_row`**
    *   **Status**: Used by `NoelLeemingAdapter`, but violates encapsulation pattern established by Cash Converters (which has its own private normalizer).
    *   **Reference**: `retail_os/core/unified_schema.py`.
    *   **Action**: Move logic into `retail_os/scrapers/noel_leeming/adapter.py` or `normalizer.py` and remove from shared `unified_schema`.

## Unused Scripts
The following scripts appear to be ad-hoc utilities that may no longer be needed:

-   `scripts/check_recent_publishes.py`: Verify if covered by `backend-use-cases.md` or UI.
-   `scripts/check_status.py`: Verify if replaced by `ops/summary` endpoints.

## Pending Adapter Refactors
-   `retail_os/scrapers/noel_leeming/adapter.py`: Still contains duplicated `_upsert_product` logic.
-   `retail_os/scrapers/cash_converters/adapter.py`: Likely contains duplicated `_upsert_product` logic.
-   **Action**: Refactor both to use `retail_os.core.product_upserter.ProductUpserter`.
