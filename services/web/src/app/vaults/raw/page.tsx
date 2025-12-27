type PageResponse<T> = { items: T[]; total: number };

type RawItem = {
  id: number;
  supplier_id: number | null;
  external_sku: string;
  title: string | null;
  cost_price: number | null;
  stock_level: number | null;
  sync_status: string | null;
  source_category?: string | null;
  enrichment_status?: string | null;
  enriched_title?: string | null;
  product_url: string | null;
  images: string[];
  last_scraped_at: string | null;
};

import Link from "next/link";
import { apiGet } from "../../_components/api";
import { Badge } from "../../_components/Badge";
import { buildQueryString } from "../../_components/pagination";
import { buttonClass, tableClass, tableHeadClass, tableRowClass } from "../../_components/ui";

function imgSrc(raw: string): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
  if (raw.startsWith("/media/")) return `${base}${raw}`;
  return raw;
}

export default async function RawVault({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; per_page?: string; q?: string; supplier_id?: string; sync_status?: string; source_category?: string }>;
}) {
  const sp = await searchParams;
  const page = Math.max(1, Number(sp.page || "1"));
  const perPage = Math.min(200, Math.max(10, Number(sp.per_page || "50")));
  const q = sp.q || "";
  const supplierId = sp.supplier_id || "";
  const syncStatus = sp.sync_status || "";
  const sourceCategory = sp.source_category || "";

  const qp = new URLSearchParams();
  qp.set("page", String(page));
  qp.set("per_page", String(perPage));
  if (q) qp.set("q", q);
  if (supplierId) qp.set("supplier_id", supplierId);
  if (syncStatus) qp.set("sync_status", syncStatus);
  if (sourceCategory) qp.set("source_category", sourceCategory);

  const data = await apiGet<PageResponse<RawItem>>(`/vaults/raw?${qp.toString()}`);

  const baseParams = {
    per_page: perPage,
    q,
    supplier_id: supplierId,
    sync_status: syncStatus,
    source_category: sourceCategory,
  };
  const prevHref = `/vaults/raw?${buildQueryString(baseParams, { page: Math.max(1, page - 1) })}`;
  const nextHref = `/vaults/raw?${buildQueryString(baseParams, { page: page + 1 })}`;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Vault 1 · Raw</h1>
          <p className="mt-1 text-sm text-slate-600">Supplier products (click a row for full inspector)</p>
        </div>
        <Badge tone="blue">
          Page {page} · {perPage}/page
        </Badge>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-col gap-3 border-b border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="text-sm text-slate-700">
            Showing {data.items.length} of {data.total}
          </div>
          <form className="flex flex-wrap items-center gap-2" method="get">
            <input type="hidden" name="page" value="1" />
            <label className="text-xs text-slate-600">
              <span className="mr-1">Search</span>
              <input
                name="q"
                defaultValue={q}
                className="w-52 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
                placeholder="title or sku"
              />
            </label>
            <label className="text-xs text-slate-600">
              <span className="mr-1">Supplier</span>
              <input
                name="supplier_id"
                defaultValue={supplierId}
                className="w-20 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
                placeholder="id"
              />
            </label>
            <label className="text-xs text-slate-600">
              <span className="mr-1">Sync</span>
              <input
                name="sync_status"
                defaultValue={syncStatus}
                className="w-28 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
                placeholder="PRESENT/REMOVED"
              />
            </label>
            <label className="text-xs text-slate-600">
              <span className="mr-1">Category</span>
              <input
                name="source_category"
                defaultValue={sourceCategory}
                className="w-56 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
                placeholder="collection/url"
              />
            </label>
            <label className="text-xs text-slate-600">
              <span className="mr-1">Per</span>
              <select
                name="per_page"
                defaultValue={String(perPage)}
                className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
              >
                <option value="25">25</option>
                <option value="50">50</option>
                <option value="100">100</option>
                <option value="200">200</option>
              </select>
            </label>
            <button type="submit" className={buttonClass({ variant: "primary" })}>
              Apply
            </button>
            <Link className="text-xs text-slate-600 underline" href="/vaults/raw">
              Reset
            </Link>
          </form>
        </div>
        <div className="overflow-x-auto">
          <table className={tableClass()}>
            <thead className={tableHeadClass()}>
              <tr>
                <th className="px-4 py-3">ID</th>
                <th className="px-4 py-3">Img</th>
                <th className="px-4 py-3">SKU</th>
                <th className="px-4 py-3">Title</th>
                <th className="px-4 py-3">Cost</th>
                <th className="px-4 py-3">Sync</th>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3">Enrichment</th>
                <th className="px-4 py-3">Scraped</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((it) => (
                <tr key={it.id} className={tableRowClass()}>
                  <td className="px-4 py-3">
                    <Link className="text-slate-900 underline" href={`/vaults/raw/${it.id}`}>
                      {it.id}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    {it.images?.length ? (
                      <Link href={`/vaults/raw/${it.id}`} className="block w-12">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          alt=""
                          src={imgSrc(it.images[0])}
                          className="h-10 w-12 rounded-md border border-slate-200 object-cover"
                        />
                      </Link>
                    ) : (
                      <div className="h-10 w-12 rounded-md border border-dashed border-slate-200 bg-slate-50" />
                    )}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">{it.external_sku}</td>
                  <td className="px-4 py-3">
                    <Link className="text-slate-900 hover:underline" href={`/vaults/raw/${it.id}`}>
                      {it.title || "-"}
                    </Link>
                  </td>
                  <td className="px-4 py-3">{it.cost_price == null ? "-" : `$${it.cost_price.toFixed(2)}`}</td>
                  <td className="px-4 py-3">{it.sync_status || "-"}</td>
                  <td className="px-4 py-3 font-mono text-[11px] text-slate-700">{it.source_category || "-"}</td>
                  <td className="px-4 py-3">{it.enrichment_status || "-"}</td>
                  <td className="px-4 py-3">{it.last_scraped_at || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex items-center justify-between border-t border-slate-200 p-4 text-sm">
          <Link
            className={`text-slate-700 underline ${page <= 1 ? "pointer-events-none opacity-40" : ""}`}
            href={prevHref}
          >
            Prev
          </Link>
          <div className="text-xs text-slate-600">Page {page}</div>
          <Link className="text-slate-700 underline" href={nextHref}>
            Next
          </Link>
        </div>
      </div>
    </div>
  );
}

