"use client";

import { useState } from "react";
import { apiPostClient } from "../../../_components/api_client";

function Spinner() {
  return (
    <span
      aria-hidden="true"
      className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-white/30 border-t-white"
    />
  );
}

export function EnrichedActions({
  internalProductId,
  supplierProductId,
}: {
  internalProductId: number;
  supplierProductId: number | null;
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
    const res = await apiPostClient<{ id: string; status: string }>("/commands", { type, payload, priority: 60 });
    return `Enqueued ${type} (${res.id.slice(0, 12)})`;
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold">Actions</div>
          <div className="mt-1 text-xs text-slate-600">Requeue enrichment, run dry-run publish, or publish.</div>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          disabled={!!busyKey}
          aria-busy={busyKey === "RESET_ENRICHMENT"}
          className={`rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-900 ${
            busyKey ? "cursor-not-allowed opacity-60" : "hover:bg-slate-50"
          }`}
          onClick={() => {
            if (!supplierProductId) {
              setStatus("No supplier product attached; cannot reset enrichment.");
              return;
            }
            run("RESET_ENRICHMENT", () => enqueue("RESET_ENRICHMENT", { supplier_product_id: supplierProductId }));
          }}
        >
          {busyKey === "RESET_ENRICHMENT" ? (
            <span className="inline-flex items-center gap-2">
              <span
                aria-hidden="true"
                className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-slate-300 border-t-slate-900"
              />
              Working…
            </span>
          ) : (
            "Reset enrichment"
          )}
        </button>

        <button
          type="button"
          disabled={!!busyKey}
          aria-busy={busyKey === "DRY_RUN_PUBLISH"}
          className={`rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white ${
            busyKey ? "cursor-not-allowed opacity-60" : "hover:bg-slate-800"
          }`}
          onClick={() => run("DRY_RUN_PUBLISH", () => enqueue("PUBLISH_LISTING", { internal_product_id: internalProductId, dry_run: true }))}
        >
          {busyKey === "DRY_RUN_PUBLISH" ? (
            <span className="inline-flex items-center gap-2">
              <Spinner /> Enqueuing…
            </span>
          ) : (
            "Dry-run publish"
          )}
        </button>

        <button
          type="button"
          disabled={!!busyKey}
          aria-busy={busyKey === "PUBLISH"}
          className={`rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white ${
            busyKey ? "cursor-not-allowed opacity-60" : "hover:bg-emerald-700"
          }`}
          onClick={() => run("PUBLISH", () => enqueue("PUBLISH_LISTING", { internal_product_id: internalProductId, dry_run: false }))}
        >
          {busyKey === "PUBLISH" ? (
            <span className="inline-flex items-center gap-2">
              <Spinner /> Enqueuing…
            </span>
          ) : (
            "Publish"
          )}
        </button>
      </div>

      {status ? <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-2 text-xs text-slate-900">{status}</div> : null}
    </div>
  );
}

