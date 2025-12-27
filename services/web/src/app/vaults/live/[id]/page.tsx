import Link from "next/link";

import { apiGet } from "../../../_components/api";
import { Badge } from "../../../_components/Badge";
import { ListingActions } from "./Actions";

type ListingDetail = {
  id: number;
  tm_listing_id: string | null;
  internal_product_id: number | null;
  actual_state: string | null;
  desired_state: string | null;
  lifecycle_state: string | null;
  is_locked: boolean;
  desired_price: number | null;
  actual_price: number | null;
  view_count: number | null;
  watch_count: number | null;
  category_id: string | null;
  payload_snapshot: string | null;
  payload_hash: string | null;
  last_synced_at: string | null;
  profitability_preview?: Record<string, unknown>;
  lifecycle_recommendation?: Record<string, unknown>;
  trust_report?: { score: number; is_trusted: boolean; blockers: string[]; breakdown: Record<string, string> };
  supplier_product?: { id: number; external_sku: string; source_category: string | null; product_url: string | null } | null;
  internal_product?: { id: number; sku: string; title: string | null } | null;
};

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-sm text-slate-900">{value}</div>
    </div>
  );
}

export default async function ListingDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const l = await apiGet<ListingDetail>(`/listings/${encodeURIComponent(id)}`);

  const trustTone = l.trust_report?.is_trusted ? "emerald" : "amber";

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Link className="text-sm text-slate-600 underline" href="/vaults/live">
              Vault 3
            </Link>
            <span className="text-sm text-slate-400">/</span>
            <span className="text-sm font-medium text-slate-900">Listing #{l.id}</span>
          </div>
          <h1 className="mt-2 text-lg font-semibold tracking-tight">{l.tm_listing_id ? `TM ${l.tm_listing_id}` : "Unpublished listing"}</h1>
          <p className="mt-1 text-sm text-slate-600">
            Internal:{" "}
            {l.internal_product ? (
              <Link className="underline" href={`/vaults/enriched/${l.internal_product.id}`}>
                {l.internal_product.sku}
              </Link>
            ) : (
              "-"
            )}
            {" · "}
            Supplier product:{" "}
            {l.supplier_product ? (
              <Link className="underline" href={`/vaults/raw/${l.supplier_product.id}`}>
                #{l.supplier_product.id}
              </Link>
            ) : (
              "-"
            )}
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <Badge tone={l.actual_state === "Live" ? "emerald" : "slate"}>{l.actual_state || "unknown"}</Badge>
          {l.trust_report ? <Badge tone={trustTone}>trust {l.trust_report.score}</Badge> : null}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        <Field label="Price" value={l.actual_price == null ? "-" : `$${l.actual_price.toFixed(2)}`} />
        <Field label="Views" value={l.view_count ?? 0} />
        <Field label="Watchers" value={l.watch_count ?? 0} />
        <Field label="Synced" value={l.last_synced_at || "-"} />
      </div>

      {l.trust_report && !l.trust_report.is_trusted ? (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
          <div className="font-semibold">Trust blockers</div>
          <ul className="mt-2 list-disc pl-5">
            {l.trust_report.blockers.map((b) => (
              <li key={b}>{b}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-sm font-semibold">Profitability preview</div>
          <pre className="mt-3 max-h-[420px] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-900">
            {JSON.stringify(l.profitability_preview || {}, null, 2)}
          </pre>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-sm font-semibold">Lifecycle recommendation</div>
          <pre className="mt-3 max-h-[420px] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-900">
            {JSON.stringify(l.lifecycle_recommendation || {}, null, 2)}
          </pre>
        </div>
      </div>

      <ListingActions listingDbId={l.id} tmListingId={l.tm_listing_id} internalProductId={l.internal_product_id} />

      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="text-sm font-semibold">Payload snapshot</div>
          <div className="text-xs text-slate-500 font-mono">{l.payload_hash || "-"}</div>
        </div>
        <pre className="mt-3 max-h-[520px] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-900">
          {l.payload_snapshot || "-"}
        </pre>
      </div>
    </div>
  );
}

