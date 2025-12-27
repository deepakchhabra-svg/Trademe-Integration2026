"use client";

import { useState } from "react";
import { apiPostClient } from "../../../_components/api_client";

export function ListingActions({
  listingDbId,
  tmListingId,
  internalProductId,
}: {
  listingDbId: number;
  tmListingId: string | null;
  internalProductId: number | null;
}) {
  const [status, setStatus] = useState<string | null>(null);

  async function enqueue(type: string, payload: Record<string, unknown>) {
    setStatus(null);
    try {
      const res = await apiPostClient<{ id: string; status: string }>("/commands", { type, payload, priority: 40 });
      setStatus(`Enqueued ${type} (${res.id.slice(0, 12)})`);
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Failed to enqueue");
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-sm font-semibold">Actions</div>
          <div className="mt-1 text-xs text-slate-600">One-click ops actions (auditable via Commands + Audits).</div>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white"
          onClick={() =>
            enqueue("SCAN_COMPETITORS", {
              listing_db_id: listingDbId,
              tm_listing_id: tmListingId,
              internal_product_id: internalProductId,
            })
          }
        >
          Scan competitors
        </button>
        <button
          type="button"
          className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-900"
          onClick={() => enqueue("SYNC_SOLD_ITEMS", {})}
        >
          Sync sold items
        </button>
      </div>

      {status ? <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-2 text-xs text-slate-900">{status}</div> : null}
    </div>
  );
}

