import Link from "next/link";

import { NotImplemented } from "../_components/NotImplemented";

export default function FulfillmentHome() {
  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Fulfillment Console</h1>
          <p className="mt-1 text-sm text-slate-600">
            Operator workflows: packing, shipping, customer comms, cancellations, returns, refunds, and risk checks.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        <Link className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm hover:border-slate-300" href="/orders">
          <div className="text-sm font-semibold">Orders</div>
          <div className="mt-1 text-xs text-slate-600">Current order list and basic fulfillment status.</div>
        </Link>
        <Link className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm hover:border-slate-300" href="/fulfillment/shipments">
          <div className="text-sm font-semibold">Shipments</div>
          <div className="mt-1 text-xs text-slate-600">Labels, tracking numbers, carrier selection, delivery confirmation.</div>
        </Link>
        <Link className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm hover:border-slate-300" href="/fulfillment/messages">
          <div className="text-sm font-semibold">Customer comms</div>
          <div className="mt-1 text-xs text-slate-600">Templates, delay notices, order updates, feedback requests.</div>
        </Link>
        <Link className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm hover:border-slate-300" href="/fulfillment/returns">
          <div className="text-sm font-semibold">Returns</div>
          <div className="mt-1 text-xs text-slate-600">Return cases, RMA, inbound tracking, resolutions.</div>
        </Link>
        <Link className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm hover:border-slate-300" href="/fulfillment/refunds">
          <div className="text-sm font-semibold">Refunds</div>
          <div className="mt-1 text-xs text-slate-600">Refund execution, partial refunds, audit trail.</div>
        </Link>
        <Link className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm hover:border-slate-300" href="/fulfillment/risk">
          <div className="text-sm font-semibold">Risk & fraud</div>
          <div className="mt-1 text-xs text-slate-600">Blacklist/scam checks, duplicate orders, returning customers.</div>
        </Link>
      </div>

      <NotImplemented
        title="Fulfillment automation (roadmap)"
        notes={[
          { label: "packing", detail: "Packing checklist, item verification, photo evidence, exceptions." },
          { label: "shipping", detail: "Carrier integration, label generation, tracking + status pushes." },
          { label: "comms", detail: "Trade Me messages + customer email/SMS templates, delay comms, feedback requests." },
          { label: "refunds", detail: "Refund decisions, partial refunds, evidence + audit logs, ledger matching." },
          { label: "returns", detail: "Return cases, RMA, inbound inspection, restock/delist, refund triggers." },
          { label: "risk", detail: "Duplicate detection, spam/scam heuristics, blacklist, returning customer signals." },
        ]}
      />
    </div>
  );
}

