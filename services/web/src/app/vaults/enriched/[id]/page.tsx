import Link from "next/link";
import { apiGet } from "../../../_components/api";
import { PageHeader } from "../../../../components/ui/PageHeader";
import { SectionCard } from "../../../../components/ui/SectionCard";
import { StatusBadge } from "../../../../components/ui/StatusBadge";
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

function Field({ label, value, testId }: { label: string; value: React.ReactNode; testId?: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3" data-testid={testId}>
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-sm text-slate-900">{value}</div>
    </div>
  );
}

function imgSrc(raw: string): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
  if (raw.startsWith("/media/")) return `${base}${raw}`;
  return raw;
}

export default async function EnrichedDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  const [ip, trust, validation] = await Promise.all([
    apiGet<InternalProductDetail>(`/internal-products/${encodeURIComponent(id)}`),
    apiGet<TrustReport>(`/trust/internal-products/${encodeURIComponent(id)}`),
    apiGet<ValidationResult>(`/validate/internal-products/${encodeURIComponent(id)}`),
  ]);

  const sp = ip.supplier_product;

  const breadcrumbs = (
    <div className="flex items-center gap-2 text-sm">
      <Link className="text-slate-600 hover:text-slate-900 underline" href="/vaults/enriched" data-testid="lnk-breadcrumb-vault2">
        Vault 2
      </Link>
      <span className="text-slate-400">/</span>
      <span className="font-medium text-slate-900">{ip.sku}</span>
    </div>
  );

  const headerActions = (
    <div className="flex items-center gap-2">
      <StatusBadge status={trust.is_trusted ? "SUCCESS" : "FAILED"} label={`Trust: ${trust.score}`} />
      <StatusBadge status={validation.ok ? "SUCCESS" : "FAILED"} label={validation.ok ? "Gates Passed" : "Gates Blocked"} />
    </div>
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title={ip.title || sp?.title || "(no title)"}
        subtitle={
          <div className="flex items-center gap-2">
            <span>SKU: <span className="font-mono text-xs">{ip.sku}</span></span>
            <span className="text-slate-300">|</span>
            <span>
              Supplier product:{" "}
              {sp ? (
                <Link className="underline hover:text-slate-900" href={`/vaults/raw/${sp.id}`} data-testid={`lnk-raw-ref-${sp.id}`}>
                  #{sp.id}
                </Link>
              ) : (
                "-"
              )}
            </span>
          </div>
        }
        actions={headerActions}
        breadcrumbs={breadcrumbs}
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Field label="Internal ID" value={ip.id} testId="field-internal-id" />
        <Field label="Supplier" value={sp?.supplier_name || sp?.supplier_id || "-"} testId="field-supplier" />
        <Field label="Cost" value={sp?.cost_price == null ? "-" : `$${sp.cost_price.toFixed(2)}`} testId="field-cost" />
        <Field label="Category" value={<span className="font-mono text-xs">{sp?.source_category || "-"}</span>} testId="field-category" />
      </div>

      {!validation.ok && validation.reason ? (
        <SectionCard title="Gate Failure" className="border-red-200 bg-red-50">
          <pre className="whitespace-pre-wrap font-mono text-xs text-red-900" data-testid="gate-failure-reason">{validation.reason}</pre>
        </SectionCard>
      ) : null}

      {!trust.is_trusted && trust.blockers?.length ? (
        <SectionCard title="Trust Blockers" className="border-amber-200 bg-amber-50">
          <ul className="list-disc pl-5 text-sm text-amber-950" data-testid="trust-blockers-list">
            {trust.blockers.map((b) => (
              <li key={b}>{b}</li>
            ))}
          </ul>
        </SectionCard>
      ) : null}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <SectionCard title="Enriched Description">
          <pre className="max-h-[520px] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-900 font-sans" data-testid="enriched-description">
            {sp?.enriched_description || "-"}
          </pre>
        </SectionCard>
        <SectionCard title="Trust Breakdown">
          <pre className="max-h-[520px] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-900 font-mono" data-testid="trust-breakdown">
            {JSON.stringify(trust.breakdown || {}, null, 2)}
          </pre>
        </SectionCard>
      </div>

      {sp?.images?.length ? (
        <SectionCard title="Product Images">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
            {sp.images.map((src, idx) => (
              <a key={idx} href={imgSrc(src)} target="_blank" rel="noreferrer" className="group">
                <img
                  alt={`image-${idx + 1}`}
                  src={imgSrc(src)}
                  className="h-32 w-full rounded-lg border border-slate-200 object-cover transition-opacity group-hover:opacity-80"
                  data-testid={`product-img-${idx}`}
                />
              </a>
            ))}
          </div>
        </SectionCard>
      ) : null}

      <SectionCard title="Operator Actions" className="bg-slate-50/50">
        <EnrichedActions
          internalProductId={ip.id}
          supplierProductId={sp?.id ?? null}
        />
      </SectionCard>
    </div>
  );
}
