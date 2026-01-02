# Audit System Functionality: The Final Truth

**Date:** 2026-01-02
**Version:** 1.0 (Post-Refactor Audit)
**Scope:** `services/web` (UI), `services/api` (Backend), `retail_os/trademe` (Worker/Core).
**Objective:** Establish the comprehensive "State of the System" regarding stack, routes, data flow, and hidden risks.

---

## 1. Stack Detection

| Layer | Technology | Details |
| :--- | :--- | :--- |
| **Frontend** | **Next.js 14+** (App Router) | React Server Components (RSC) heavily used for data fetching. |
| **Styling** | **Tailwind CSS** | Used exclusively via utility classes and `buttonClass` helpers. |
| **Data Fetching** | **Direct API Calls (RSC)** | `apiGet` helper in `page.tsx` files (Server-Side). |
| **Mutations** | **Client Components** | `useClient` pattern for `apiPostClient` (e.g., `InboxCommandActions`). |
| **Backend** | **FastAPI** | Python 3.10+, Pydantic v2 schemas. |
| **Database** | **SQLAlchemy + SQLite** | `retail_os.core.database` (Sync engine). |
| **Async** | **Worker Polling** | `CommandWorker` polls `SystemCommand` table (no Celery/Redis). |
| **Integration** | **Trade Me API** | `retail_os.trademe.api` (OAuth1 + XML/JSON). |

---

## 2. Backend Inventory

All endpoints are served via `FastAPI` in `services/api`.

### Core (`main.py`)
| Method | Route | Output | Side Effects / Notes |
| :--- | :--- | :--- | :--- |
| `GET` | `/whoami` | Role, RBAC, Config | Returns auth state & feature flags. |
| `GET` | `/products` | `PageResponse` | **Master View**: Joins SupplierProduct + InternalProduct + Listing. |
| `GET` | `/orders` | `PageResponse` | Read-only view of `Order` table. |
| `GET` | `/suppliers` | `List[Supplier]` | Simple lookup. |
| `GET` | `/suppliers/{id}/policy` | `dict` | returns `scrape`, `enrich`, `publish` policies. |
| `PUT` | `/suppliers/{id}/policy` | `dict` | **Risk**: Updates `SystemSetting` JSON blob. |
| `GET` | `/metrics/listings/{id}` | `PageResponse` | View/Watch count history. |

### Ops (`routers/ops.py`)
| Method | Route | Output | Side Effects / Notes |
| :--- | :--- | :--- | :--- |
| `GET` | `/ops/inbox` | `Inbox` | **Hub**: Aggregates failed commands, jobs, and pending orders. |
| `GET` | `/ops/commands` | `PageResponse` | Explorer for `SystemCommand`. |
| `POST` | `/commands` | `CommandCreateResponse` | **Critical**: Creates any command type. Gatekeeper for automation. |
| `GET` | `/commands/{id}` | `Command` | Detail view. |
| `POST` | `/commands/{id}/retry` | `CommandAction` | Resets status to `PENDING`. |
| `POST` | `/commands/{id}/cancel` | `CommandAction` | Sets status to `CANCELLED`. |
| `GET` | `/ops/readiness` | `dict` | **Heavy**: Runs `LaunchLock` on N items (fast-mode). |
| `GET` | `/ops/removed_items` | `dict` | Audits supplier removal vs listing status. |

### Vaults (`routers/vaults.py`)
| Method | Route | Output | Notes |
| :--- | :--- | :--- | :--- |
| `GET` | `/vaults/raw` | `PageResponse` | Vault 1 (SupplierProduct). |
| `GET` | `/vaults/enriched` | `PageResponse` | Vault 2 (InternalProduct). |
| `GET` | `/vaults/live` | `PageResponse` | Vault 3 (TradeMeListing). |
| `GET` | `/listings/{id}` | `ListingDetail` | **Complex**: Returns Listing + `launchlock` (Gate) + `preview`. |

