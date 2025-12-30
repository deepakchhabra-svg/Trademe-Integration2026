import Link from "next/link";

import { apiGet } from "../../../_components/api";
import { PageHeader } from "../../../../components/ui/PageHeader";
import { SectionCard } from "../../../../components/ui/SectionCard";
import { StatusBadge } from "../../../../components/ui/StatusBadge";
import { buttonClass } from "../../../_components/ui";

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
  internal_product_id: number | null;
};

type DraftPayload = { internal_product_id: number; payload: Record<string, unknown>; payload_hash: string };

function Field({ label, value, testId }: { label: string; value: React.ReactNode; testId?: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3" data-testid={testId}>
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-sm text-slate-900">{value}</div>
    </div>
  );
}

function imgSrc(raw: string): string {
  if (raw.startsWith("/media/")) return raw.replace(/^\/media\//, "/api/media/");
  return raw;
}

function formatNZT(iso: string | null): string {
  if (!iso) return "unknown";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  const s = new Intl.DateTimeFormat("en-NZ", {
    timeZone: "Pacific/Auckland",
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(d);
  return `${s} NZT`;
}

export default async function RawDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ tab?: string }>;
}) {
  const { id } = await params;
  const spTab = await searchParams;
  const sp = await apiGet<SupplierProduct>(`/supplier-products/${encodeURIComponent(id)}`);
  const tab = (spTab.tab || "raw").toLowerCase();
  const draft: DraftPayload | null =
    tab === "listing" && sp.internal_product_id
      ? await apiGet<DraftPayload>(`/draft/internal-products/${encodeURIComponent(String(sp.internal_product_id))}/trademe`)
      : null;
  // tab selection via querystring keeps URLs shareable without client state
  // (e.g. /vaults/raw/123?tab=listing)

  const tabs: Array<{ key: string; label: string }> = [
    { key: "raw", label: "Supplier data" },
    { key: "enriched", label: "Enriched copy" },
    { key: "listing", label: "Listing preview" },
    { key: "images", label: "Images" },
    { key: "history", label: "History" },
  ];

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

      <div className="rounded-xl border border-slate-200 bg-white p-3">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">You are viewing</div>
        <div className="mt-1 text-sm font-semibold text-slate-900">Vault 1 · Supplier data</div>
        {String(sp.sync_status || "").toUpperCase() === "REMOVED" ? (
          <div className="mt-2 text-sm text-slate-800" data-testid="removed-explainer">
            <StatusBadge status="REMOVED" />{" "}
            <span className="ml-1">
              Removed from supplier (last seen: <span className="font-mono text-xs">{formatNZT(sp.last_scraped_at)}</span>). Hidden by default and blocked from listing.
            </span>
          </div>
        ) : null}
        {sp.internal_product_id ? (
          <div className="mt-1 text-xs text-slate-600">
            Linked enriched product:{" "}
            <Link className="underline" href={`/vaults/enriched/${sp.internal_product_id}`}>
              Internal #{sp.internal_product_id}
            </Link>
          </div>
        ) : (
          <div className="mt-1 text-xs text-slate-600">No enriched product linked yet.</div>
        )}
      </div>

      <div className="flex flex-wrap gap-2">
        {tabs.map((t) => (
          <Link
            key={t.key}
            href={`/vaults/raw/${sp.id}?tab=${encodeURIComponent(t.key)}`}
            className={buttonClass({ variant: t.key === tab ? "primary" : "outline" })}
          >
            {t.label}
          </Link>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Field label="Cost price" value={sp.cost_price == null ? "-" : `$${sp.cost_price.toFixed(2)}`} testId="field-cost" />
        <Field label="Stock level" value={sp.stock_level ?? "-"} testId="field-stock" />
        <Field label="Source category" value={<span className="font-mono text-xs">{sp.source_category || "-"}</span>} testId="field-category" />
        <Field label="Last scraped" value={sp.last_scraped_at || "-"} testId="field-last-scraped" />
      </div>

      {tab === "raw" ? (
        <SectionCard
          title="Supplier description"
          actions={sp.product_url ? (
            <a className={buttonClass({ variant: "link" })} href={sp.product_url} target="_blank" rel="noreferrer" data-testid="lnk-supplier-page">
              Open supplier page
            </a>
          ) : null}
        >
          <pre className="max-h-[520px] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-900 font-sans" data-testid="raw-description">
            {sp.description || "-"}
          </pre>
        </SectionCard>
      ) : null}

      {tab === "enriched" ? (
        <SectionCard title="Enriched copy" subtitle={sp.enriched_title ? "Generated title + description" : undefined}>
          {sp.enrichment_error ? (
            <div className="mb-3 rounded-lg border border-red-100 bg-red-50 p-3 text-xs text-red-800" data-testid="enrichment-error">
              {sp.enrichment_error}
            </div>
          ) : null}
          <pre className="max-h-[520px] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-900 font-sans" data-testid="enriched-description">
            {sp.enriched_description || "-"}
          </pre>
        </SectionCard>
      ) : null}

      {tab === "listing" ? (
        sp.internal_product_id ? (
          <SectionCard title="Listing preview (Draft payload)">
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Title</div>
              <div className="mt-1 text-base font-semibold text-slate-900">{String(draft?.payload?.Title || "-")}</div>

              <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
                <Field label="Category" value={String(draft?.payload?.Category || "-")} />
                <Field label="Start price" value={draft?.payload?.StartPrice != null ? `$${Number(draft.payload.StartPrice).toFixed(2)}` : "-"} />
                <Field label="Duration" value={draft?.payload?.Duration != null ? `${draft.payload.Duration} days` : "-"} />
              </div>

              <div className="mt-4 text-xs font-semibold uppercase tracking-wide text-slate-500">Description</div>
              <div className="mt-2 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-900 whitespace-pre-wrap">
                {Array.isArray(draft?.payload?.Description) ? String(draft?.payload?.Description?.[0] || "-") : String(draft?.payload?.Description || "-")}
              </div>

              <div className="mt-3 text-[11px] text-slate-500">
                Payload hash: <span className="font-mono">{draft?.payload_hash?.slice(0, 16) || "-"}</span>…
              </div>
            </div>
          </SectionCard>
        ) : (
          <SectionCard title="Listing preview">
            <div className="text-sm text-slate-600">Create/enrich an internal product first (Vault 2) to generate a Trade Me draft payload.</div>
          </SectionCard>
        )
      ) : null}

      {tab === "images" ? (
        <SectionCard title="Images">
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
      ) : null}

      {tab === "history" ? (
        <SectionCard title="History">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-4">
            <Field label="Raw ID" value={sp.id} />
            <Field label="Source status" value={<StatusBadge status={sp.sync_status || "UNKNOWN"} />} />
            <Field label="Enrichment status" value={<StatusBadge status={sp.enrichment_status || "UNKNOWN"} />} />
            <Field label="Last scraped (UTC)" value={sp.last_scraped_at || "-"} />
          </div>
          <div className="mt-4">
            <SectionCard title="Technical specifications" subtitle={`Snapshot: ${sp.snapshot_hash || "-"}`}>
              <pre className="max-h-[520px] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-900 font-mono" data-testid="tech-specs">
                {JSON.stringify(sp.specs || {}, null, 2)}
              </pre>
            </SectionCard>
          </div>
        </SectionCard>
      ) : null}
    </div>
  );
}
