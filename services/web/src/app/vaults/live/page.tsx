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
  last_synced_at: string | null;
};

async function getLive(): Promise<PageResponse<LiveItem>> {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  const res = await fetch(`${base}/vaults/live?page=1&per_page=50`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed: ${res.status}`);
  return (await res.json()) as PageResponse<LiveItem>;
}

export default async function LiveVault() {
  const data = await getLive();

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">Vault 3 (Live)</h1>
            <p className="mt-1 text-sm text-slate-600">Trade Me listings</p>
          </div>
          <a className="text-sm text-slate-700 underline" href="/">
            Home
          </a>
        </div>

        <div className="mt-6 rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-200 p-4">
            <div className="text-sm text-slate-700">
              Showing {data.items.length} of {data.total}
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3">TM ID</th>
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
                  <tr key={it.id} className="border-t border-slate-100">
                    <td className="px-4 py-3 font-mono text-xs">{it.tm_listing_id || "-"}</td>
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
        </div>
      </div>
    </div>
  );
}

