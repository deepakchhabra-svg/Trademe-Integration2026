import { apiGet } from "../_components/api";
import { Badge } from "../_components/Badge";

type PageResponse<T> = { items: T[]; total: number };

type OrderRow = {
  id: number;
  tm_order_ref: string;
  buyer_name: string | null;
  sold_price: number | null;
  sold_date: string | null;
  order_status: string | null;
  payment_status: string | null;
  fulfillment_status: string | null;
  created_at: string | null;
};

export default async function OrdersPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; per_page?: string }>;
}) {
  const sp = await searchParams;
  const page = Math.max(1, Number(sp.page || "1"));
  const perPage = Math.min(200, Math.max(10, Number(sp.per_page || "50")));

  let data: PageResponse<OrderRow> | null = null;
  let error: string | null = null;

  try {
    data = await apiGet<PageResponse<OrderRow>>(`/orders?page=${page}&per_page=${perPage}`);
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to load orders";
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Orders</h1>
          <p className="mt-1 text-sm text-slate-600">
            Fulfillment-critical records. Keep everything visible and auditable.
          </p>
        </div>
        <Badge tone="blue">
          Page {page} · {perPage}/page
        </Badge>
      </div>

      {error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</div>
      ) : null}

      {data ? (
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-200 p-4 text-sm text-slate-700">
            <div>
              Showing {data.items.length} of {data.total}
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3">TM Ref</th>
                  <th className="px-4 py-3">Buyer</th>
                  <th className="px-4 py-3">Sold</th>
                  <th className="px-4 py-3">Order</th>
                  <th className="px-4 py-3">Payment</th>
                  <th className="px-4 py-3">Fulfillment</th>
                  <th className="px-4 py-3">Created</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((o) => (
                  <tr key={o.id} className="border-t border-slate-100">
                    <td className="px-4 py-3 font-mono text-xs">{o.tm_order_ref}</td>
                    <td className="px-4 py-3">{o.buyer_name || "-"}</td>
                    <td className="px-4 py-3">{o.sold_price == null ? "-" : `$${o.sold_price.toFixed(2)}`}</td>
                    <td className="px-4 py-3">{o.order_status || "-"}</td>
                    <td className="px-4 py-3">{o.payment_status || "-"}</td>
                    <td className="px-4 py-3">{o.fulfillment_status || "-"}</td>
                    <td className="px-4 py-3">{o.created_at || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </div>
  );
}

