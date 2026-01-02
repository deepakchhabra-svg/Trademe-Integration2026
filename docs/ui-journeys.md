# UI User Journeys

> **Generated:** 2026-01-02
> **Scope:** `services/web/src/app/**`
> **Purpose:** Document key end-to-end user flows with precise Backend URI mapping.

---

## Journey 1: Supplier Onboarding

**Goal:** Configure a new supplier for automated listing on Trade Me
**Persona:** System Administrator / Operator

### Steps

1. **Navigate to Suppliers**
   - Route: `/suppliers`
   - Action: View list of configured suppliers
   - Method: `GET`
   - URI: `/suppliers`

2. **Open Supplier Detail**
   - Route: `/suppliers/[id]`
   - Action: Click on supplier name/ID
   - Method: `GET`
   - URI: `/suppliers/{id}/policy` (fetched by `PolicyEditor`)

3. **Enable Supplier**
   - Route: `/suppliers/[id]`
   - Action: Click "Enable supplier" button
   - Method: `PUT`
   - URI: `/suppliers/{id}/policy`
   - Payload keys: `policy`, `enable_scrape`, `enable_enrich`, `enable_publish`

4. **Configure Pipeline Settings**
   - Route: `/suppliers/[id]`
   - Action: Toggle scrape/enrich/publish checkboxes
   - Method: -
   - URI: - (Local state update until Save)

5. **Save Policy**
   - Route: `/suppliers/[id]`
   - Action: Click "Save" button
   - Method: `PUT`
   - URI: `/suppliers/{id}/policy`

6. **Verify Configuration**
   - Route: `/suppliers/[id]`
   - Action: Click "Refresh" to confirm saved state
   - Method: `GET`
   - URI: `/suppliers/{id}/policy`

---

## Journey 2: Product Pipeline (Scrape → Enrich → Draft)

**Goal:** Import products from supplier, enrich them with AI, and create listing drafts.
**Persona:** Operator

### Steps

1. **Open Pipeline Index**
   - Route: `/pipeline`
   - Action: View available suppliers
   - Method: `GET`
   - URI: `/suppliers`

2. **Select Supplier**
   - Route: `/pipeline`
   - Action: Click "Open pipeline"
   - Method: `GET`
   - URI: `/ops/suppliers/{id}/pipeline` (fetched by page)

3. **Run Scrape**
   - Route: `/pipeline/[supplierId]`
   - Action: Click "Run scrape" button
   - Method: `POST`
   - URI: `/ops/enqueue`
   - Payload: `{ type: "SCRAPE_SUPPLIER" }`

4. **Wait for Scrape Completion**
   - Route: `/pipeline/[supplierId]`
   - Action: Monitor progress via refresh
   - Method: `GET`
   - URI: `/ops/suppliers/{id}/pipeline`

5. **Run Enrich**
   - Route: `/pipeline/[supplierId]`
   - Action: Click "Run enrich" button
   - Method: `POST`
   - URI: `/ops/enqueue`
   - Payload: `{ type: "ENRICH_SUPPLIER" }`

6. **Build Drafts**
   - Route: `/pipeline/[supplierId]`
   - Action: Click "Build drafts" button
   - Method: `POST`
   - URI: `/ops/bulk/dryrun_publish`
   - Payload: `{ supplier_id: id }`

---

## Journey 3: Publish to Trade Me

**Goal:** Move approved drafts to live Trade Me listings.
**Persona:** Operator / Publisher

### Steps

1. **Check Trade Me Health**
   - Route: `/ops/trademe`
   - Action: Verify account balance
   - Method: `GET`
   - URI: `/trademe/account_summary`

2. **Check Publish Readiness**
   - Route: `/ops/readiness`
   - Action: Review ready vs blocked counts
   - Method: `GET`
   - URI: `/ops/readiness`

3. **Validate Sample Drafts**
   - Route: `/ops/trademe`
   - Action: Click "Validate 10"
   - Method: `POST`
   - URI: `/trademe/validate_drafts`

4. **Go to Bulk Ops Console**
   - Route: `/ops/bulk`
   - Action: Select Supplier
   - Method: `GET`
   - URI: `/suppliers`

5. **Publish Approved Drafts**
   - Route: `/ops/bulk`
   - Action: Click "Publish approved drafts"
   - Method: `POST`
   - URI: `/ops/bulk/approve_publish`
   - Payload: `{ supplier_id: id }`

6. **Monitor Publishing**
   - Route: `/ops/commands?type=PUBLISH_LISTING`
   - Action: Watch for success/failure
   - Method: `GET`
   - URI: `/commands`

---

## Journey 4: Operational Monitoring

