# Testing Master Plan

## 1. Objectives
Establish a comprehensive automated testing suite and canary process for the Trade Me admin tool to ensure code quality and prevent regressions.

## 2. Test Strategy
We employ a multi-layered testing approach:

### A. Contract Tests (High Priority)
- **Goal:** Prevent API drift and ensure frontend/backend alignment.
- **Scope:** 
  - Backend route existence/methods (`test_contract_routes.py`).
  - Registry content validity (`test_contract_registry.py`).
  - Frontend code compliance (no direct fetch) (`test_contract_frontend_code.py`).
- **Status:** IMPLEMENTED & PASSING.

### B. Property-Based Tests
- **Goal:** Verify business logic invariants across valid input ranges.
- **Scope:**
  - Pricing Strategy: Margin safety, rounding rules (`test_property_pricing.py`).
  - Upsert Logic: Idempotency (`test_property_upsert.py`).
- **Tooling:** `pytest` + `hypothesis`.
- **Status:** IMPLEMENTED.

### C. Integration Tests
- **Goal:** Verify component interaction with seeded database and mocked externals.
- **Scope:**
  - Command Enqueueing & Lifecycle (`test_integration_commands.py`).
  - Bulk Operations (Publish, Reprice) (`test_integration_ops_bulk.py`).
  - Worker Execution (Polling -> Handler -> Success) (`test_integration_worker.py`).
- **Status:** IMPLEMENTED & PASSING.

### D. End-to-End (E2E) Browser Tests
- **Goal:** Verify full user flows.
- **Tool:** Playwright (`services/web/tests/`).
- **Status:** Existing infrastructure exists; to be expanded.

## 3. Execution
A unified runner is available for CI/CD and local development:
- **Windows:** `scripts/test_all.ps1`
- **Linux/Mac:** `scripts/test_all.sh`

Usage:
```bash
./scripts/test_all.sh
```

## 4. Next Steps
- Expand E2E coverage for crucial flows (Publishing Wizard).
- Implement "Canary" scheduled job using the contract tests.
- Add `test_property_duplicates.py` once duplicate logic is re-introduced.
