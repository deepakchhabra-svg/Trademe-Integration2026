import Link from "next/link";
import { apiGet } from "./_components/api";
import { PageHeader } from "../components/ui/PageHeader";
import { SectionCard } from "../components/ui/SectionCard";
import { buttonClass } from "./_components/ui";

type OpsSummary = {
  utc?: string;
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
  const summary = await apiGet<OpsSummary>("/ops/summary");

  const headerActions = (
    <div className="flex flex-wrap gap-2">
      <Link
        className={buttonClass({ variant: "primary" })}
        href="/ops/bulk"
        data-testid="btn-nav-bulk"
      >
        Runbook
      </Link>
      <Link
        className={buttonClass({ variant: "outline" })}
        href="/ops/inbox"
        data-testid="btn-nav-inbox"
      >
        Inbox
      </Link>
    </div>
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Ops Workbench"
        subtitle="Operator flow: Scrape → Enrich & standardise → Create drafts → Publish approved."
        actions={
          <div className="flex flex-wrap items-center gap-3">
            <div className="text-xs text-slate-500">
              Last updated:{" "}
              <span className="font-mono text-slate-700">{summary.utc ? summary.utc.replace("T", " ").slice(0, 16) : "-"}</span>
            </div>
            <Link className={buttonClass({ variant: "link" })} href="/">
              Refresh
            </Link>
            {headerActions}
          </div>
        }
      />

      {summary ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          <SectionCard title="Queue" className="h-full">
            <div className="text-sm text-slate-900" data-testid="stat-queue-pending-exec">
              <Link className="hover:underline" href="/ops/queue?view=active">
                queued <span className="font-semibold" data-testid="val-pending">{summary.commands.pending}</span> · running{" "}
                <span className="font-semibold" data-testid="val-executing">{summary.commands.executing}</span>
              </Link>
            </div>
            <div className="mt-1 text-sm text-slate-900" data-testid="stat-queue-human-failed">
              <Link className="hover:underline" href="/ops/queue?view=attention">
                needs attention <span className="font-semibold" data-testid="val-human">{summary.commands.human_required}</span> · failed{" "}
                <span className="font-semibold" data-testid="val-failed">{summary.commands.failed}</span>
              </Link>
            </div>
            <div className="mt-2">
              <Link className={buttonClass({ variant: "link" })} href="/ops/queue?view=attention">
                View queue →
              </Link>
            </div>
          </SectionCard>

          <SectionCard title="Vaults" className="h-full">
            <div className="text-sm text-slate-900" data-testid="stat-vaults-raw">
              <Link className="hover:underline" href="/vaults/raw">
                raw <span className="font-semibold" data-testid="val-raw-present">{summary.vaults.raw_present}</span>/
                <span className="font-semibold" data-testid="val-raw-total">{summary.vaults.raw_total}</span>
              </Link>
            </div>
            <div className="mt-1 text-sm text-slate-900" data-testid="stat-vaults-enriched">
              <Link className="hover:underline" href="/vaults/enriched">
                enriched-ready <span className="font-semibold" data-testid="val-enriched-ready">{summary.vaults.enriched_ready}</span>/
                <span className="font-semibold" data-testid="val-enriched-total">{summary.vaults.enriched_total}</span>
              </Link>
            </div>
          </SectionCard>

          <SectionCard title="Listings" className="h-full">
            <div className="text-sm text-slate-900" data-testid="stat-listings-dry">
              <Link className="hover:underline" href="/vaults/live?status=DRY_RUN">
                Draft <span className="font-semibold" data-testid="val-listings-dry">{summary.vaults.listings_dry_run}</span>
              </Link>
            </div>
            <div className="mt-1 text-sm text-slate-900" data-testid="stat-listings-live">
              <Link className="hover:underline" href="/vaults/live?status=Live">
                Live <span className="font-semibold" data-testid="val-listings-live">{summary.vaults.listings_live}</span>
              </Link>
            </div>
          </SectionCard>

          <SectionCard title="Fulfillment" className="h-full">
            <div className="text-sm text-slate-900" data-testid="stat-orders-pending">
              <Link className="hover:underline" href="/orders">
                pending orders <span className="font-semibold" data-testid="val-orders-pending">{summary.orders.pending_fulfillment}</span>
              </Link>
            </div>
            <div className="mt-1 text-xs text-slate-500">Use Inbox to clear exceptions.</div>
          </SectionCard>
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <SectionCard title="1) Scrape supplier data">
          <p className="text-sm text-slate-600">
            Pull the latest catalog from suppliers into <span className="font-semibold">Vault 1</span>.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link className={buttonClass({ variant: "primary" })} href="/ops/bulk" data-testid="btn-scrape-enqueue">
              Start scrape
            </Link>
            <Link className={buttonClass({ variant: "outline" })} href="/vaults/raw" data-testid="btn-scrape-vault">
              View Vault 1
            </Link>
          </div>
        </SectionCard>

        <SectionCard title="2) Enrich & standardise">
          <p className="text-sm text-slate-600">
            Generate listing-ready copy and create internal products in <span className="font-semibold">Vault 2</span>.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link className={buttonClass({ variant: "primary" })} href="/ops/bulk" data-testid="btn-enrich-enqueue">
              Enrich now
            </Link>
            <Link className={buttonClass({ variant: "outline" })} href="/vaults/enriched" data-testid="btn-enrich-vault">
              View Vault 2
            </Link>
          </div>
        </SectionCard>

        <SectionCard title="3) Create drafts (safe)">
          <p className="text-sm text-slate-600">
            Create Draft listings to review payload and guardrails without spending.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link className={buttonClass({ variant: "primary" })} href="/ops/bulk" data-testid="btn-dryrun-enqueue">
              Create drafts
            </Link>
            <Link className={buttonClass({ variant: "outline" })} href="/vaults/live?status=DRY_RUN" data-testid="btn-dryrun-vault">
              Review drafts
            </Link>
          </div>
        </SectionCard>

        <SectionCard title="4) Publish approved">
          <p className="text-sm text-slate-600">
            Publish approved Drafts in controlled batches (drift-safe, quota-safe).
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link className={buttonClass({ variant: "primary" })} href="/ops/bulk" data-testid="btn-publish-enqueue">
              Publish approved drafts
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
          <div className="mt-1 text-xs text-slate-600">Exceptions needing attention (jobs + orders).</div>
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
