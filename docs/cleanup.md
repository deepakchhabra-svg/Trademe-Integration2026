# Cleanup (Mission 4)

This doc captures final deletions and responsibility locks to make the repo feel intentional and product-grade.

## Canonical pipeline (single answer)

- **Vault 1 (Raw)**: supplier truth only (`SupplierProduct`)
- **Vault 2 (Enriched)**: enriched copy on supplier product + internal product linkage
- **Vault 3 (Listings)**: Draft/Live listings with Trade Me payload preview
- **LaunchLock**: single readiness authority (hard gates + trust/policy/margin)
- **Listing builder**: consumes enriched fields only; no fallback templating

## Removed / locked down

- **Silent fallbacks removed from listing payload generation**:
  - `MarketplaceAdapter.prepare_for_trademe()` now requires `enriched_title` + `enriched_description` and blocks default category fallback.
  - AI enrichment path is explicitly disabled for listing payload generation (no hidden behavior changes).

- **Competitor scanning removed from operator flow** (out of pilot scope):
  - Orphaned endpoint/UI/dead code removed earlier; see `docs/orphans.md`.

## Safety defaults

- **Stop-on-failure default ON** for bulk draft creation and bulk publish approval (enqueues one at a time unless explicitly disabled).
- **Trade Me health is binary and honest**: publishing endpoints refuse to enqueue when credentials are missing / auth fails.

