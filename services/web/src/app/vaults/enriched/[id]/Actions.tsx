"use client";

import { useState } from "react";

import { useEnqueue } from "../../../_hooks/useEnqueue";
import { buttonClass } from "../../../_components/ui";

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
  supplierId,
  supplierProductId,
  sourceStatus,
  blockers = [],
}: {
  internalProductId: number;
  supplierId: number | null;
  supplierProductId: number | null;
  sourceStatus: string | null;
  blockers?: string[];
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

  const { enqueue: runEnqueue } = useEnqueue();

  async function enqueue(type: string, payload: Record<string, unknown>): Promise<string> {
    const res = await runEnqueue({ type, payload, priority: 60 });
    return `Queued action (${(res.id || "000").slice(0, 12)})`;
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
          className={buttonClass({ variant: "outline", disabled: !!busyKey })}
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

        {supplierId && blockers.some((b) => b.toLowerCase().includes("image")) ? (
          <button
            type="button"
            disabled={!!busyKey}
            className={buttonClass({ variant: "outline", disabled: !!busyKey })}
            onClick={() => run("BACKFILL_IMAGES", () => enqueue("BACKFILL_IMAGES_ONECHEQ", { supplier_id: supplierId, priority: 80 }))}
          >
            {busyKey === "BACKFILL_IMAGES" ? "Queuing..." : "Backfill images"}
          </button>
        ) : null}

        <button
          type="button"
          disabled={!!busyKey || String(sourceStatus || "").toUpperCase() === "REMOVED"}
          aria-busy={busyKey === "DRY_RUN_PUBLISH"}
          className={buttonClass({ variant: "primary", disabled: !!busyKey || String(sourceStatus || "").toUpperCase() === "REMOVED" })}
          onClick={() => run("DRY_RUN_PUBLISH", () => enqueue("PUBLISH_LISTING", { internal_product_id: internalProductId, dry_run: true }))}
        >
          {busyKey === "DRY_RUN_PUBLISH" ? (
            <span className="inline-flex items-center gap-2">
              <Spinner /> Enqueuing…
            </span>
          ) : (
            "Create draft"
          )}
        </button>

        <button
          type="button"
          disabled={!!busyKey || String(sourceStatus || "").toUpperCase() === "REMOVED"}
          aria-busy={busyKey === "PUBLISH"}
          className={buttonClass({ variant: "success", disabled: !!busyKey || String(sourceStatus || "").toUpperCase() === "REMOVED" })}
          onClick={() => run("PUBLISH", () => enqueue("PUBLISH_LISTING", { internal_product_id: internalProductId, dry_run: false }))}
        >
          {busyKey === "PUBLISH" ? (
            <span className="inline-flex items-center gap-2">
              <Spinner /> Enqueuing…
            </span>
          ) : (
            "Publish (go live)"
          )}
        </button>
      </div>

      {String(sourceStatus || "").toUpperCase() === "REMOVED" ? (
        <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-2 text-xs text-slate-900">
          Listing blocked: this item is <span className="font-semibold">Removed from supplier</span>. Scrape again or replace the supplier truth before listing.
        </div>
      ) : null}

      {status ? <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-2 text-xs text-slate-900">{status}</div> : null}
    </div>
  );
}

