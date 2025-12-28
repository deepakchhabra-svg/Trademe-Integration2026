import Link from "next/link";

import { apiGet } from "../../../_components/api";
import { PageHeader } from "../../../../components/ui/PageHeader";
import { SectionCard } from "../../../../components/ui/SectionCard";
import { StatusBadge } from "../../../../components/ui/StatusBadge";

type SupplierProduct = {
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
  last_scraped_at: string | null;
  snapshot_hash: string | null;
};

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

export default async function RawDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const sp = await apiGet<SupplierProduct>(`/supplier-products/${encodeURIComponent(id)}`);

  const breadcrumbs = (
    <div className="flex items-center gap-2 text-sm">
      <Link className="text-slate-600 hover:text-slate-900 underline" href="/vaults/raw" data-testid="lnk-breadcrumb-vault1">
        Vault 1
      </Link>
      <span className="text-slate-400">/</span>
      <span className="font-medium text-slate-900">SupplierProduct #{sp.id}</span>
    </div>
  );

  const headerActions = (
    <div className="flex items-center gap-2">
      <StatusBadge status={sp.sync_status || "UNKNOWN"} data-testid="badge-sync-status" />
      <StatusBadge status={sp.enrichment_status || "UNKNOWN"} data-testid="badge-enrichment-status" />
    </div>
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title={sp.title || "(no title)"}
        subtitle={
          <div className="flex items-center gap-2">
            <span>Supplier: {sp.supplier_name || sp.supplier_id || "-"}</span>
            <span className="text-slate-300">|</span>
            <span>SKU: <span className="font-mono text-xs">{sp.external_sku}</span></span>
          </div>
        }
        actions={headerActions}
        breadcrumbs={breadcrumbs}
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Field label="Cost price" value={sp.cost_price == null ? "-" : `$${sp.cost_price.toFixed(2)}`} testId="field-cost" />
        <Field label="Stock level" value={sp.stock_level ?? "-"} testId="field-stock" />
        <Field label="Source category" value={<span className="font-mono text-xs">{sp.source_category || "-"}</span>} testId="field-category" />
        <Field label="Last scraped" value={sp.last_scraped_at || "-"} testId="field-last-scraped" />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <SectionCard
          title="Raw Description"
          actions={sp.product_url ? (
            <a className="text-xs text-slate-600 underline hover:text-slate-900" href={sp.product_url} target="_blank" rel="noreferrer" data-testid="lnk-supplier-page">
              Open supplier page
            </a>
          ) : null}
        >
          <pre className="max-h-[420px] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-900 font-sans" data-testid="raw-description">
            {sp.description || "-"}
          </pre>
        </SectionCard>

        <SectionCard
          title="Enriched Copy"
          subtitle={sp.enriched_title ? "Generated title + description" : "Description only"}
        >
          {sp.enrichment_error ? (
            <div className="mb-3 rounded-lg border border-red-100 bg-red-50 p-3 text-xs text-red-800" data-testid="enrichment-error">
              {sp.enrichment_error}
            </div>
          ) : null}
          <pre className="max-h-[420px] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-900 font-sans" data-testid="enriched-description">
            {sp.enriched_description || "-"}
          </pre>
        </SectionCard>
      </div>

      <SectionCard title="Product Images">
        {sp.images?.length ? (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
            {sp.images.map((src, idx) => (
              <a key={idx} href={imgSrc(src)} target="_blank" rel="noreferrer" className="group">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  alt={`image-${idx + 1}`}
                  src={imgSrc(src)}
                  className="h-32 w-full rounded-lg border border-slate-200 object-cover transition-opacity group-hover:opacity-80"
                  data-testid={`product-img-${idx}`}
                />
              </a>
            ))}
          </div>
        ) : (
          <div className="text-sm text-slate-500" data-testid="no-images">No images available for this product.</div>
        )}
      </SectionCard>

      <SectionCard title="Technical Specifications" subtitle={`Snapshot: ${sp.snapshot_hash || "-"}`}>
        <pre className="max-h-[420px] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-900 font-mono" data-testid="tech-specs">
          {JSON.stringify(sp.specs || {}, null, 2)}
        </pre>
      </SectionCard>
    </div>
  );
}