### Inspectors & Diagnostics
| Get | `/inspector/supplier-products/{id}` | Single Truth View | Joins all 3 Vaults for one item. |
| Get | `/draft/internal-products/{id}/trademe` | Payload Preview | **Safe**: Generates payload *without* uploading photos. |

---

## 3. Command/Worker Audit

The system uses a "Command Pattern" where the UI/API creates a `SystemCommand` row, and a background `worker.py` executes it.

### Command Types
| Type | Payload Arguments | Handler Logic | Risks |
| :--- | :--- | :--- | :--- |
| `PUBLISH_LISTING` | `internal_product_id`, `dry_run`, `photo_path` | **Complex**: Validates -> Downloads Photos -> Uploads -> Drafts -> Publishes. | **High**: Handles money/inventory. Relies on `LaunchLock`. |
| `UPDATE_PRICE` | `listing_id`, `new_price` | Updates Trade Me API + Local DB + Price History. | **Med**: Can trigger API rate limits if bulk-called. |
| `WITHDRAW_LISTING` | `listing_id` | Calls `WithdrawListing`. | **Med**: Irreversible on Trade Me side (feature fee loss). |
| `SCRAPE_SUPPLIER` | `supplier_id` | Trigger specific scraper adapter. | **Low**: Resource intensive. |
| `SCRAPE_OC` | `items_limit`, `lite_mode` | OneCheq specific full/partial sync. | **High**: Can scrape thousands of pages. |
| `SCAN_COMPETITORS` | `listing_id` | Runs `CompetitorScanner`. | **Low**: Read-only. |
| `SYNC_SOLD_ITEMS` | None | Updates Orders & Stock. | **High**: Financial data accuracy. |

### Safety Mechanisms
1.  **LaunchLock**: Shared hard-gate logic used in both API (preview) and Worker (execution).
2.  **Dry Run**: `PUBLISH_LISTING` with `dry_run=true` generates a `ListingDraft` and `payload_hash` without calling Trade Me.
3.  **Human Required**: Worker sets this status on "soft" failures (Balance, Quota, Policy) to block retry loops.

---

## 4. UI Routes & Screens

| Route | Purpose | Key Components | Action Capabilities |
| :--- | :--- | :--- | :--- |
| `/ops/inbox` | **Operator Hub** | `InboxCommandActions` | Retry, Cancel, Acknowledge Commands. |
| `/ops/commands` | Audit Log | Read-Only Table | Search/Filter only. |
| `/vaults/live` | **Active Listings** | `LiveVaultClient` | Filter by Status/Supplier. Links to Detail. |
| `/vaults/live/[id]` | **Listing Detail** | `ListingActions` | **Publish**, **Reprice**, **Withdraw** (Contextual). |
| `/products/[id]` | **Inspector** | `StatusBadge`, `SectionCard` | Read-only view of pipeline state. |
| `/ops/readiness` | Pipeline Health | Aggregated Stats | None (Reporting only). |

---

## 5. UI Action Catalog

Mapping user interactions to their backend side-effects.

### Inbox (`/ops/inbox`)
| User Action (Button) | Component | Backend Call | Side Effect |
| :--- | :--- | :--- | :--- |
| **Retry** | `InboxCommandActions` | `POST /commands/{id}/retry` | Resets `status="PENDING"`, worker picks it up. |
| **Cancel** | `InboxCommandActions` | `POST /commands/{id}/cancel` | Sets `status="CANCELLED"`. |
| **Acknowledge** | `InboxCommandActions` | `POST /commands/{id}/ack` | Sets `status="CANCELLED"` (semantic "seen"). |

### Listing Detail (`/vaults/live/[id]`)
| User Action | Component | Backend Call | Side Effect |
| :--- | :--- | :--- | :--- |
| **Publish / List** | `ListingActions` | `POST /commands` | Creates `PUBLISH_LISTING` command. |
| **Withdraw** | `ListingActions` | `POST /commands` | Creates `WITHDRAW_LISTING` command. |
| **Update Price** | `ListingActions` | `POST /commands` | Creates `UPDATE_PRICE` command. |
| **View on TradeMe** | `LiveVaultClient` | External Link | None. |

