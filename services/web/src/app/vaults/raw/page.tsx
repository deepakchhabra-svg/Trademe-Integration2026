type PageResponse<T> = { items: T[]; total: number };

type RawItem = {
  id: number;
  supplier_id: number | null;
  external_sku: string;
  title: string | null;
  cost_price: number | null;
  stock_level: number | null;
  sync_status: string | null;
  product_url: string | null;
  images: string[];
  last_scraped_at: string | null;
};

async function getRaw(): Promise<PageResponse<RawItem>> {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  const res = await fetch(`${base}/vaults/raw?page=1&per_page=50`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed: ${res.status}`);
  return (await res.json()) as PageResponse<RawItem>;
}

export default async function RawVault() {
  const data = await getRaw();

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">Vault 1 (Raw)</h1>
            <p className="mt-1 text-sm text-slate-600">Supplier products</p>
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
                  <th className="px-4 py-3">ID</th>
                  <th className="px-4 py-3">SKU</th>
                  <th className="px-4 py-3">Title</th>
                  <th className="px-4 py-3">Cost</th>
                  <th className="px-4 py-3">Sync</th>
                  <th className="px-4 py-3">Scraped</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((it) => (
                  <tr key={it.id} className="border-t border-slate-100">
                    <td className="px-4 py-3">{it.id}</td>
                    <td className="px-4 py-3 font-mono text-xs">{it.external_sku}</td>
                    <td className="px-4 py-3">{it.title || "-"}</td>
                    <td className="px-4 py-3">{it.cost_price == null ? "-" : `$${it.cost_price.toFixed(2)}`}</td>
                    <td className="px-4 py-3">{it.sync_status || "-"}</td>
                    <td className="px-4 py-3">{it.last_scraped_at || "-"}</td>
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

