"use client";

import { useState } from "react";
import { apiPostClient } from "../../_components/api_client";

type Resp = { id: string; status: string };

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="text-sm font-semibold">{title}</div>
      <div className="mt-3">{children}</div>
    </div>
  );
}

export function BulkOpsForm() {
  const [supplierId, setSupplierId] = useState<string>("");
  const [supplierName, setSupplierName] = useState<string>("");
  const [sourceCategory, setSourceCategory] = useState<string>("");
  const [pages, setPages] = useState<string>("1");
  const [batchSize, setBatchSize] = useState<string>("25");
  const [msg, setMsg] = useState<string | null>(null);

  async function enqueue(type: string, payload: Record<string, unknown>, priority = 60) {
    setMsg(null);
    try {
      const res = await apiPostClient<Resp>("/ops/enqueue", { type, payload, priority });
      setMsg(`Enqueued ${type} (${res.id.slice(0, 12)})`);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Failed to enqueue");
    }
  }

  return (
    <div className="space-y-4">
      {msg ? <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-900">{msg}</div> : null}

      <Section title="Scope">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <label className="text-xs text-slate-600">
            <div className="mb-1 font-semibold uppercase tracking-wide">supplier_id</div>
            <input
              className="w-full rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
              value={supplierId}
              onChange={(e) => setSupplierId(e.target.value)}
              placeholder="e.g. 1"
            />
          </label>
          <label className="text-xs text-slate-600">
            <div className="mb-1 font-semibold uppercase tracking-wide">supplier_name</div>
            <input
              className="w-full rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
              value={supplierName}
              onChange={(e) => setSupplierName(e.target.value)}
              placeholder="e.g. CASH_CONVERTERS"
            />
          </label>
          <label className="text-xs text-slate-600 md:col-span-2">
            <div className="mb-1 font-semibold uppercase tracking-wide">source_category</div>
            <input
              className="w-full rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
              value={sourceCategory}
              onChange={(e) => setSourceCategory(e.target.value)}
              placeholder="CC browse_url / NL category_url / OC collection handle"
            />
          </label>
        </div>
      </Section>

      <Section title="Scrape supplier (category-scoped)">
        <div className="flex flex-wrap items-end gap-2">
          <label className="text-xs text-slate-600">
            <div className="mb-1 font-semibold uppercase tracking-wide">pages</div>
            <input
              className="w-20 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
              value={pages}
              onChange={(e) => setPages(e.target.value)}
            />
          </label>
          <button
            type="button"
            className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white"
            onClick={() =>
              enqueue(
                "SCRAPE_SUPPLIER",
                {
                  supplier_id: supplierId ? Number(supplierId) : undefined,
                  supplier_name: supplierName || undefined,
                  source_category: sourceCategory || undefined,
                  pages: Number(pages || "1"),
                },
                70,
              )
            }
          >
            Enqueue SCRAPE_SUPPLIER
          </button>
        </div>
      </Section>

      <Section title="Enrich supplier (category-scoped)">
        <div className="flex flex-wrap items-end gap-2">
          <label className="text-xs text-slate-600">
            <div className="mb-1 font-semibold uppercase tracking-wide">batch_size</div>
            <input
              className="w-24 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
              value={batchSize}
              onChange={(e) => setBatchSize(e.target.value)}
            />
          </label>
          <button
            type="button"
            className="rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white"
            onClick={() =>
              enqueue(
                "ENRICH_SUPPLIER",
                {
                  supplier_id: supplierId ? Number(supplierId) : undefined,
                  supplier_name: supplierName || undefined,
                  source_category: sourceCategory || undefined,
                  batch_size: Number(batchSize || "25"),
                  delay_seconds: 0,
                },
                60,
              )
            }
          >
            Enqueue ENRICH_SUPPLIER
          </button>
        </div>
      </Section>

      <Section title="Marketplace sync (ops)">
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-900"
            onClick={() => enqueue("SYNC_SOLD_ITEMS", {}, 80)}
          >
            Enqueue SYNC_SOLD_ITEMS
          </button>
          <button
            type="button"
            className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-900"
            onClick={() => enqueue("SYNC_SELLING_ITEMS", { limit: 50 }, 70)}
          >
            Enqueue SYNC_SELLING_ITEMS
          </button>
        </div>
      </Section>
    </div>
  );
}

