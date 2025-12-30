import Link from "next/link";

import { apiGet } from "../../_components/api";
import { PageHeader } from "../../../components/ui/PageHeader";
import { SectionCard } from "../../../components/ui/SectionCard";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import { formatNZT } from "../../_components/time";
import { buttonClass } from "../../_components/ui";

type RemovedRow = {
  supplier_product_id: number;
  supplier_id: number | null;
  external_sku: string;
  title: string | null;
  product_url: string | null;
  source_category: string | null;
  removed_at: string | null;
  internal_product_id: number | null;
  listing: { id: number; tm_listing_id: string | null; actual_state: string | null; last_synced_at: string | null } | null;
  withdraw_command:
    | { id: string; status: string; updated_at: string | null; error_code: string | null; error_message: string | null }
    | null;
};

type Resp = { utc: string; total: number; items: RemovedRow[]; page: number; per_page: number };

export default async function RemovedItemsPage({ searchParams }: { searchParams: Promise<{ supplier_id?: string }> }) {
  const sp = await searchParams;
  const supplierId = sp.supplier_id || "";
  const qp = new URLSearchParams();
  if (supplierId) qp.set("supplier_id", supplierId);
  qp.set("page", "1");
  qp.set("per_page", "50");

  const data = await apiGet<Resp>(`/ops/removed_items?${qp.toString()}`);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Removed items"
        subtitle="Confirmed removed from supplier (2 misses). Shows linked listings and withdraw status."
        actions={
          <div className="flex items-center gap-2">
            <Link className={buttonClass({ variant: "outline" })} href="/vaults/raw?sync_status=REMOVED">
              View in Vault 1
            </Link>
            <Link className={buttonClass({ variant: "link" })} href="/ops/commands?type=WITHDRAW_LISTING&status=NOT_SUCCEEDED">
              Withdraw queue →
            </Link>
          </div>
        }
      />

      <SectionCard title="Filters">
        <form method="get" className="flex flex-wrap items-end gap-3">
          <label className="text-xs text-slate-600">
            <div className="mb-1 font-semibold uppercase tracking-wide">Supplier ID</div>
            <input className="w-28 rounded-md border border-slate-200 bg-white px-2 py-2 text-sm text-slate-900" name="supplier_id" defaultValue={supplierId} placeholder="e.g. 1" />
          </label>
          <button type="submit" className={buttonClass({ variant: "primary" })}>
            Apply
          </button>
          <Link className={buttonClass({ variant: "outline" })} href="/ops/removed">
            Reset
          </Link>
        </form>
      </SectionCard>

      <SectionCard title={`Showing ${data.items.length} of ${data.total}`} subtitle={`Last checked: ${formatNZT(data.utc)}`}>
        <div className="overflow-auto">
          <table className="w-full min-w-[980px] border-collapse text-sm">
            <thead className="text-left text-xs text-slate-500">
              <tr>
                <th className="border-b border-slate-200 p-2">Raw ID</th>
                <th className="border-b border-slate-200 p-2">SKU</th>
                <th className="border-b border-slate-200 p-2">Title</th>
                <th className="border-b border-slate-200 p-2">Removed at</th>
                <th className="border-b border-slate-200 p-2">Listing</th>
                <th className="border-b border-slate-200 p-2">Withdraw</th>
              </tr>
            </thead>
            <tbody>
              {data.items.length ? (
                data.items.map((r) => (
                  <tr key={r.supplier_product_id} className="hover:bg-slate-50">
                    <td className="border-b border-slate-100 p-2">
                      <Link className="underline" href={`/vaults/raw/${r.supplier_product_id}`}>
                        {r.supplier_product_id}
                      </Link>
                    </td>
                    <td className="border-b border-slate-100 p-2 font-mono text-xs">{r.external_sku}</td>
                    <td className="border-b border-slate-100 p-2">
                      <div className="max-w-[520px] truncate">{r.title || "-"}</div>
                      {r.product_url ? (
                        <a className="text-[11px] text-indigo-700 hover:underline" href={r.product_url} target="_blank" rel="noreferrer">
                          supplier page →
                        </a>
                      ) : null}
                    </td>
                    <td className="border-b border-slate-100 p-2">{formatNZT(r.removed_at)}</td>
                    <td className="border-b border-slate-100 p-2">
                      {r.listing ? (
                        <div className="space-y-1">
                          <StatusBadge status={r.listing.actual_state || "UNKNOWN"} />
                          {r.listing.id ? (
                            <Link className="block text-[11px] text-indigo-700 hover:underline" href={`/vaults/live/${r.listing.id}`}>
                              Vault 3 #{r.listing.id}
                            </Link>
                          ) : null}
                          <div className="text-[11px] text-slate-500">TM: {r.listing.tm_listing_id || "-"}</div>
                        </div>
                      ) : (
                        <div className="text-[11px] text-slate-500">No linked listing</div>
                      )}
                    </td>
                    <td className="border-b border-slate-100 p-2">
                      {r.withdraw_command ? (
                        <div className="space-y-1">
                          <StatusBadge status={r.withdraw_command.status} />
                          <Link className="block text-[11px] text-indigo-700 hover:underline" href={`/ops/commands/${r.withdraw_command.id}`}>
                            cmd {r.withdraw_command.id.slice(0, 8)}…
                          </Link>
                          {r.withdraw_command.error_code || r.withdraw_command.error_message ? (
                            <div className="text-[11px] text-slate-500">
                              {(r.withdraw_command.error_code || "").trim()}
                              {r.withdraw_command.error_message ? ` — ${r.withdraw_command.error_message}` : ""}
                            </div>
                          ) : null}
                        </div>
                      ) : r.listing?.tm_listing_id ? (
                        <div className="text-[11px] text-slate-500">No withdraw command found</div>
                      ) : (
                        <div className="text-[11px] text-slate-500">—</div>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td className="p-4 text-slate-500" colSpan={6}>
                    No removed items found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </SectionCard>
    </div>
  );
}

