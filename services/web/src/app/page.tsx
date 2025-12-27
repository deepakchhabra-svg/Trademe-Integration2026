export default async function Home() {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-start justify-between gap-6">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Overview</h1>
          <p className="mt-1 text-sm text-slate-600">
            Use the sidebar to traverse records end-to-end (raw → enriched → listings → commands → audits → jobs → orders).
          </p>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {/* eslint-disable-next-line @next/next/no-html-link-for-pages */}
        <a className="rounded-lg border border-slate-200 bg-slate-50 p-4 hover:bg-slate-100" href="/vaults/raw">
          <div className="text-sm font-semibold">Vault 1 · Raw</div>
          <div className="mt-1 text-xs text-slate-600">Supplier truth, reconciliation evidence</div>
        </a>
        {/* eslint-disable-next-line @next/next/no-html-link-for-pages */}
        <a className="rounded-lg border border-slate-200 bg-slate-50 p-4 hover:bg-slate-100" href="/vaults/enriched">
          <div className="text-sm font-semibold">Vault 2 · Enriched</div>
          <div className="mt-1 text-xs text-slate-600">Enrichment status, copy, publish readiness</div>
        </a>
        {/* eslint-disable-next-line @next/next/no-html-link-for-pages */}
        <a className="rounded-lg border border-slate-200 bg-slate-50 p-4 hover:bg-slate-100" href="/vaults/live">
          <div className="text-sm font-semibold">Vault 3 · Listings</div>
          <div className="mt-1 text-xs text-slate-600">Lifecycle, payload drift, performance signals</div>
        </a>
        {/* eslint-disable-next-line @next/next/no-html-link-for-pages */}
        <a className="rounded-lg border border-slate-200 bg-slate-50 p-4 hover:bg-slate-100" href="/ops/commands">
          <div className="text-sm font-semibold">Commands</div>
          <div className="mt-1 text-xs text-slate-600">Queue, failures, payload inspection</div>
        </a>
        {/* eslint-disable-next-line @next/next/no-html-link-for-pages */}
        <a className="rounded-lg border border-slate-200 bg-slate-50 p-4 hover:bg-slate-100" href="/suppliers">
          <div className="text-sm font-semibold">Suppliers</div>
          <div className="mt-1 text-xs text-slate-600">Source health and category partitioning</div>
        </a>
        {/* eslint-disable-next-line @next/next/no-html-link-for-pages */}
        <a className="rounded-lg border border-slate-200 bg-slate-50 p-4 hover:bg-slate-100" href="/orders">
          <div className="text-sm font-semibold">Orders</div>
          <div className="mt-1 text-xs text-slate-600">Fulfillment attention & customer truth</div>
        </a>
      </div>
    </div>
  );
}
