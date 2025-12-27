import Link from "next/link";

import { apiGet } from "../../../_components/api";
import { Badge } from "../../../_components/Badge";
import { EnrichedActions } from "./Actions";

type InternalProductDetail = {
  id: number;
  sku: string;
  title: string | null;
  supplier_product: {
    id: number;
    supplier_id: number | null;
    supplier_name: string | null;
    external_sku: string;
    title: string | null;
    description: string | null;
    cost_price: number | null;
    stock_level: number | null;
    product_url: string | null;
    images: string[];
    specs: Record<string, unknown>;
    sync_status: string | null;
    source_category: string | null;
    enrichment_status: string | null;
    enrichment_error: string | null;
    enriched_title: string | null;
    enriched_description: string | null;
  } | null;
};

type TrustReport = {
  internal_product_id: number;
  score: number;
  is_trusted: boolean;
  blockers: string[];
  breakdown: Record<string, string>;
};

type ValidationResult = { internal_product_id: number; ok: boolean; reason: string | null };

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-sm text-slate-900">{value}</div>
    </div>
  );
}

export default async function EnrichedDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  const [ip, trust, validation] = await Promise.all([
    apiGet<InternalProductDetail>(`/internal-products/${encodeURIComponent(id)}`),
    apiGet<TrustReport>(`/trust/internal-products/${encodeURIComponent(id)}`),
    apiGet<ValidationResult>(`/validate/internal-products/${encodeURIComponent(id)}`),
  ]);

  const sp = ip.supplier_product;

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Link className="text-sm text-slate-600 underline" href="/vaults/enriched">
              Vault 2
            </Link>
            <span className="text-sm text-slate-400">/</span>
            <span className="text-sm font-medium text-slate-900">{ip.sku}</span>
          </div>
          <h1 className="mt-2 text-lg font-semibold tracking-tight">{ip.title || sp?.title || "(no title)"}</h1>
          <p className="mt-1 text-sm text-slate-600">
            Supplier product:{" "}
            {sp ? (
              <Link className="underline" href={`/vaults/raw/${sp.id}`}>
                #{sp.id}
              </Link>
            ) : (
              "-"
            )}
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <Badge tone={trust.is_trusted ? "emerald" : "amber"}>trust {trust.score}</Badge>
          <Badge tone={validation.ok ? "emerald" : "red"}>{validation.ok ? "passes gates" : "blocked"}</Badge>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        <Field label="Internal ID" value={ip.id} />
        <Field label="Supplier" value={sp?.supplier_name || sp?.supplier_id || "-"} />
        <Field label="Cost" value={sp?.cost_price == null ? "-" : `$${sp.cost_price.toFixed(2)}`} />
        <Field label="Category" value={<span className="font-mono text-xs">{sp?.source_category || "-"}</span>} />
      </div>

      {!validation.ok && validation.reason ? (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-900">
          <div className="font-semibold">Gate failure</div>
          <pre className="mt-2 whitespace-pre-wrap font-mono text-xs">{validation.reason}</pre>
        </div>
      ) : null}

      {!trust.is_trusted && trust.blockers?.length ? (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
          <div className="font-semibold">Trust blockers</div>
          <ul className="mt-2 list-disc pl-5">
            {trust.blockers.map((b) => (
              <li key={b}>{b}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-sm font-semibold">Enriched description</div>
          <pre className="mt-3 max-h-[520px] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-900">
            {sp?.enriched_description || "-"}
          </pre>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-sm font-semibold">Trust breakdown</div>
          <pre className="mt-3 max-h-[520px] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-900">
            {JSON.stringify(trust.breakdown || {}, null, 2)}
          </pre>
        </div>
      </div>

      <EnrichedActions
        internalProductId={ip.id}
        supplierProductId={sp?.id ?? null}
      />
    </div>
  );
}

