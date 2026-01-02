# Duplicate Groups Analysis

> **Generated:** 2026-01-02
> **Method:** Clustering by Backend Operation ID (URI + Method + Intent)

## Group 1: Enqueue Scrape Supplier
**Operation:** `POST /ops/enqueue` (Scrape)
**Confidence:** High (Identical payload structure)

| Location | File | Intent |
|----------|------|--------|
| `/ops/bulk` | `ops/bulk/ui.tsx` | Bulk scrape all presets or specific selection |
| `/pipeline/[supplierId]` | `PipelineClient.tsx` | Scrape single supplier |

**Recommendation:**
Extract `useScrapeSupplier(supplierId)` hook that calls the shared API endpoint.

## Group 2: Enqueue Enrich Supplier
**Operation:** `POST /ops/enqueue` (Enrich)
**Confidence:** High

| Location | File | Intent |
|----------|------|--------|
| `/ops/bulk` | `ops/bulk/ui.tsx` | Bulk enrich all presets |
| `/pipeline/[supplierId]` | `PipelineClient.tsx` | Enrich single supplier |

**Recommendation:**
Extract `useEnrichSupplier(supplierId)` hook.

## Group 3: Bulk Dry Run Publish
**Operation:** `POST /ops/bulk/dryrun_publish`
**Confidence:** High

| Location | File | Intent |
|----------|------|--------|
| `/ops/bulk` | `ops/bulk/ui.tsx` | Create drafts for multiple suppliers |
| `/pipeline/[supplierId]` | `PipelineClient.tsx` | Create drafts for single supplier |

**Recommendation:**
Consolidate into `useBuildDrafts(supplierId?)`.

## Group 4: Sync Sold Items
**Operation:** `POST /ops/enqueue` (Sync Sold) vs `POST /commands` (Sync Sold)
**Confidence:** Medium (Start points differ but intent is identical)

| Location | File | Implementation |
|----------|------|----------------|
| `/ops/bulk` | `ops/bulk/ui.tsx` | Uses `/ops/enqueue` helper |
| `/vaults/live/[id]` | `vaults/live/[id]/Actions.tsx` | Uses direct `/commands` enqueue |

**Recommendation:**
Standardize on `/ops/enqueue` or a dedicated `useSyncSold()` hook to avoid divergent implementations.

## Group 5: Command Actions (Retry/Ack/Cancel)
**Operations:** `retry_command`, `ack_command`, `cancel_command`
**Confidence:** High (Exact duplications of logic)

| Location | File |
|----------|------|
| `/ops/commands/[id]` | `ops/commands/[id]/Actions.tsx` |
| `/ops/inbox` | `ops/inbox/Actions.tsx` |

**Recommendation:**
Create a shared `<CommandActions commandId={id} />` component. The inline inbox warnings/loading states are identical to the detail view.

## Group 6: Get Suppliers List
**Operation:** `GET /suppliers`
**Confidence:** High

| Location | File |
|----------|------|
| `/ops/bulk` | `ops/bulk/ui.tsx` |
| `/pipeline` | `pipeline/page.tsx` |
| `/suppliers` | `suppliers/page.tsx` |

**Recommendation:**
Keep as is. These are data fetches in Server Components (mostly), which is fine. The `ui.tsx` fetch could be passed down from a parent Server Component to reduce client-side fetching.

## Group 7: Get Draft Payload
**Operation:** `GET /draft/internal-products/{id}/trademe`
**Confidence:** High

| Location | File |
|----------|------|
| `/vaults/raw/[id]` | `vaults/raw/[id]/page.tsx` |
| `/vaults/enriched/[id]` | `vaults/enriched/[id]/page.tsx` |

**Recommendation:**
This likely implies a need for a shared "Preview Tab" component used in both vault views, rather than duplicating the fetch and render logic in both page files.

## Summary

| Cluster | Count | Type | Priority |
|---------|-------|------|----------|
| Enqueue Operations | 4 | Logic Duplicate | High |
| Command Actions | 2 | UI Component Duplicate | High |
| Data Fetching | 3 | Pattern Overlap | Low |

Total extractable shared logic units: **3** (Hooks: `usePipelineActions`, Components: `CommandActions`, `DraftPreview`).
