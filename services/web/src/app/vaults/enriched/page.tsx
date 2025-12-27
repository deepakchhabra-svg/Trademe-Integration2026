type PageResponse<T> = { items: T[]; total: number };

type EnrichedItem = {
  id: number;
  sku: string;
  title: string | null;
  supplier_product_id: number | null;
  supplier_id: number | null;
  cost_price: number | null;
  enriched_title: string | null;
  enriched_description: string | null;
  source_category?: string | null;
  product_url?: string | null;
  sync_status?: string | null;
  enrichment_status?: string | null;
};

import Link from "next/link";
import { apiGet } from "../../_components/api";
import { Badge } from "../../_components/Badge";

export default async function EnrichedVault({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; per_page?: string; q?: string; supplier_id?: string; enrichment?: string; source_category?: string }>;
}) {
  const sp = await searchParams;
  const page = Math.max(1, Number(sp.page || "1"));
  const perPage = Math.min(200, Math.max(10, Number(sp.per_page || "50")));

  const qp = new URLSearchParams();
  qp.set("page", String(page));
  qp.set("per_page", String(perPage));
  if (sp.q) qp.set("q", sp.q);
  if (sp.supplier_id) qp.set("supplier_id", sp.supplier_id);
  if (sp.enrichment) qp.set("enrichment", sp.enrichment);
  if (sp.source_category) qp.set("source_category", sp.source_category);

  const data = await apiGet<PageResponse<EnrichedItem>>(`/vaults/enriched?${qp.toString()}`);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Vault 2 · Enriched</h1>
          <p className="mt-1 text-sm text-slate-600">Internal products (click a row for trust + gate inspector)</p>
        </div>
        <Badge tone="blue">
          Page {page} · {perPage}/page
        </Badge>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-200 p-4">
          <div className="text-sm text-slate-700">
            Showing {data.items.length} of {data.total}
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">ID</th>
                <th className="px-4 py-3">SKU</th>
                <th className="px-4 py-3">Title</th>
                <th className="px-4 py-3">Cost</th>
                <th className="px-4 py-3">Sync</th>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3">Enrichment</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((it) => (
                <tr key={it.id} className="border-t border-slate-100 hover:bg-slate-50 align-top">
                  <td className="px-4 py-3">
                    <Link className="text-slate-900 underline" href={`/vaults/enriched/${it.id}`}>
                      {it.id}
                    </Link>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">{it.sku}</td>
                  <td className="px-4 py-3">{it.title || "-"}</td>
                  <td className="px-4 py-3">{it.cost_price == null ? "-" : `$${it.cost_price.toFixed(2)}`}</td>
                  <td className="px-4 py-3">{it.sync_status || "-"}</td>
                  <td className="px-4 py-3 font-mono text-[11px] text-slate-700">{it.source_category || "-"}</td>
                  <td className="px-4 py-3">{it.enrichment_status || (it.enriched_description ? "SUCCESS" : "-")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

