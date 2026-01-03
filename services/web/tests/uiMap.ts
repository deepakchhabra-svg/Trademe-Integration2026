/**
 * UI Map for E2E tests.
 * This file serves as a single source of truth for selecting interactive elements.
 */

export const UI = {
    // Layout
    layout: {
        nav: {
            dashboard: 'lnk-nav-ops-workbench',
            // Derived from NavLink label sanitization in AppShell/NavLink
            vaultRaw: 'lnk-nav-vault-1-supplier-data',
            vaultEnriched: 'lnk-nav-vault-2-enriched-products',
            vaultLive: 'lnk-nav-vault-3-listings',
            suppliers: 'lnk-nav-suppliers',
            orders: 'lnk-nav-orders',
        }
    },

    // Common Components
    common: {
        table: {
            container: 'data-table',
            loading: 'table-loading',
            empty: 'table-empty',
            pagination: {
                current: 'pagination-current',
                next: 'pagination-next',
                prev: 'pagination-prev',
                first: 'pagination-first',
                last: 'pagination-last',
            }
        },
        pageHeader: {
            title: 'page-title',
            actions: 'page-actions',
        },
        error: {
            container: 'error-state',
            retry: 'btn-error-retry',
        }
    },

    // Pages
    pages: {
        dashboard: {
            bulkBatch: 'btn-nav-bulk',
            inbox: 'btn-nav-inbox',
            stats: {
                pending: 'val-pending',
                executing: 'val-executing',
                human: 'val-human',
                failed: 'val-failed',
            },
            actions: {
                scrape: 'btn-scrape-enqueue',
                enrich: 'btn-enrich-enqueue',
                dryRun: 'btn-dryrun-enqueue',
                publish: 'btn-publish-enqueue',
            }
        },
        bulkOps: {
            supplier: 'sel-bulk-supplier',
            category: 'inp-bulk-category',
            pages: 'inp-bulk-pages',
            scrapeBtn: 'btn-bulk-scrape',
            enrichBtn: 'btn-bulk-enrich',
            dryRunBtn: 'btn-bulk-dryrun',
            approveBtn: 'btn-bulk-approve',
        },
        vaults: {
            searchForm: 'search-form',
            searchInp: 'inp-search-q',
            searchApply: 'btn-search-apply',
            searchReset: 'lnk-search-reset',
            // Table specific links are dynamic lnk-id-{id}
        }
    }
};