### Vault Lists (`/vaults/*`)
- **Search/Filter**: URL Params (`?q=`, `?status=`) -> Server Component -> `apiGet` -> DB Query. **Safe**.

---

## 6. Critical Journeys

### A. The "Golden Path" (Listing)
1.  **Scrape**: `SCRAPE_OC` command updates `SupplierProduct` (Vault 1).
2.  **Enrich**: Automatic or manual trigger updates `InternalProduct` (Vault 2).
3.  **Review**: Operator views `/products/[id]`, checks `LaunchLock` gates.
4.  **Publish**:
    - User clicks **"List Item"** in UI.
    - POST `/commands` -> `{"type": "PUBLISH_LISTING", "payload": {"internal_product_id": 123}}`.
    - **Worker** picks up command.
    - **Phase 1**: `LaunchLock` validation (Price, Title, Image presence).
    - **Phase 2**: Photos downloaded/uploaded to Trade Me.
    - **Phase 3**: `MarketplaceAdapter` standardizes payload -> `TradeMeAPI.create_listing`.
    - **Result**: `TradeMeListing` row created/updated (Vault 3).

### B. The "Safety Net" (Withdrawal)
1.  **Detection**: `SCRAPE_OC` detects product is removed/OOS.
2.  **Flagging**: `SupplierProduct.sync_status` set to `REMOVED`.
3.  **Visibility**: Item appears in `/ops/removed_items`.
4.  **Action**:
    - User clicks **"Withdraw"** (or automated policy triggers it).
    - POST `/commands` -> `{"type": "WITHDRAW_LISTING", "payload": {"listing_id": 456}}`.
    - **Worker** calls `api.withdraw_listing()`.
    - **Result**: Listing withdrawn on Trade Me, `actual_state` updated to `Withdrawn`.

---

## 7. Hidden Duplication & Risks

### 1. LaunchLock Duplication
- **Risk**: `LaunchLock` logic is invoked in `api/main.py` (for UI readiness) and `worker.py` (for execution).
- **Status**: **Mitigated**. Both call the shared `retail_os.core.validator.LaunchLock` class. This is good design.

### 2. Payload Drift
- **Risk**: The "Preview" shown in `/vaults/live/[id]` is generated on-the-fly by `draft_trademe_payload`. The "Actual" listing is generated by `worker.py`.
- **Status**: **Managed**. Both use `retail_os.core.listing_builder.build_listing_payload`. Verification: Worker computes a hash (`payload_hash`) which is stored and can be compared.

### 3. API Client Usage
- **Consistency**: `services/web` uses `apiGet` (Server) and `apiPostClient` (Client).
- **Risk**: No centralized type-safety for payload bodies between Frontend/Backend. If `CommandCreateRequest` payload definition changes in Python, the TS definition in `Actions.tsx` must be manually updated.

### 4. Legacy Command Payloads
- **Tech Debt**: Worker's `resolve_command` supports both `command_type` (new) and `type` (old), and `parameters` (new) vs `payload` (old).
- **Recommendation**: Standardize on `type` + `payload` as defined in `api/main.py`.

---

## 8. Final Conclusions

The system has successfully transitioned to a **Command-Driven Architecture**.
- **Consistency**: The "3-Vault" model is consistently reflected in DB, API, and UI.
- **Safety**: `LaunchLock` and `HumanRequired` states prevent runaway automation failures.
- **Visibility**: The `/ops/inbox` provides excellent visibility into system health.
- **Missing**:
    - **Frontend Tests**: `npm test` is empty. UI logic is untested.
    - **Type Safety**: No shared types between FastAPI Pydantic models and Next.js TypeScript interfaces.

**Functionality Status**: **GREEN**. The system is auditable, robust, and functional.
