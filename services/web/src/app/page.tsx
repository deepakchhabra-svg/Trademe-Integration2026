import Link from "next/link";
import { apiGet } from "./_components/api";

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
  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <h1 className="text-xl font-semibold tracking-tight">Ops Workbench</h1>
            <p className="mt-1 text-sm text-slate-600">
              Run the store in a guided flow: <span className="font-semibold">Scrape → Enrich → Dry-run → Publish</span>.
              Use Vaults for inspection; use Ops only when something breaks.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link className="rounded-md bg-slate-900 px-3 py-2 text-xs font-medium text-white" href="/ops/bulk">
              Run a batch (Bulk Ops)
            </Link>
            <Link className="rounded-md border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-900" href="/ops/inbox">
              Inbox (exceptions)
            </Link>
            <Link className="rounded-md border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-900" href="/vaults/live?status=DRY_RUN">
              Review DRY_RUN
            </Link>
          </div>
        </div>
      </div>

      {summary ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Queue</div>
            <div className="mt-2 text-sm text-slate-900">
              pending <span className="font-semibold">{summary.commands.pending}</span> · executing{" "}
              <span className="font-semibold">{summary.commands.executing}</span>
            </div>
            <div className="mt-1 text-sm text-slate-900">
              human <span className="font-semibold">{summary.commands.human_required}</span> · failed{" "}
              <span className="font-semibold">{summary.commands.failed}</span>
            </div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Vaults</div>
            <div className="mt-2 text-sm text-slate-900">
              raw <span className="font-semibold">{summary.vaults.raw_present}</span>/<span className="font-semibold">{summary.vaults.raw_total}</span>
            </div>
            <div className="mt-1 text-sm text-slate-900">
              enriched-ready <span className="font-semibold">{summary.vaults.enriched_ready}</span>/
              <span className="font-semibold">{summary.vaults.enriched_total}</span>
            </div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Listings</div>
            <div className="mt-2 text-sm text-slate-900">
              DRY_RUN <span className="font-semibold">{summary.vaults.listings_dry_run}</span>
            </div>
            <div className="mt-1 text-sm text-slate-900">
              Live <span className="font-semibold">{summary.vaults.listings_live}</span>
            </div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Fulfillment</div>
            <div className="mt-2 text-sm text-slate-900">
              pending orders <span className="font-semibold">{summary.orders.pending_fulfillment}</span>
            </div>
            <div className="mt-1 text-xs text-slate-500">Use Inbox to clear exceptions.</div>
          </div>
        </div>
      ) : (
        <div className="rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-600 shadow-sm">
          Ops summary is unavailable at your current role. Switch role to <span className="font-mono">power</span> or{" "}
          <span className="font-mono">root</span>.
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="text-sm font-semibold">1) Scrape supplier truth</div>
          <p className="mt-2 text-sm text-slate-600">
            Pull the latest catalog from suppliers into <span className="font-semibold">Vault 1</span>.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link className="rounded-md bg-slate-900 px-3 py-2 text-xs font-medium text-white" href="/ops/bulk">
              Enqueue SCRAPE_SUPPLIER
            </Link>
            <Link className="rounded-md border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-900" href="/vaults/raw">
              Inspect Vault 1
            </Link>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="text-sm font-semibold">2) Enrich + standardize copy</div>
          <p className="mt-2 text-sm text-slate-600">
            Generate listing-ready copy and create internal products in <span className="font-semibold">Vault 2</span>.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link className="rounded-md bg-slate-900 px-3 py-2 text-xs font-medium text-white" href="/ops/bulk">
              Enqueue ENRICH_SUPPLIER
            </Link>
            <Link className="rounded-md border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-900" href="/vaults/enriched">
              Inspect Vault 2
            </Link>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="text-sm font-semibold">3) Dry-run publish (safe)</div>
          <p className="mt-2 text-sm text-slate-600">
            Create DRY_RUN listing drafts to review payload and guardrails without spending.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link className="rounded-md bg-slate-900 px-3 py-2 text-xs font-medium text-white" href="/ops/bulk">
              Enqueue DRY_RUN publish
            </Link>
            <Link className="rounded-md border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-900" href="/vaults/live?status=DRY_RUN">
              Review queue
            </Link>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="text-sm font-semibold">4) Approve publish (real)</div>
          <p className="mt-2 text-sm text-slate-600">
            Promote DRY_RUN → PUBLISH in controlled batches (drift-safe, quota-safe, store-mode safe).
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link className="rounded-md bg-slate-900 px-3 py-2 text-xs font-medium text-white" href="/ops/bulk">
              Enqueue PUBLISH from DRY_RUN
            </Link>
            <Link className="rounded-md border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-900" href="/ops/trademe">
              Check balance/health
            </Link>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        <Link className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm hover:bg-slate-50" href="/ops/inbox">
          <div className="text-sm font-semibold">Inbox</div>
          <div className="mt-1 text-xs text-slate-600">All HUMAN_REQUIRED + failed jobs + pending orders.</div>
        </Link>
        <Link className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm hover:bg-slate-50" href="/suppliers">
          <div className="text-sm font-semibold">Suppliers</div>
          <div className="mt-1 text-xs text-slate-600">Supplier health + category partitioning.</div>
        </Link>
        <Link className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm hover:bg-slate-50" href="/orders">
          <div className="text-sm font-semibold">Orders</div>
          <div className="mt-1 text-xs text-slate-600">Fulfillment workflow (human work).</div>
        </Link>
      </div>
    </div>
  );
}
