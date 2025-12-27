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
};

async function getEnriched(): Promise<PageResponse<EnrichedItem>> {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  const res = await fetch(`${base}/vaults/enriched?page=1&per_page=50`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed: ${res.status}`);
  return (await res.json()) as PageResponse<EnrichedItem>;
}

export default async function EnrichedVault() {
  const data = await getEnriched();

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">Vault 2 (Enriched)</h1>
            <p className="mt-1 text-sm text-slate-600">Internal products + enrichment</p>
          </div>
          {/* eslint-disable-next-line @next/next/no-html-link-for-pages */}
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
                  <th className="px-4 py-3">Enriched</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((it) => (
                  <tr key={it.id} className="border-t border-slate-100 align-top">
                    <td className="px-4 py-3">{it.id}</td>
                    <td className="px-4 py-3 font-mono text-xs">{it.sku}</td>
                    <td className="px-4 py-3">{it.title || "-"}</td>
                    <td className="px-4 py-3">{it.cost_price == null ? "-" : `$${it.cost_price.toFixed(2)}`}</td>
                    <td className="px-4 py-3">
                      {it.enriched_description ? (
                        <span className="rounded-full bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700">
                          yes
                        </span>
                      ) : (
                        <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700">
                          no
                        </span>
                      )}
                    </td>
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

