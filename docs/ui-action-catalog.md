# UI Action Catalog

> **Generated:** 2026-01-02  
> **Scope:** `services/web/src/app/**`  
> **Purpose:** Exhaustive catalog of all user actions in the Trade Me Integration UI

---

## Table of Contents

1. [Route Inventory](#route-inventory)
2. [Action Catalog by Route](#action-catalog-by-route)
3. [Action Summary Table](#action-summary-table)
4. [Duplicate Detection](#duplicate-detection)
5. [Shared Components](#shared-components)

---

## Route Inventory

| Route | Dynamic Segments | Page File | Description |
|-------|------------------|-----------|-------------|
| `/` | - | `page.tsx` | Ops Workbench dashboard |
| `/access` | - | `access/page.tsx` | Token management / authentication |
| `/admin/settings` | - | `admin/settings/page.tsx` | Root-only system settings |
| `/fulfillment` | - | `fulfillment/page.tsx` | Fulfillment console hub |
| `/fulfillment/messages` | - | `fulfillment/messages/page.tsx` | Customer communications |
| `/fulfillment/refunds` | - | `fulfillment/refunds/page.tsx` | Refund management |
| `/fulfillment/returns` | - | `fulfillment/returns/page.tsx` | Returns management |
| `/fulfillment/risk` | - | `fulfillment/risk/page.tsx` | Risk & fraud checks |
| `/fulfillment/shipments` | - | `fulfillment/shipments/page.tsx` | Shipment management |
| `/ops/alerts` | - | `ops/alerts/page.tsx` | System alerts |
| `/ops/audits` | - | `ops/audits/page.tsx` | Audit log |
| `/ops/bulk` | - | `ops/bulk/page.tsx` | Bulk operations console |
| `/ops/commands` | - | `ops/commands/page.tsx` | Command log |
| `/ops/commands/[id]` | `id` | `ops/commands/[id]/page.tsx` | Command detail |
| `/ops/inbox` | - | `ops/inbox/page.tsx` | Operator inbox |
| `/ops/jobs` | - | `ops/jobs/page.tsx` | Job history |
| `/ops/llm` | - | `ops/llm/page.tsx` | LLM operations |
| `/ops/queue` | - | `ops/queue/page.tsx` | Queue (redirects to commands) |
| `/ops/readiness` | - | `ops/readiness/page.tsx` | Publish readiness dashboard |
| `/ops/removed` | - | `ops/removed/page.tsx` | Removed items management |
| `/ops/trademe` | - | `ops/trademe/page.tsx` | Trade Me health dashboard |
| `/orders` | - | `orders/page.tsx` | Orders list with filters |
| `/pipeline` | - | `pipeline/page.tsx` | Pipeline index (supplier selector) |
| `/pipeline/[supplierId]` | `supplierId` | `pipeline/[supplierId]/page.tsx` | Pipeline for specific supplier |
| `/products` | - | `products/page.tsx` | Master product list |
| `/products/[id]` | `id` | `products/[id]/page.tsx` | Product inspector |
| `/suppliers` | - | `suppliers/page.tsx` | Suppliers list |
| `/suppliers/[id]` | `id` | `suppliers/[id]/page.tsx` | Supplier detail with policy |
| `/vaults/enriched` | - | `vaults/enriched/page.tsx` | Vault 2 - Enriched products |
| `/vaults/enriched/[id]` | `id` | `vaults/enriched/[id]/page.tsx` | Enriched product detail |
| `/vaults/live` | - | `vaults/live/page.tsx` | Vault 3 - Listings |
| `/vaults/live/[id]` | `id` | `vaults/live/[id]/page.tsx` | Listing detail |
| `/vaults/raw` | - | `vaults/raw/page.tsx` | Vault 1 - Raw supplier products |
| `/vaults/raw/[id]` | `id` | `vaults/raw/[id]/page.tsx` | Raw product detail |

---

## Action Catalog by Route

### `/` (Ops Workbench)

| Action Name | Trigger | Type | Files | Backend Call |
|-------------|---------|------|-------|--------------|
| Refresh summary | Button click | read | `WorkbenchClient.tsx` | `GET /ops/summary` |
| Navigate to Pipeline | Link click | navigate | `WorkbenchClient.tsx` | - |
| Navigate to Inbox | Link click | navigate | `WorkbenchClient.tsx` | - |
| Navigate to Command log | Link click | navigate | `WorkbenchClient.tsx` | - |
| Navigate to commands filtered | Link click | navigate | `WorkbenchClient.tsx` | - |
| Navigate to vaults filtered | Link click | navigate | `WorkbenchClient.tsx` | - |
| Navigate to Readiness | Link click | navigate | `WorkbenchClient.tsx` | - |
| Navigate to Trade Me Health | Link click | navigate | `WorkbenchClient.tsx` | - |
| Navigate to Removed items | Link click | navigate | `WorkbenchClient.tsx` | - |
| Navigate to Bulk ops | Link click | navigate | `WorkbenchClient.tsx` | - |
| Load Trade Me health | Auto-load | read | `WorkbenchClient.tsx` | `GET /trademe/account_summary` |

### `/access` (Access & Tokens)

| Action Name | Trigger | Type | Files | Backend Call |
|-------------|---------|------|-------|--------------|
| Set access token | Button click | mutate | `TokenSetter.tsx` | Cookie set (client-side) |

### `/admin/settings` (Settings)

| Action Name | Trigger | Type | Files | Backend Call |
|-------------|---------|------|-------|--------------|
| Load settings | Page load | read | `settings/page.tsx` | `GET /settings/{key}` (multiple) |
| Save setting | Button click | mutate | `settings/Editor.tsx` | `PUT /settings/{key}` |
| Toggle shipping template | Checkbox | mutate | `settings/Editor.tsx` | `PUT /settings/trademe.shipping.use_template` |
| Save template ID | Button click | mutate | `settings/Editor.tsx` | `PUT /settings/trademe.shipping.template_id` |
| Save footer | Button click | mutate | `settings/Editor.tsx` | `PUT /settings/trademe.listing.footer` |

### `/fulfillment` (Fulfillment Console)

| Action Name | Trigger | Type | Files | Backend Call |
|-------------|---------|------|-------|--------------|
| Navigate to Orders | Link click | navigate | `fulfillment/page.tsx` | - |
| Navigate to Shipments | Link click | navigate | `fulfillment/page.tsx` | - |
| Navigate to Messages | Link click | navigate | `fulfillment/page.tsx` | - |
| Navigate to Returns | Link click | navigate | `fulfillment/page.tsx` | - |
| Navigate to Refunds | Link click | navigate | `fulfillment/page.tsx` | - |
| Navigate to Risk | Link click | navigate | `fulfillment/page.tsx` | - |

### `/ops/bulk` (Bulk Operations)

| Action Name | Trigger | Type | Files | Backend Call |
|-------------|---------|------|-------|--------------|
| Select supplier | Dropdown change | read | `ops/bulk/ui.tsx` | - |
| Load category presets | Auto-load on supplier select | read | `ops/bulk/ui.tsx` | `GET /suppliers/{id}/policy` |
| Apply category preset | Button click | mutate | `ops/bulk/ui.tsx` | - (local state) |
| Scrape all presets | Button click | mutate | `ops/bulk/ui.tsx` | `POST /ops/enqueue` (multiple) |
| Enrich all presets | Button click | mutate | `ops/bulk/ui.tsx` | `POST /ops/enqueue` (multiple) |
| Start scrape | Button click | mutate | `ops/bulk/ui.tsx` | `POST /ops/enqueue` |
| OneCheq full backfill | Button click | mutate | `ops/bulk/ui.tsx` | `POST /ops/enqueue` |
| Enrich now | Button click | mutate | `ops/bulk/ui.tsx` | `POST /ops/enqueue` |
| Sync sold items | Button click | mutate | `ops/bulk/ui.tsx` | `POST /ops/enqueue` |
| Sync selling items | Button click | mutate | `ops/bulk/ui.tsx` | `POST /ops/enqueue` |
| Create drafts | Button click | mutate | `ops/bulk/ui.tsx` | `POST /ops/bulk/dryrun_publish` |
| Publish approved drafts | Button click | mutate | `ops/bulk/ui.tsx` | `POST /ops/bulk/approve_publish` |
| Reset enrichment | Button click | mutate | `ops/bulk/ui.tsx` | `POST /ops/bulk/reset_enrichment` |

### `/ops/commands` (Command Log)

| Action Name | Trigger | Type | Files | Backend Call |
|-------------|---------|------|-------|--------------|
| Filter by type | Form input | read | `ops/commands/page.tsx` | URL params |
| Filter by status | Form input/buttons | read | `ops/commands/page.tsx` | URL params |
| Filter Needs attention | Button click | navigate | `ops/commands/page.tsx` | - |
| Filter Active | Button click | navigate | `ops/commands/page.tsx` | - |
| Filter Not succeeded | Button click | navigate | `ops/commands/page.tsx` | - |
| Filter Succeeded | Button click | navigate | `ops/commands/page.tsx` | - |
| Filter All | Button click | navigate | `ops/commands/page.tsx` | - |
| Apply filters | Form submit | navigate | `ops/commands/page.tsx` | - |
| Reset filters | Link click | navigate | `ops/commands/page.tsx` | - |
| Change page size | Select change | navigate | `ops/commands/page.tsx` | - |
| Navigate to command detail | Link click | navigate | `ops/commands/page.tsx` | - |
| Paginate (Prev/Next) | Link click | navigate | `ops/commands/page.tsx` | - |
| Toggle auto-refresh | Checkbox | read | `AutoRefresh.tsx` | - |

### `/ops/commands/[id]` (Command Detail)

| Action Name | Trigger | Type | Files | Backend Call |
|-------------|---------|------|-------|--------------|
| Retry command | Button click | mutate | `ops/commands/[id]/Actions.tsx` | `POST /commands/{id}/retry` |
| Mark resolved | Button click | mutate | `ops/commands/[id]/Actions.tsx` | `POST /commands/{id}/ack` |
| Cancel command | Button click | mutate | `ops/commands/[id]/Actions.tsx` | `POST /commands/{id}/cancel` |
| Auto-refresh status | Timer | read | `LivePanel.tsx` | `GET /commands/{id}` |
| Load command logs | Auto | read | `LogsPanel.tsx` | (poll) |

### `/ops/inbox` (Operator Inbox)

| Action Name | Trigger | Type | Files | Backend Call |
|-------------|---------|------|-------|--------------|
| Retry command (inline) | Button click | mutate | `ops/inbox/Actions.tsx` | `POST /commands/{id}/retry` |
| Acknowledge command | Button click | mutate | `ops/inbox/Actions.tsx` | `POST /commands/{id}/ack` |
| Cancel command (inline) | Button click | mutate | `ops/inbox/Actions.tsx` | `POST /commands/{id}/cancel` |
| View in Commands | Link click | navigate | `ops/inbox/page.tsx` | - |

### `/ops/readiness` (Publish Readiness)

| Action Name | Trigger | Type | Files | Backend Call |
|-------------|---------|------|-------|--------------|
| Load readiness | Page load | read | `ops/readiness/page.tsx` | `GET /ops/readiness` |
| Navigate to Trade Me health | Link click | navigate | `ops/readiness/page.tsx` | - |
| Navigate to Pipeline | Link click | navigate | `ops/readiness/page.tsx` | - |

### `/ops/removed` (Removed Items)

| Action Name | Trigger | Type | Files | Backend Call |
|-------------|---------|------|-------|--------------|
| Filter by supplier ID | Form submit | navigate | `ops/removed/page.tsx` | - |
| Reset filter | Link click | navigate | `ops/removed/page.tsx` | - |
| Withdraw all removed items | Button click | mutate | `WithdrawButton.tsx` | `POST /ops/bulk/withdraw_removed` |
| View in Vault 1 | Link click | navigate | `ops/removed/page.tsx` | - |
| View withdraw queue | Link click | navigate | `ops/removed/page.tsx` | - |

### `/ops/trademe` (Trade Me Health)

| Action Name | Trigger | Type | Files | Backend Call |
|-------------|---------|------|-------|--------------|
| Load account summary | Page load | read | `ops/trademe/page.tsx` | `GET /trademe/account_summary` |
| Open Trade Me statement | External link | navigate | `ops/trademe/page.tsx` | - |
| Credit account | External link | navigate | `ops/trademe/page.tsx` | - |
| Validate drafts | Button click | mutate | `ValidateDraftsClient.tsx` | `POST /trademe/validate_drafts` |

### `/orders` (Orders)

| Action Name | Trigger | Type | Files | Backend Call |
|-------------|---------|------|-------|--------------|
| Search orders | Form input | navigate | `orders/page.tsx` | - |
| Filter by fulfillment status | Form input | navigate | `orders/page.tsx` | - |
| Filter by payment status | Form input | navigate | `orders/page.tsx` | - |
| Filter by order status | Form input | navigate | `orders/page.tsx` | - |
| Change page size | Select change | navigate | `orders/page.tsx` | - |
| Apply filters | Form submit | navigate | `orders/page.tsx` | - |
| Reset filters | Link click | navigate | `orders/page.tsx` | - |
| Paginate (Prev/Next) | Link click | navigate | `orders/page.tsx` | - |

### `/pipeline` (Pipeline Index)

| Action Name | Trigger | Type | Files | Backend Call |
|-------------|---------|------|-------|--------------|
| Navigate to Trade Me health | Link click | navigate | `pipeline/page.tsx` | - |
| Open supplier pipeline | Link click | navigate | `pipeline/page.tsx` | - |
| Open supplier site | External link | navigate | `pipeline/page.tsx` | - |

### `/pipeline/[supplierId]` (Supplier Pipeline)

| Action Name | Trigger | Type | Files | Backend Call |
|-------------|---------|------|-------|--------------|
| Refresh pipeline | Button click | read | `PipelineClient.tsx` | `GET /ops/suppliers/{id}/pipeline` |
| Run scrape | Button click | mutate | `PipelineClient.tsx` | `POST /ops/enqueue` (SCRAPE_SUPPLIER) |
| Backfill images | Button click | mutate | `PipelineClient.tsx` | `POST /ops/enqueue` (BACKFILL_IMAGES_ONECHEQ) |
| Run enrich | Button click | mutate | `PipelineClient.tsx` | `POST /ops/enqueue` (ENRICH_SUPPLIER) |
| Build drafts | Button click | mutate | `PipelineClient.tsx` | `POST /ops/bulk/dryrun_publish` |
| View running scrape | Link click | navigate | `PipelineClient.tsx` | - |
| View running images | Link click | navigate | `PipelineClient.tsx` | - |
| View running enrich | Link click | navigate | `PipelineClient.tsx` | - |
| View drafts | Link click | navigate | `PipelineClient.tsx` | - |
| Open vault links | Link click | navigate | `PipelineClient.tsx` | - |
| Navigate to Trade Me health | Link click | navigate | `PipelineClient.tsx` | - |
| Navigate to Readiness | Link click | navigate | `PipelineClient.tsx` | - |
| Navigate to Publish console | Link click | navigate | `PipelineClient.tsx` | - |
| Navigate to command detail | Link click | navigate | `PipelineClient.tsx` | - |
| Auto-refresh (when active) | Timer | read | `PipelineClient.tsx` | `GET /ops/suppliers/{id}/pipeline` |

### `/products` (Products List)

| Action Name | Trigger | Type | Files | Backend Call |
|-------------|---------|------|-------|--------------|
| Search products | Form input | navigate | `ProductsClient.tsx` | - |
| Filter by supplier ID | Form input | navigate | `ProductsClient.tsx` | - |
| Filter by source category | Form input | navigate | `ProductsClient.tsx` | - |
| Filter by stage | Select change | navigate | `ProductsClient.tsx` | - |
| Apply filters | Form submit | navigate | `ProductsClient.tsx` | - |
| Reset filters | Link click | navigate | `ProductsClient.tsx` | - |
| Navigate to product detail | Link click | navigate | `ProductsClient.tsx` | - |
| Navigate to raw vault | Link click | navigate | `ProductsClient.tsx` | - |
| Navigate to enriched vault | Link click | navigate | `ProductsClient.tsx` | - |
| Paginate | DataTable controls | navigate | `DataTable.tsx` | - |

### `/products/[id]` (Product Inspector)

| Action Name | Trigger | Type | Files | Backend Call |
|-------------|---------|------|-------|--------------|
| Navigate to supplier page | External link | navigate | `products/[id]/page.tsx` | - |
| Navigate to Vault 2 | Link click | navigate | `products/[id]/page.tsx` | - |
| View buyer preview | Link click | navigate | `products/[id]/page.tsx` | - |
| Open image full-size | Link click | navigate | `products/[id]/page.tsx` | - |

### `/suppliers` (Suppliers List)

| Action Name | Trigger | Type | Files | Backend Call |
|-------------|---------|------|-------|--------------|
| Navigate to supplier detail | Link click | navigate | `suppliers/page.tsx` | - |

### `/suppliers/[id]` (Supplier Detail)

| Action Name | Trigger | Type | Files | Backend Call |
|-------------|---------|------|-------|--------------|
| Refresh policy | Button click | read | `PolicyEditor.tsx` | `GET /suppliers/{id}/policy` |
| Save policy | Button click | mutate | `PolicyEditor.tsx` | `PUT /suppliers/{id}/policy` |
| Enable supplier | Button click | mutate | `PolicyEditor.tsx` | `PUT /suppliers/{id}/policy` |
| Disable supplier | Button click | mutate | `PolicyEditor.tsx` | `PUT /suppliers/{id}/policy` |
| Toggle scrape enabled | Checkbox | mutate | `PolicyEditor.tsx` | (local state, needs Save) |
| Toggle enrich enabled | Checkbox | mutate | `PolicyEditor.tsx` | (local state, needs Save) |
| Toggle publish enabled | Checkbox | mutate | `PolicyEditor.tsx` | (local state, needs Save) |
| Edit policy JSON | Textarea | mutate | `PolicyEditor.tsx` | (local state, needs Save) |

### `/vaults/raw` (Vault 1 - Raw Products)

| Action Name | Trigger | Type | Files | Backend Call |
|-------------|---------|------|-------|--------------|
| Search products | Form input | navigate | `RawVaultClient.tsx` | - |
| Filter by supplier ID | Form input | navigate | `RawVaultClient.tsx` | - |
| Filter by sync status | Select change | navigate | `RawVaultClient.tsx` | - |
| Filter by source category | Form input | navigate | `RawVaultClient.tsx` | - |
| Apply filters | Form submit | navigate | `RawVaultClient.tsx` | - |
| Reset filters | Link click | navigate | `RawVaultClient.tsx` | - |
| Clear filter chip | Link click | navigate | `RawVaultClient.tsx` | - |
| Refresh data | Button click | read | `RawVaultClient.tsx` | `GET /vaults/raw` |
| Toggle auto-refresh | Checkbox | read | `RawVaultClient.tsx` | - |
| Navigate to product detail | Link click | navigate | `RawVaultClient.tsx` | - |
| Open supplier page | External link | navigate | `RawVaultClient.tsx` | - |
| Paginate | DataTable controls | navigate | `DataTable.tsx` | - |

### `/vaults/raw/[id]` (Raw Product Detail)

| Action Name | Trigger | Type | Files | Backend Call |
|-------------|---------|------|-------|--------------|
| Switch tab | Link click | navigate | `vaults/raw/[id]/page.tsx` | - |
| Open supplier page | External link | navigate | `vaults/raw/[id]/page.tsx` | - |
| Navigate to enriched product | Link click | navigate | `vaults/raw/[id]/page.tsx` | - |
| Open image full-size | Link click | navigate | `vaults/raw/[id]/page.tsx` | - |
| Navigate to Vault 1 list | Link click | navigate | `vaults/raw/[id]/page.tsx` | - |

### `/vaults/enriched` (Vault 2 - Enriched Products)

| Action Name | Trigger | Type | Files | Backend Call |
|-------------|---------|------|-------|--------------|
| Search products | Form input | navigate | `EnrichedVaultClient.tsx` | - |
| Filter by supplier ID | Form input | navigate | `EnrichedVaultClient.tsx` | - |
| Filter by enrichment status | Select change | navigate | `EnrichedVaultClient.tsx` | - |
| Apply filters | Form submit | navigate | `EnrichedVaultClient.tsx` | - |
| Reset filters | Link click | navigate | `EnrichedVaultClient.tsx` | - |
| Clear filter chip | Link click | navigate | `EnrichedVaultClient.tsx` | - |
| Navigate to product detail | Link click | navigate | `EnrichedVaultClient.tsx` | - |
| Open supplier page | External link | navigate | `EnrichedVaultClient.tsx` | - |
| Paginate | DataTable controls | navigate | `DataTable.tsx` | - |

### `/vaults/enriched/[id]` (Enriched Product Detail)

| Action Name | Trigger | Type | Files | Backend Call |
|-------------|---------|------|-------|--------------|
| Switch tab | Link click | navigate | `vaults/enriched/[id]/page.tsx` | - |
| Open supplier page | External link | navigate | `vaults/enriched/[id]/page.tsx` | - |
| Navigate to raw product | Link click | navigate | `vaults/enriched/[id]/page.tsx` | - |
| Navigate to Vault 2 list | Link click | navigate | `vaults/enriched/[id]/page.tsx` | - |
| Open image full-size | Link click | navigate | `vaults/enriched/[id]/page.tsx` | - |
| Reset enrichment | Button click | mutate | `vaults/enriched/[id]/Actions.tsx` | `POST /commands` (RESET_ENRICHMENT) |
| Create draft | Button click | mutate | `vaults/enriched/[id]/Actions.tsx` | `POST /commands` (PUBLISH_LISTING, dry_run) |
| Publish (go live) | Button click | mutate | `vaults/enriched/[id]/Actions.tsx` | `POST /commands` (PUBLISH_LISTING) |

### `/vaults/live` (Vault 3 - Listings)

| Action Name | Trigger | Type | Files | Backend Call |
|-------------|---------|------|-------|--------------|
| Search listings | Form input | navigate | `LiveVaultClient.tsx` | - |
| Filter by status | Select change | navigate | `LiveVaultClient.tsx` | - |
| Filter by supplier ID | Form input | navigate | `LiveVaultClient.tsx` | - |
| Apply filters | Form submit | navigate | `LiveVaultClient.tsx` | - |
| Reset filters | Link click | navigate | `LiveVaultClient.tsx` | - |
| Clear filter chip | Link click | navigate | `LiveVaultClient.tsx` | - |
| Navigate to listing detail | Link click | navigate | `LiveVaultClient.tsx` | - |
| Paginate | DataTable controls | navigate | `DataTable.tsx` | - |

### `/vaults/live/[id]` (Listing Detail)

| Action Name | Trigger | Type | Files | Backend Call |
|-------------|---------|------|-------|--------------|
| Switch tab | Link click | navigate | `vaults/live/[id]/page.tsx` | - |
| Navigate to internal product | Link click | navigate | `vaults/live/[id]/page.tsx` | - |
| Navigate to supplier product | Link click | navigate | `vaults/live/[id]/page.tsx` | - |
| Navigate to Vault 3 list | Link click | navigate | `vaults/live/[id]/page.tsx` | - |
| Navigate to Audit log | Link click | navigate | `vaults/live/[id]/page.tsx` | - |
| Open image full-size | Link click | navigate | `vaults/live/[id]/page.tsx` | - |
| Scan competitors | Button click | mutate | `vaults/live/[id]/Actions.tsx` | `POST /commands` (SCAN_COMPETITORS) |
| Sync sold items | Button click | mutate | `vaults/live/[id]/Actions.tsx` | `POST /commands` (SYNC_SOLD_ITEMS) |

---

## Action Summary Table

| Category | Read | Navigate | Mutate | Total |
|----------|------|----------|--------|-------|
| Dashboard/Home | 2 | 10 | 0 | 12 |
| Access/Settings | 1 | 1 | 6 | 8 |
| Fulfillment | 0 | 6 | 0 | 6 |
| Ops (Bulk) | 1 | 0 | 12 | 13 |
| Ops (Commands) | 2 | 12 | 3 | 17 |
| Ops (Inbox) | 0 | 1 | 3 | 4 |
| Ops (Readiness) | 1 | 2 | 0 | 3 |
| Ops (Removed) | 0 | 3 | 1 | 4 |
| Ops (Trade Me) | 1 | 2 | 1 | 4 |
| Orders | 0 | 8 | 0 | 8 |
| Pipeline | 3 | 14 | 4 | 21 |
| Products | 0 | 12 | 0 | 12 |
| Suppliers | 1 | 2 | 6 | 9 |
| Vault 1 (Raw) | 2 | 12 | 0 | 14 |
| Vault 2 (Enriched) | 0 | 13 | 3 | 16 |
| Vault 3 (Live) | 0 | 11 | 2 | 13 |
| **TOTAL** | **14** | **109** | **41** | **164** |

---

## Duplicate Detection

### Duplicate Group 1: Enqueue Command

**Pattern:** `POST /ops/enqueue` or `POST /commands`  
**Intent:** Queue a background command for processing

| Canonical | Duplicates | Files |
|-----------|------------|-------|
| `enqueue()` | 6+ implementations | `PipelineClient.tsx`, `ops/bulk/ui.tsx`, `vaults/enriched/[id]/Actions.tsx`, `vaults/live/[id]/Actions.tsx` |

**Recommendation:** Extract to shared hook `useEnqueue()` or utility function in `_components/api_client.ts`

### Duplicate Group 2: Command Actions (Retry/Ack/Cancel)

**Pattern:** `POST /commands/{id}/retry`, `POST /commands/{id}/ack`, `POST /commands/{id}/cancel`  
**Intent:** Manage command lifecycle

| Instance | File |
|----------|------|
| `CommandActions` | `ops/commands/[id]/Actions.tsx` |
| `InboxCommandActions` | `ops/inbox/Actions.tsx` |

**Recommendation:** Extract shared component `CommandActionButtons` with common logic

### Duplicate Group 3: Sync Sold/Selling Items

**Pattern:** `POST /ops/enqueue` with type `SYNC_SOLD_ITEMS` or `SYNC_SELLING_ITEMS`

| Instance | File |
|----------|------|
| Bulk ops | `ops/bulk/ui.tsx` |
| Listing actions | `vaults/live/[id]/Actions.tsx` |

**Recommendation:** Create shared action or consolidate into single location

### Duplicate Group 4: Image URL Transform (`imgSrc`)

**Pattern:** Convert `/media/` paths to `/api/media/`

| Instance | File |
|----------|------|
| `imgSrc()` | `products/ProductsClient.tsx` |
| `imgSrc()` | `vaults/raw/RawVaultClient.tsx` |
| `imgSrc()` | `vaults/raw/[id]/page.tsx` |
| `imgSrc()` | `vaults/enriched/EnrichedVaultClient.tsx` |
| `imgSrc()` | `vaults/enriched/[id]/page.tsx` |
| `imgSrc()` | `vaults/live/LiveVaultClient.tsx` |
| `imgSrc()` | `products/[id]/page.tsx` |

**Recommendation:** Extract to `_components/media.ts` as shared utility

### Duplicate Group 5: Filter/Search Form Pattern

**Pattern:** Form with inputs for search, supplier_id, status filters

| Instance | File |
|----------|------|
| Raw vault filters | `RawVaultClient.tsx` |
| Enriched vault filters | `EnrichedVaultClient.tsx` |
| Live vault filters | `LiveVaultClient.tsx` |
| Products filters | `ProductsClient.tsx` |
| Orders filters | `orders/page.tsx` |
| Commands filters | `ops/commands/page.tsx` |

**Recommendation:** Create shared `FilterForm` component with configurable fields

### Duplicate Group 6: Spinner Component

**Pattern:** Loading spinner during async operations

| Instance | File |
|----------|------|
| `Spinner()` | `ops/bulk/ui.tsx` |
| `Spinner()` | `vaults/enriched/[id]/Actions.tsx` |
| `Spinner()` | `vaults/live/[id]/Actions.tsx` |

**Recommendation:** Extract to `_components/Spinner.tsx`

### Duplicate Group 7: Field Display Component

**Pattern:** Label + Value display box

| Instance | File |
|----------|------|
| `Field()` | `vaults/raw/[id]/page.tsx` |
| `Field()` | `vaults/enriched/[id]/page.tsx` |
| `Field()` | `vaults/live/[id]/page.tsx` |
| `Field()` | `ops/commands/[id]/page.tsx` |

**Recommendation:** Extract to `components/ui/Field.tsx`

### Duplicate Group 8: formatNZT Usage

**Pattern:** Format timestamps to NZ timezone

| Usage Count | Files |
|-------------|-------|
| 15+ | Most page and client components |

**Status:** Already centralized in `_components/time.ts` ✓

---

## Shared Components

### Currently Shared

| Component | Location | Used By |
|-----------|----------|---------|
| `DataTable` | `components/tables/DataTable.tsx` | Products, Vaults, Readiness |
| `PageHeader` | `components/ui/PageHeader.tsx` | Most pages |
| `SectionCard` | `components/ui/SectionCard.tsx` | Most detail pages |
| `StatusBadge` | `components/ui/StatusBadge.tsx` | All status displays |
| `FilterChips` | `components/ui/FilterChips.tsx` | Vault lists, Orders |
| `Badge` | `_components/Badge.tsx` | Headers, status indicators |
| `buttonClass` | `_components/ui.ts` | All buttons |
| `apiGet` / `apiPost` | `_components/api.ts`, `_components/api_client.ts` | All API calls |
| `formatNZT` | `_components/time.ts` | All timestamps |

### Recommended New Shared Components

1. **`useEnqueue`** - Custom hook for queueing commands
2. **`CommandActionButtons`** - Retry/Ack/Cancel button group
3. **`imgSrc`** - Media URL transformer utility
4. **`Spinner`** - Loading indicator
5. **`Field`** - Label/value display pair
6. **`VaultFilterForm`** - Reusable filter form for vaults

---

## API Endpoints Summary

| Method | Endpoint | Used By |
|--------|----------|---------|
| GET | `/ops/summary` | Home |
| GET | `/trademe/account_summary` | Home, Trade Me Health |
| GET | `/suppliers` | Suppliers, Pipeline, Bulk |
| GET | `/suppliers/{id}/policy` | Supplier Detail, Bulk |
| PUT | `/suppliers/{id}/policy` | Supplier Detail |
| GET | `/settings/{key}` | Settings |
| PUT | `/settings/{key}` | Settings |
| GET | `/ops/inbox` | Inbox |
| GET | `/ops/readiness` | Readiness |
| GET | `/ops/removed_items` | Removed Items |
| GET | `/ops/suppliers/{id}/pipeline` | Pipeline |
| GET | `/commands` | Commands List |
| GET | `/commands/{id}` | Command Detail |
| POST | `/commands/{id}/retry` | Command Actions |
| POST | `/commands/{id}/ack` | Command Actions |
| POST | `/commands/{id}/cancel` | Command Actions |
| POST | `/commands` | Direct enqueue |
| POST | `/ops/enqueue` | Pipeline, Bulk |
| POST | `/ops/bulk/dryrun_publish` | Pipeline, Bulk |
| POST | `/ops/bulk/approve_publish` | Bulk |
| POST | `/ops/bulk/reset_enrichment` | Bulk |
| POST | `/ops/bulk/withdraw_removed` | Removed Items |
| POST | `/trademe/validate_drafts` | Trade Me Health |
| GET | `/orders` | Orders |
| GET | `/products` | Products |
| GET | `/inspector/supplier-products/{id}` | Product Detail |
| GET | `/supplier-products/{id}` | Raw Detail |
| GET | `/internal-products/{id}` | Enriched Detail |
| GET | `/trust/internal-products/{id}` | Enriched Detail |
| GET | `/validate/internal-products/{id}` | Enriched Detail |
| GET | `/draft/internal-products/{id}/trademe` | Raw/Enriched Detail |
| GET | `/listings/{id}` | Listing Detail |
| GET | `/vaults/raw` | Raw Vault |
| GET | `/vaults/enriched` | Enriched Vault |
| GET | `/vaults/live` | Live Vault |

---

*End of UI Action Catalog*
