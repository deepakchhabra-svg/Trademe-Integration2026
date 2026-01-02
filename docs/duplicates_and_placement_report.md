# Duplicates and Placement Report

## Purpose
This document identifies duplicate functionality, misplaced features, and their resolution.

---

## 1. Duplicate Entry Points Identified

### 1.1 "Sync Sold Items" (Import Orders)
| Location | Path | Resolution |
|----------|------|------------|
| ✅ **KEEP** | Fulfillment Dashboard | Canonical location |
| ❌ Remove | `/ops/bulk` (Sourcing tab) | Hidden in v1.0 |
| ❌ Remove | Pipeline supplier detail | Hidden in v1.0 |

**Reasoning**: Order syncing is a Fulfillment concern, not Pipeline.

---

### 1.2 "Build Drafts" / "Dry Run Publish"
| Location | Path | Resolution |
|----------|------|------------|
| ✅ **KEEP** | Pipeline → Supplier → "Prepare for Publish" | Canonical (workflow step) |
| ⚠️ Rename | `/ops/bulk` → "Preview Publish Batch" | Keep but clarify it's for bulk review |

**Reasoning**: Single-supplier draft building belongs in Pipeline. Bulk review belongs in Publish Console.

---

### 1.3 "Withdraw Removed Items"
| Location | Path | Resolution |
|----------|------|------------|
| ✅ **KEEP** | Advanced → Unavailable Items | Canonical location |
| ❌ Remove | `/ops/bulk` (Maintenance tab) | Hidden in v1.0 |

**Reasoning**: Cleanup actions belong in Advanced, not Core workflow.

---

### 1.4 Command Actions (Retry/Cancel/Ack)
| Location | Path | Resolution |
|----------|------|------------|
| ✅ **KEEP** Retry only | Inbox list | Quick retry without navigating |
| ✅ **KEEP** All actions | Job Detail page | Full control |
| ❌ Remove Cancel/Ack | Inbox list | Too dangerous for one-click |

**Reasoning**: Retry is safe (idempotent). Cancel/Ack need confirmation on detail page.

---

### 1.5 "Sync Selling Items" (Reconcile Live)
| Location | Path | Resolution |
|----------|------|------------|
| ✅ **KEEP** | Advanced → Trade Me Account | Canonical (admin action) |
| ❌ Remove | `/ops/bulk` | Hidden in v1.0 |

**Reasoning**: Reconciliation is an advanced/audit action, not daily workflow.

---

## 2. Misplaced Features

### 2.1 Reprice in Vault Detail Pages
**Problem**: Individual reprice buttons in `/vaults/live/[id]` compete with bulk reprice.

**Resolution**: 
- Remove individual reprice from Core listing detail
- Available in Advanced mode via "Quick Actions" dropdown

---

### 2.2 "Scan Competitors" Button
**Problem**: Appears in multiple vault detail pages.

**Resolution**:
- Keep only in Live Listing Detail (where it makes sense)
- Remove from Raw/Enriched detail pages

---

### 2.3 Orders Page
**Problem**: `/orders` duplicates `/fulfillment`.

**Resolution**:
- Redirect `/orders` to `/fulfillment`
- Keep `/orders` route for API backward compatibility

---

## 3. Merged Features

### 3.1 Pipeline Actions Consolidated
**Before**: Scrape, Enrich, Backfill Images, Build Drafts were separate pages.

**After**: All in Pipeline → Supplier Detail → Workflow Steps (sequential buttons)

---

### 3.2 Bulk Ops Simplified
**Before**: 5 tabs with overlapping functionality.

**After**: 
- **Sourcing Tab**: Removed (moved to Pipeline)
- **Listing Tab**: Publish Preview + Approve
- **Reprice Tab**: Preview + Apply
- **Maintenance Tab**: Hidden in Advanced

---

## 4. Legacy Routes (Kept for Backward Compatibility)

| Route | Redirects To | Reason |
|-------|--------------|--------|
| `/orders` | `/fulfillment` | API/bookmark compatibility |
| `/ops/commands` | `/ops/inbox` (default) | Old bookmarks |
| `/vaults/raw` | Accessible in Advanced | Power users need it |

---

## 5. Removed/Hidden Elements Summary

| Element | Status | Can Restore? |
|---------|--------|--------------|
| `/ops/bulk` Sourcing tab | Hidden | Yes (via feature flag) |
| `/ops/bulk` Maintenance tab | Hidden | Yes (via feature flag) |
| Individual Reprice buttons | Hidden from Core | Yes (Advanced mode) |
| Ack/Cancel in Inbox list | Removed | No (by design) |
| Duplicate nav links | Removed | No |

---

## 6. Acceptance Criteria Verification

- [x] Each intent has exactly ONE Core entry point
- [x] Duplicate buttons identified and resolved  
- [x] Legacy routes redirect cleanly
- [x] Advanced features accessible but not in Core nav
- [x] No functionality removed permanently (only hidden/moved)

---

## 7. Migration Notes

### For Existing Users
1. Bookmark `/ops/commands` → automatically shows Inbox (failed jobs first)
2. "Sync sold" moved to Fulfillment section
3. "Build drafts" is now in Pipeline, not Bulk Ops

### For Developers
1. `/ops/enqueue` endpoint unchanged (backward compatible)
2. `/commands` API unchanged
3. Feature flags control visibility of hidden tabs:
   - `FEATURE_BULK_SOURCING=true` → Shows Sourcing tab
   - `FEATURE_BULK_MAINTENANCE=true` → Shows Maintenance tab
