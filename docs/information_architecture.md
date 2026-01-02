# Information Architecture — God-Level Trade Me Ops System

## North Star Mental Model
```
Dashboard → Pipeline → Publish → Live → Jobs/Inbox → Fulfillment
```

Every operator action follows this flow. No exceptions, no shortcuts to confusing pages.

---

## 1. Core Screens (5 + Fulfillment)

### 1.1 Store Dashboard (`/`)
**Purpose**: Morning health check. Where am I? What needs attention?

| Element | Content |
|---------|---------|
| KPI Cards | Revenue today, Orders pending, Live listings, Failed jobs |
| Quick Actions | Go to Pipeline, Go to Inbox, Go to Live |
| Status Banner | API health, Last scrape, Scheduler status |

**Actions Available**:
- Navigation only (no mutations on dashboard itself)

---

### 1.2 Pipeline (`/pipeline`, `/pipeline/[supplierId]`)
**Purpose**: Get products from suppliers into the system, enriched and ready to publish.

| Tab | Content |
|-----|---------|
| Overview | Supplier list with pipeline stage counts |
| Supplier Detail | Scrape → Enrich → Build Drafts workflow |

**Actions Available**:
| Button | Label | Backend Op | Preview Required |
|--------|-------|------------|------------------|
| 🔄 Scrape | "Refresh Products" | `SCRAPE_SUPPLIER` | No (read-only) |
| ✨ Enrich | "AI Enrich" | `ENRICH_SUPPLIER` | No |
| 📝 Build Drafts | "Prepare for Publish" | `bulk_dryrun_publish` | Shows count first |

---

### 1.3 Publish Console (`/ops/bulk`)
**Purpose**: Review and approve listings before they go live on Trade Me.

| Section | Content |
|---------|---------|
| Draft Queue | Products ready for approval |
| Validation Results | Per-item pass/fail with reasons |
| Bulk Actions | Approve selected, Reject, Edit |

**Actions Available**:
| Button | Label | Backend Op | Preview Required |
|--------|-------|------------|------------------|
| 👁️ Preview | "Preview Changes" | `bulk_dryrun_publish` | N/A (this IS preview) |
| ✅ Approve | "Publish to Trade Me" | `bulk_approve_publish` | Yes - shows payload hash |
| 💰 Reprice Preview | "Calculate New Prices" | `bulk_reprice` (dry_run=true) | N/A |
| 💰 Apply Prices | "Apply Price Changes" | `bulk_reprice` (dry_run=false) | Yes - shows diff |

---

### 1.4 Live Listings (`/vaults/live`, `/vaults/live/[id]`)
**Purpose**: Monitor and manage active Trade Me listings.

| Section | Content |
|---------|---------|
| List View | All live listings with price, views, status |
| Filters | Supplier, Price range, Age, Performance |
| Detail View | Full listing payload, metrics, actions |

**Actions Available**:
| Button | Label | Backend Op | Preview Required |
|--------|-------|------------|------------------|
| 🔍 View | "View Details" | GET listing | No |
| 📊 Metrics | "View Performance" | GET metrics | No |

*Note: Withdraw/Reprice individual items is in Advanced mode only.*

---

### 1.5 Jobs / Inbox (`/ops/inbox`, `/ops/commands`, `/ops/commands/[id]`)
**Purpose**: Track all background operations, handle failures.

| View | Content |
|------|---------|
| Inbox | Failed/attention-required jobs only |
| Jobs Log | All jobs with status, duration, outcome |
| Job Detail | Logs, retry/cancel/dismiss actions |

**Actions Available (Inbox)**:
| Button | Label | Backend Op |
|--------|-------|------------|
| 🔄 Retry | "Retry" | `retry_command` |
| ➡️ Open | "View Details" | Navigation |

**Actions Available (Job Detail Only)**:
| Button | Label | Backend Op |
|--------|-------|------------|
| 🔄 Retry | "Retry Job" | `retry_command` |
| ❌ Cancel | "Cancel Job" | `cancel_command` |
| ✓ Dismiss | "Mark Resolved" | `ack_command` |

