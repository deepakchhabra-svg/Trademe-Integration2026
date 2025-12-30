import { apiGet } from "../_components/api";
import { Badge } from "../_components/Badge";
import Link from "next/link";
import { buildQueryString } from "../_components/pagination";
import { buttonClass } from "../_components/ui";
import { PageHeader } from "../../components/ui/PageHeader";
import { FilterChips } from "../../components/ui/FilterChips";
import { formatNZT } from "../_components/time";

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
  searchParams: Promise<{ page?: string; per_page?: string; q?: string; fulfillment_status?: string; payment_status?: string; order_status?: string }>;
}) {
  const sp = await searchParams;
  const page = Math.max(1, Number(sp.page || "1"));
  const perPage = Math.min(200, Math.max(10, Number(sp.per_page || "50")));
  const q = sp.q || "";
  const fulfillmentStatus = sp.fulfillment_status || "";
  const paymentStatus = sp.payment_status || "";
  const orderStatus = sp.order_status || "";

  let data: PageResponse<OrderRow> | null = null;
  let error: string | null = null;

  try {
    const qs = buildQueryString(
      { page, per_page: perPage, q, fulfillment_status: fulfillmentStatus, payment_status: paymentStatus, order_status: orderStatus },
      {},
    );
    data = await apiGet<PageResponse<OrderRow>>(`/orders?${qs}`);
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to load orders";
  }

  const baseParams = {
    per_page: perPage,
    q,
    fulfillment_status: fulfillmentStatus,
    payment_status: paymentStatus,
    order_status: orderStatus,
  };
  const prevHref = `/orders?${buildQueryString(baseParams, { page: Math.max(1, page - 1) })}`;
  const nextHref = `/orders?${buildQueryString(baseParams, { page: page + 1 })}`;

  return (
    <div className="space-y-4">
      <PageHeader
        title="Orders"
        subtitle="Fulfillment-critical records. Filter to see what’s pending and what needs action."
        actions={
          <Badge tone="indigo">
            Page {page} · {perPage}/page
          </Badge>
        }
      />

      <FilterChips
        chips={[
          { label: "Fulfillment", value: fulfillmentStatus || null, href: "/orders" },
          { label: "Payment", value: paymentStatus || null, href: "/orders" },
          { label: "Order", value: orderStatus || null, href: "/orders" },
          { label: "Search", value: q || null, href: "/orders" },
        ]}
      />

      {error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</div>
      ) : null}

      {data ? (
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="flex flex-col gap-3 border-b border-slate-200 p-4 text-sm text-slate-700 sm:flex-row sm:items-center sm:justify-between">
            <div>
              Showing {data.items.length} of {data.total}
            </div>
            <form className="flex flex-wrap items-center gap-2" method="get">
              <input type="hidden" name="page" value="1" />
              <label className="text-xs text-slate-600">
                <span className="mr-1">Search</span>
                <input
                  name="q"
                  defaultValue={q}
                  className="w-44 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
                  placeholder="order ref / buyer"
                />
              </label>
              <label className="text-xs text-slate-600">
                <span className="mr-1">Fulfillment</span>
                <input
                  name="fulfillment_status"
                  defaultValue={fulfillmentStatus}
                  className="w-28 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
                  placeholder="PENDING"
                />
              </label>
              <label className="text-xs text-slate-600">
                <span className="mr-1">Payment</span>
                <input
                  name="payment_status"
                  defaultValue={paymentStatus}
                  className="w-24 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
                  placeholder="PAID"
                />
              </label>
              <label className="text-xs text-slate-600">
                <span className="mr-1">Order</span>
                <input
                  name="order_status"
                  defaultValue={orderStatus}
                  className="w-24 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
                  placeholder="CONFIRMED"
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
              <Link className={buttonClass({ variant: "link" })} href="/orders">
                Reset
              </Link>
            </form>
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
                    <td className="px-4 py-3">{formatNZT(o.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-between border-t border-slate-200 p-4 text-sm">
            <Link className={`text-slate-700 underline ${page <= 1 ? "pointer-events-none opacity-40" : ""}`} href={prevHref}>
              Prev
            </Link>
            <div className="text-xs text-slate-600">Page {page}</div>
            <Link className="text-slate-700 underline" href={nextHref}>
              Next
            </Link>
          </div>
        </div>
      ) : null}
    </div>
  );
}

