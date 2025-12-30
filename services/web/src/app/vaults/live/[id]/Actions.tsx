"use client";

import { useState } from "react";
import { apiPostClient } from "../../../_components/api_client";
import { buttonClass } from "../../../_components/ui";

function Spinner() {
  return (
    <span
      aria-hidden="true"
      className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-white/30 border-t-white"
    />
  );
}

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
  const [busyKey, setBusyKey] = useState<string | null>(null);

  async function run(key: string, fn: () => Promise<string>) {
    if (busyKey) return;
    setBusyKey(key);
    setStatus(`Working: ${key}…`);
    try {
      const s = await fn();
      setStatus(s);
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusyKey(null);
    }
  }

  async function enqueue(type: string, payload: Record<string, unknown>): Promise<string> {
    const res = await apiPostClient<{ id: string; status: string }>("/commands", { type, payload, priority: 40 });
    return `Queued action (${res.id.slice(0, 12)})`;
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
          disabled={!!busyKey}
          aria-busy={busyKey === "SCAN_COMPETITORS"}
          className={buttonClass({ variant: "primary", disabled: !!busyKey })}
          onClick={() =>
            run("SCAN_COMPETITORS", () =>
              enqueue("SCAN_COMPETITORS", {
                listing_db_id: listingDbId,
                tm_listing_id: tmListingId,
                internal_product_id: internalProductId,
              }),
            )
          }
        >
          {busyKey === "SCAN_COMPETITORS" ? (
            <span className="inline-flex items-center gap-2">
              <Spinner /> Enqueuing…
            </span>
          ) : (
            "Scan competitors"
          )}
        </button>
        <button
          type="button"
          disabled={!!busyKey}
          aria-busy={busyKey === "SYNC_SOLD_ITEMS"}
          className={buttonClass({ variant: "outline", disabled: !!busyKey })}
          onClick={() => run("SYNC_SOLD_ITEMS", () => enqueue("SYNC_SOLD_ITEMS", {}))}
        >
          {busyKey === "SYNC_SOLD_ITEMS" ? (
            <span className="inline-flex items-center gap-2">
              <span
                aria-hidden="true"
                className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-slate-300 border-t-slate-900"
              />
              Enqueuing…
            </span>
          ) : (
            "Sync sold items"
          )}
        </button>
      </div>

      {status ? <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-2 text-xs text-slate-900">{status}</div> : null}
    </div>
  );
}

