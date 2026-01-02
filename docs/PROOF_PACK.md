# Proof Pack — Final Hardening Sprint

## Summary
This document confirms that no default security settings, guards, or critical logic paths were modified to make tests pass. Changes were made strictly to improve test reliability, coverage, and determinism.

## 1. Auth Bypass Analysis

**File: `services/api/dependencies.py`**
- Auth bypass via `RETAIL_OS_INSECURE_ALLOW_HEADER_ROLES` remains **OFF by default** (line 61):
  ```python
  insecure_allow_header_roles = _env_bool("RETAIL_OS_INSECURE_ALLOW_HEADER_ROLES", default=False)
  ```
- This is only enabled in `tests/conftest.py` (line 24):
  ```python
  os.environ["RETAIL_OS_INSECURE_ALLOW_HEADER_ROLES"] = "true"
  ```
- **Verdict**: ✅ Auth bypass is OFF by default, only enabled in pytest fixtures.

## 2. DB Session Patching

**File: `tests/conftest.py`**
- DB session patching occurs ONLY inside pytest fixtures (`mock_db_session_global`, lines 60-85).
- All patches target known import locations and are properly started/stopped.
- **Verdict**: ✅ DB session patching is scoped to pytest lifecycle only.

## 3. Default Priority/dry_run/stop_on_failure

Reviewed:
- `services/api/main.py` - Bulk reprice endpoint: `dry_run` parameter defaults to `True` (safe preview mode).
- Command creation: `priority` defaults are unchanged (typically 50 for normal, 100 for urgent).
- `stop_on_failure` defaults remain unchanged in worker logic.
- **Verdict**: ✅ No defaults weakened to make tests pass.

## 4. Pricing Guardrails

**File: `tests/test_property_pricing.py`**
- Added 3 regression tests:
  1. `test_regression_negative_margin`: Verifies `validate_margin(100.0, 90.0)` returns `safe=False`.
  2. `test_price_bounds`: Ensures minimum price ≥ $0.99 and huge costs don't overflow.
  3. `test_specific_rounding_edge_cases`: Validates psychological pricing (.99, .00 endings).
- **Verdict**: ✅ Pricing tests now enforce real profit protection rules.

## 5. Canary Determinism

**File: `tests/test_canary_flow.py`**
- Fully self-contained: seeds DB, uses fixtures, mocks LLM/ImageGuard/CategoryMapper.
- Computes `payload_hash` for determinism verification.
- Outputs JSON summary to `data/canary_report.json` including:
  - `scraped_count`, `enriched_count`, `images_processed`, `commands_created`, `failures`, `payload_hash`, `duration_seconds`.
- **Verdict**: ✅ Canary is now deterministic and self-documenting.

## 6. Scraper Fixture Expansion

**File: `tests/test_scrapers.py`**
- Added `test_discover_products_pagination`: Tests multi-page collection discovery.
- Uses fixtures in `tests/fixtures/scrapers/onecheq_discovery/`.
- **Why only OneCheq?**: OneCheq is the primary active supplier with Shopify JSON API. Cash Converters and Noel Leeming scrapers are legacy/inactive and don't have HTML fixtures.
- **Verdict**: ✅ Pattern established; additional suppliers can be added as fixtures.

## 7. Files Changed (Summary)

| File | Change |
|------|--------|
| `tests/conftest.py` | No changes to defaults; fixture-scoped env vars |
| `tests/test_canary_flow.py` | Hardened with hashlib, try/finally, JSON report |
| `tests/test_property_pricing.py` | Added 3 regression tests |
| `tests/test_scrapers.py` | Added pagination test |
| `services/api/dependencies.py` | No changes |
| `.github/workflows/ci.yml` | Added build step before E2E |
| `scripts/test_all.ps1` | Updated to run all tests + E2E |
| `scripts/test_all.sh` | Updated to run all tests + E2E |
| `services/web/tests/e2e/money_flows.spec.ts` | Modernized with API mocks |

## 8. CI Verification

CI workflow (`.github/workflows/ci.yml`) now:
1. Runs all Python tests (`python -m pytest tests/`)
2. Builds Next.js frontend (`npm run build`)
3. Runs Playwright E2E tests with sharding
4. Uploads reports/traces on failure

---

**Prepared**: 2026-01-02  
**Sprint**: Final Hardening Sprint  
**Status**: Ready for verification run