**Goal:** Monitor system health and catch issues early.
**Persona:** Operator / Admin

### Steps

1. **Open Dashboard**
   - Route: `/`
   - Action: Review summary statistics
   - Method: `GET`
   - URI: `/ops/summary`

2. **Review Inbox**
   - Route: `/ops/inbox`
   - Action: Check human-required commands
   - Method: `GET`
   - URI: `/ops/inbox`

3. **Check Command Queue**
   - Route: `/ops/commands?status=ACTIVE`
   - Action: Monitor running commands
   - Method: `GET`
   - URI: `/commands`

4. **Monitor Removed Items**
   - Route: `/ops/removed`
   - Action: Check for removals
   - Method: `GET`
   - URI: `/ops/removed_items`

---

## Journey 5: Error Resolution

**Goal:** Diagnose and resolve failed commands.
**Persona:** Operator

### Steps

1. **Open Inbox**
   - Route: `/ops/inbox`
   - Action: detailed list of errors
   - Method: `GET`
   - URI: `/ops/inbox`

2. **Open Command Detail**
   - Route: `/ops/commands/[id]`
   - Action: View logs and payload
   - Method: `GET`
   - URI: `/commands/{id}`

3. **Retry Command**
   - Route: `/ops/commands/[id]`
   - Action: Click "Retry" button
   - Method: `POST`
   - URI: `/commands/{id}/retry`

4. **Or Acknowledge/Cancel**
   - Route: `/ops/commands/[id]`
   - Action: Click "Mark resolved"
   - Method: `POST`
   - URI: `/commands/{id}/ack`

---

## Journey 6: Inventory Lifecycle

**Goal:** Manage products through vaults.
**Persona:** Operator

### Steps

1. **View Raw Products**
   - Route: `/vaults/raw`
   - Action: Browse supplier items
   - Method: `GET`
   - URI: `/vaults/raw`

2. **View Enriched Detail**
   - Route: `/vaults/enriched/[id]`
   - Action: Check enrichment quality
   - Method: `GET`
   - URI: `/internal-products/{id}`

3. **Reset Enrichment**
   - Route: `/vaults/enriched/[id]`
   - Action: Click "Reset enrichment"
   - Method: `POST`
   - URI: `/commands`
   - Payload: `{ type: "RESET_ENRICHMENT" ... }`

4. **Withdraw Removed Listings**
   - Route: `/ops/removed`
   - Action: Click "Withdraw all removed items"
   - Method: `POST`
   - URI: `/ops/bulk/withdraw_removed`

---

## Journey 7: System Configuration

**Goal:** Configure system credentials and settings.
**Persona:** Admin

### Steps

1. **Access Token Setup**
   - Route: `/access`
   - Action: Save token to cookie
   - Method: -
   - URI: - (Client-side)

2. **Load Settings**
   - Route: `/admin/settings`
   - Action: View system settings
   - Method: `GET`
   - URI: `/settings/{key}`

3. **Update Setting**
   - Route: `/admin/settings`
   - Action: Save Shipping Template
   - Method: `PUT`
   - URI: `/settings/trademe.shipping.use_template`

---

## Journey 8: Product Inspection

**Goal:** Deep dive QA.
**Persona:** QA

### Steps

1. **Load Product Inspector**
   - Route: `/products/[id]`
   - Action: View supplier truth
   - Method: `GET`
   - URI: `/inspector/supplier-products/{id}`

2. **Preview Listing**
   - Route: `/vaults/live/[id]?tab=preview`
   - Action: View buyer preview
   - Method: `GET`
   - URI: `/listings/{id}`

---

## Journey 9: Bulk Operations

**Goal:** Batch processing.
**Persona:** Operator

### Steps

1. **Scrape All Presets**
   - Route: `/ops/bulk`
   - Action: Enqueue bulk scrape
   - Method: `POST`
   - URI: `/ops/enqueue`

2. **Enrich All Presets**
   - Route: `/ops/bulk`
   - Action: Enqueue bulk enrich
   - Method: `POST`
   - URI: `/ops/enqueue`

3. **Sync Marketplace Data**
   - Route: `/ops/bulk`
   - Action: Click "Sync sold items"
   - Method: `POST`
   - URI: `/ops/enqueue`
   - Payload: `{ type: "SYNC_SOLD_ITEMS" }`

---

## Journey 10: Order Fulfillment

**Goal:** Process Orders.
**Persona:** Fulfillment

### Steps

1. **Load Orders**
   - Route: `/orders`
   - Action: View pending orders
   - Method: `GET`
   - URI: `/orders`

2. **Process**
   - Route: `/fulfillment`
   - Action: (Manual process currently)
   - Method: -
   - URI: -
