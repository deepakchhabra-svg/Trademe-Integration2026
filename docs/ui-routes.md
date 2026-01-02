# UI Routes Catalog
(As of 2026-01-01)

## Public / Shared
- `/` (Home/Dashboard Redirect)
- `/access` (Login/Role Selection)
- `/admin/settings` (System Config)

## Operations (Power Role)
**Dashboard & Monitoring**
- `/ops/inbox` (Operator Attention Required)
- `/ops/commands` (Command Queue)
- `/ops/commands/[id]` (Command Detail)
- `/ops/jobs` (Scheduled Jobs)
- `/ops/alerts` (System Alerts)
- `/ops/audits` (Audit Log)
- `/ops/readiness` (LaunchLock Status)
- `/ops/removed` (Removed Items Report)
- `/ops/bulk` (Bulk Operations Center)
- `/ops/queue` (Worker Queue Status)
- `/ops/trademe` (Account Health)
- `/ops/llm` (AI Provider Health)

**Pipeline Management**
- `/pipeline` (Summary)
- `/pipeline/[supplierId]` (Supplier Detail)

## Data Views (Vaults)
- `/vaults/raw` (Supplier Inputs)
- `/vaults/raw/[id]` (Detail)
- `/vaults/enriched` (Enriched Products)
- `/vaults/enriched/[id]` (Detail)
- `/vaults/live` (Trade Me Listings)
- `/vaults/live/[id]` (Detail)

## Fulfillment
- `/fulfillment` (Orders Dashboard)
- `/fulfillment/messages` (Buyer Questions)
- `/fulfillment/shipments` (Shipping Status)
- `/fulfillment/returns` (Returns Management)
- `/fulfillment/refunds` (Refunds)
- `/fulfillment/risk` (Fraud Check)
- `/orders` (Legacy Order View)

## Entities
- `/suppliers` (Supplier List)
- `/suppliers/[id]` (Supplier Detail)
- `/products` (Global Product Search)
- `/products/[id]` (Product Detail)
