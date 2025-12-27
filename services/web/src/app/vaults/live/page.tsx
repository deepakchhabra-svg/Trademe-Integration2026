type PageResponse<T> = { items: T[]; total: number };

type LiveItem = {
  id: number;
  tm_listing_id: string | null;
  internal_product_id: number | null;
  actual_state: string | null;
  lifecycle_state: string | null;
  actual_price: number | null;
  view_count: number | null;
  watch_count: number | null;
  category_id: string | null;
  title?: string | null;
  thumb?: string | null;
  source_category?: string | null;
  last_synced_at: string | null;
};

import Link from "next/link";
import { apiGet } from "../../_components/api";
import { Badge } from "../../_components/Badge";
import { buildQueryString } from "../../_components/pagination";

function imgSrc(raw: string): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  if (raw.startsWith("/media/")) return `${base}${raw}`;
  return raw;
}

export default async function LiveVault({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; per_page?: string; q?: string; status?: string; supplier_id?: string; source_category?: string }>;
}) {
  const sp = await searchParams;
  const page = Math.max(1, Number(sp.page || "1"));
  const perPage = Math.min(200, Math.max(10, Number(sp.per_page || "50")));
  const q = sp.q || "";
  // Default view should show real listings only (not DRY_RUN drafts).
  const status = sp.status || "Live";
  const supplierId = sp.supplier_id || "";
  const sourceCategory = sp.source_category || "";

  const qp = new URLSearchParams();
  qp.set("page", String(page));
  qp.set("per_page", String(perPage));
  if (q) qp.set("q", q);
  qp.set("status", status);
  if (supplierId) qp.set("supplier_id", supplierId);
  if (sourceCategory) qp.set("source_category", sourceCategory);

  const data = await apiGet<PageResponse<LiveItem>>(`/vaults/live?${qp.toString()}`);

  const baseParams = {
    per_page: perPage,
    q,
    status,
    supplier_id: supplierId,
    source_category: sourceCategory,
  };
  const prevHref = `/vaults/live?${buildQueryString(baseParams, { page: Math.max(1, page - 1) })}`;
  const nextHref = `/vaults/live?${buildQueryString(baseParams, { page: page + 1 })}`;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Vault 3 · Listings</h1>
          <p className="mt-1 text-sm text-slate-600">Click to inspect trust, profitability, payload drift, lifecycle.</p>
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
                placeholder="title or TM id"
              />
            </label>
            <label className="text-xs text-slate-600">
              <span className="mr-1">Status</span>
              <select
                name="status"
                defaultValue={status}
                className="w-32 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
              >
                <option value="Live">Live</option>
                <option value="DRY_RUN">DRY_RUN</option>
                <option value="Withdrawn">Withdrawn</option>
                <option value="All">All</option>
              </select>
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
            <button type="submit" className="rounded-md bg-slate-900 px-3 py-1 text-xs font-medium text-white">
              Apply
            </button>
            <Link className="text-xs text-slate-600 underline" href="/vaults/live?status=Live">
              Reset
            </Link>
          </form>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">ID</th>
                <th className="px-4 py-3">Img</th>
                <th className="px-4 py-3">TM ID</th>
                <th className="px-4 py-3">Title</th>
                <th className="px-4 py-3">State</th>
                <th className="px-4 py-3">Lifecycle</th>
                <th className="px-4 py-3">Price</th>
                <th className="px-4 py-3">Views</th>
                <th className="px-4 py-3">Watch</th>
                <th className="px-4 py-3">Synced</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((it) => (
                <tr key={it.id} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <Link className="underline" href={`/vaults/live/${it.id}`}>
                      {it.id}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    {it.thumb ? (
                      <Link href={`/vaults/live/${it.id}`} className="block w-12">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          alt=""
                          src={imgSrc(it.thumb)}
                          className="h-10 w-12 rounded-md border border-slate-200 object-cover"
                        />
                      </Link>
                    ) : (
                      <div className="h-10 w-12 rounded-md border border-dashed border-slate-200 bg-slate-50" />
                    )}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">{it.tm_listing_id || "-"}</td>
                  <td className="px-4 py-3">
                    <Link className="text-slate-900 hover:underline" href={`/vaults/live/${it.id}`}>
                      {it.title || "-"}
                    </Link>
                  </td>
                  <td className="px-4 py-3">{it.actual_state || "-"}</td>
                  <td className="px-4 py-3">{it.lifecycle_state || "-"}</td>
                  <td className="px-4 py-3">{it.actual_price == null ? "-" : `$${it.actual_price.toFixed(2)}`}</td>
                  <td className="px-4 py-3">{it.view_count ?? 0}</td>
                  <td className="px-4 py-3">{it.watch_count ?? 0}</td>
                  <td className="px-4 py-3">{it.last_synced_at || "-"}</td>
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

