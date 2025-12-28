import Link from "next/link";
import { apiGet } from "./_components/api";
import { PageHeader } from "../components/ui/PageHeader";
import { SectionCard } from "../components/ui/SectionCard";
import { buttonClass } from "./_components/ui";

type OpsSummary = {
  commands: { total: number; pending: number; executing: number; human_required: number; failed: number };
  vaults: {
    raw_total: number;
    raw_present: number;
    enriched_total: number;
    enriched_ready: number;
    listings_total: number;
    listings_dry_run: number;
    listings_live: number;
  };
  orders: { total: number; pending_fulfillment: number };
};

export default async function Home() {
  let summary: OpsSummary | null = null;
  try {
    summary = await apiGet<OpsSummary>("/ops/summary");
  } catch {
    summary = null;
  }

  const headerActions = (
    <div className="flex flex-wrap gap-2">
      <Link
        className={buttonClass({ variant: "primary" })}
        href="/ops/bulk"
        data-testid="btn-nav-bulk"
      >
        Run a batch (Bulk Ops)
      </Link>
      <Link
        className={buttonClass({ variant: "outline" })}
        href="/ops/inbox"
        data-testid="btn-nav-inbox"
      >
        Inbox (exceptions)
      </Link>
    </div>
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Ops Workbench"
        subtitle="Run the store in a guided flow: Scrape → Enrich → Dry-run → Publish. Use Vaults for inspection; use Ops only when something breaks."
        actions={headerActions}
      />

      {summary ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          <SectionCard title="Queue" className="h-full">
            <div className="text-sm text-slate-900" data-testid="stat-queue-pending-exec">
              pending <span className="font-semibold" data-testid="val-pending">{summary.commands.pending}</span> · executing{" "}
              <span className="font-semibold" data-testid="val-executing">{summary.commands.executing}</span>
            </div>
            <div className="mt-1 text-sm text-slate-900" data-testid="stat-queue-human-failed">
              human <span className="font-semibold" data-testid="val-human">{summary.commands.human_required}</span> · failed{" "}
              <span className="font-semibold" data-testid="val-failed">{summary.commands.failed}</span>
            </div>
          </SectionCard>

          <SectionCard title="Vaults" className="h-full">
            <div className="text-sm text-slate-900" data-testid="stat-vaults-raw">
              raw <span className="font-semibold" data-testid="val-raw-present">{summary.vaults.raw_present}</span>/
              <span className="font-semibold" data-testid="val-raw-total">{summary.vaults.raw_total}</span>
            </div>
            <div className="mt-1 text-sm text-slate-900" data-testid="stat-vaults-enriched">
              enriched-ready <span className="font-semibold" data-testid="val-enriched-ready">{summary.vaults.enriched_ready}</span>/
              <span className="font-semibold" data-testid="val-enriched-total">{summary.vaults.enriched_total}</span>
            </div>
          </SectionCard>

          <SectionCard title="Listings" className="h-full">
            <div className="text-sm text-slate-900" data-testid="stat-listings-dry">
              DRY_RUN <span className="font-semibold" data-testid="val-listings-dry">{summary.vaults.listings_dry_run}</span>
            </div>
            <div className="mt-1 text-sm text-slate-900" data-testid="stat-listings-live">
              Live <span className="font-semibold" data-testid="val-listings-live">{summary.vaults.listings_live}</span>
            </div>
          </SectionCard>

          <SectionCard title="Fulfillment" className="h-full">
            <div className="text-sm text-slate-900" data-testid="stat-orders-pending">
              pending orders <span className="font-semibold" data-testid="val-orders-pending">{summary.orders.pending_fulfillment}</span>
            </div>
            <div className="mt-1 text-xs text-slate-500">Use Inbox to clear exceptions.</div>
          </SectionCard>
        </div>
      ) : (
        <SectionCard className="p-0">
          <div className="p-6 text-sm text-slate-600" data-testid="banner-summary-unavailable">
            Ops summary is unavailable at your current role. Switch role to <span className="font-mono">power</span> or{" "}
            <span className="font-mono">root</span>.
          </div>
        </SectionCard>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <SectionCard title="1) Scrape supplier truth">
          <p className="text-sm text-slate-600">
            Pull the latest catalog from suppliers into <span className="font-semibold">Vault 1</span>.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link className={buttonClass({ variant: "primary" })} href="/ops/bulk" data-testid="btn-scrape-enqueue">
              Enqueue SCRAPE_SUPPLIER
            </Link>
            <Link className={buttonClass({ variant: "outline" })} href="/vaults/raw" data-testid="btn-scrape-vault">
              Inspect Vault 1
            </Link>
          </div>
        </SectionCard>

        <SectionCard title="2) Enrich + standardize copy">
          <p className="text-sm text-slate-600">
            Generate listing-ready copy and create internal products in <span className="font-semibold">Vault 2</span>.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link className={buttonClass({ variant: "primary" })} href="/ops/bulk" data-testid="btn-enrich-enqueue">
              Enqueue ENRICH_SUPPLIER
            </Link>
            <Link className={buttonClass({ variant: "outline" })} href="/vaults/enriched" data-testid="btn-enrich-vault">
              Inspect Vault 2
            </Link>
          </div>
        </SectionCard>

        <SectionCard title="3) Dry-run publish (safe)">
          <p className="text-sm text-slate-600">
            Create DRY_RUN listing drafts to review payload and guardrails without spending.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link className={buttonClass({ variant: "primary" })} href="/ops/bulk" data-testid="btn-dryrun-enqueue">
              Enqueue DRY_RUN publish
            </Link>
            <Link className={buttonClass({ variant: "outline" })} href="/vaults/live?status=DRY_RUN" data-testid="btn-dryrun-vault">
              Review queue
            </Link>
          </div>
        </SectionCard>

        <SectionCard title="4) Approve publish (real)">
          <p className="text-sm text-slate-600">
            Promote DRY_RUN → PUBLISH in controlled batches (drift-safe, quota-safe, store-mode safe).
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link className={buttonClass({ variant: "primary" })} href="/ops/bulk" data-testid="btn-publish-enqueue">
              Enqueue PUBLISH from DRY_RUN
            </Link>
            <Link className={buttonClass({ variant: "outline" })} href="/ops/trademe" data-testid="btn-publish-trademe">
              Check balance/health
            </Link>
          </div>
        </SectionCard>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        <Link
          className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm hover:bg-slate-50 transition-colors"
          href="/ops/inbox"
          data-testid="card-nav-inbox"
        >
          <div className="text-sm font-semibold">Inbox</div>
          <div className="mt-1 text-xs text-slate-600">All HUMAN_REQUIRED + failed jobs + pending orders.</div>
        </Link>
        <Link
          className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm hover:bg-slate-50 transition-colors"
          href="/suppliers"
          data-testid="card-nav-suppliers"
        >
          <div className="text-sm font-semibold">Suppliers</div>
          <div className="mt-1 text-xs text-slate-600">Supplier health + category partitioning.</div>
        </Link>
        <Link
          className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm hover:bg-slate-50 transition-colors"
          href="/orders"
          data-testid="card-nav-orders"
        >
          <div className="text-sm font-semibold">Orders</div>
          <div className="mt-1 text-xs text-slate-600">Fulfillment workflow (human work).</div>
        </Link>
      </div>
    </div>
  );
}