---

### 1.6 Fulfillment (`/fulfillment`)
**Purpose**: Process sales from sold to shipped.

| Tab | Content |
|-----|---------|
| Orders | Pending dispatch, requires attention |
| Shipments | In-transit, delivered |
| Messages | Buyer questions (placeholder) |

**Actions Available**:
| Button | Label | Backend Op | Status |
|--------|-------|------------|--------|
| 📦 Mark Shipped | "Dispatch" | TBD | Planned |
| 💬 Reply | "Reply to Buyer" | TBD | Placeholder |

---

## 2. Advanced Screens (Power Users Only)

Accessed via hamburger menu → "Advanced Tools"

| Route | Name | Purpose |
|-------|------|---------|
| `/vaults/raw` | Raw Products | Unprocessed supplier data |
| `/vaults/enriched` | Ready Products | Enriched, not yet published |
| `/ops/readiness` | Publish Readiness | LaunchLock validation details |
| `/ops/removed` | Unavailable Items | Items removed by supplier |
| `/ops/duplicates` | Duplicate Manager | Resolve duplicate listings |
| `/ops/jobs` | Scheduled Jobs | Cron/scheduler status |
| `/ops/alerts` | System Alerts | Threshold breaches |
| `/ops/audits` | Audit Log | All state changes |
| `/ops/queue` | Worker Queue | Background job queue depth |
| `/ops/trademe` | Trade Me Account | Balance, API status |
| `/ops/llm` | AI Provider | LLM health and usage |
| `/products` | Product Search | Cross-supplier search |
| `/suppliers` | Supplier Config | Policies, settings |
| `/admin/settings` | System Settings | Global config |

---

## 3. Naming Glossary

| Old Label | New Label | Reason |
|-----------|-----------|--------|
| Vault 1 · Raw | Raw Products | "Vault" is developer jargon |
| Vault 2 · Enriched | Ready Products | Implies ready for publish |
| Vault 3 · Listings | Live Listings | Matches Trade Me terminology |
| Commands | Jobs | Everyday language |
| Command Log | Jobs History | Clearer |
| Enqueue | Start Job | What it actually does |
| Readiness | Publish Readiness | Context matters |
| Sync sold items | Import Orders | User intent |
| Sync selling items | Reconcile Live | What it checks |
| Acknowledge / Ack | Dismiss | Honest about effect |
| Inbox | Attention Required | Exactly what it is |

---

## 4. Navigation Structure

```
┌─────────────────────────────────────────────────────────────┐
│  [Logo]  Store Dashboard  │  Pipeline  │  Publish  │  Live  │  Jobs  │  Fulfillment  │  [≡ Advanced]  │
└─────────────────────────────────────────────────────────────┘
```

### Sidebar (when in section)
```
Pipeline:
  └─ All Suppliers
  └─ OneCheq
  └─ Cash Converters
  └─ Noel Leeming

Jobs:
  └─ Attention Required
  └─ All Jobs
  └─ Scheduled

Fulfillment:
  └─ Pending Orders
  └─ Shipped
  └─ Messages
```

---

## 5. Removed / Hidden Elements

| Element | Reason | Fate |
|---------|--------|------|
| `/orders` (legacy) | Duplicate of `/fulfillment` | Hidden, redirect to `/fulfillment` |
| Multiple "Sync sold" buttons | Duplicate entry points | Keep only in Fulfillment |
| "Build drafts" on bulk page | Duplicate of Pipeline action | Remove from bulk, keep in Pipeline |
| Ack/Cancel on Inbox list | Dangerous one-click | Move to Job Detail only |

---

## 6. Acceptance Criteria

- [ ] Operator can reach any core action in ≤2 clicks from relevant screen
- [ ] No jargon terms visible in Core screens
- [ ] All mutation buttons show confirmation or preview
- [ ] Advanced screens require explicit navigation (not in main nav)
- [ ] Every action has a single canonical location
