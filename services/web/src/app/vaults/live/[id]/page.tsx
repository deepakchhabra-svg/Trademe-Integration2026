import Link from "next/link";
import { apiGet } from "../../../_components/api";
import { PageHeader } from "../../../../components/ui/PageHeader";
import { SectionCard } from "../../../../components/ui/SectionCard";
import { StatusBadge } from "../../../../components/ui/StatusBadge";
import { buttonClass } from "../../../_components/ui";
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

function Field({ label, value, testId }: { label: string; value: React.ReactNode; testId?: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3" data-testid={testId}>
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-sm text-slate-900">{value}</div>
    </div>
  );
}

export default async function ListingDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ tab?: string }>;
}) {
  const { id } = await params;
  const spTab = await searchParams;
  const l = await apiGet<ListingDetail>(`/listings/${encodeURIComponent(id)}`);
  const tab = (spTab.tab || "overview").toLowerCase();

  const breadcrumbs = (
    <div className="flex items-center gap-2 text-sm">
      <Link className="text-slate-600 hover:text-slate-900 underline" href="/vaults/live" data-testid="lnk-breadcrumb-vault3">
        Vault 3
      </Link>
      <span className="text-slate-400">/</span>
      <span className="font-medium text-slate-900">Listing #{l.id}</span>
    </div>
  );

  const headerActions = (
    <div className="flex items-center gap-2">
      <StatusBadge status={l.actual_state || "UNKNOWN"} />
      {l.trust_report ? (
        <StatusBadge status={l.trust_report.is_trusted ? "SUCCESS" : "FAILED"} label={`Trust: ${l.trust_report.score}`} />
      ) : null}
    </div>
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title={l.tm_listing_id ? `TradeMe Listing ${l.tm_listing_id}` : "Unpublished Vault Listing"}
        subtitle={
          <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-4">
            <div className="flex items-center gap-2">
              <span className="text-slate-500">Internal:</span>
              {l.internal_product ? (
                <Link className="underline hover:text-slate-900 font-medium" href={`/vaults/enriched/${l.internal_product.id}`} data-testid="lnk-internal-ref">
                  {l.internal_product.sku}
                </Link>
              ) : (
                "-"
              )}
            </div>
            <div className="hidden sm:block text-slate-300">|</div>
            <div className="flex items-center gap-2">
              <span className="text-slate-500">Supplier SKUs:</span>
              {l.supplier_product ? (
                <Link className="underline hover:text-slate-900 font-medium font-mono text-xs" href={`/vaults/raw/${l.supplier_product.id}`} data-testid="lnk-supplier-ref">
                  {l.supplier_product.external_sku}
                </Link>
              ) : (
                "-"
              )}
            </div>
          </div>
        }
        actions={headerActions}
        breadcrumbs={breadcrumbs}
      />

      <div className="rounded-xl border border-slate-200 bg-white p-3">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">You are viewing</div>
        <div className="mt-1 text-sm font-semibold text-slate-900">Vault 3 · Listing</div>
        <div className="mt-1 text-xs text-slate-600">
          State: <span className="font-mono">{l.actual_state || "-"}</span>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {[
          ["overview", "Overview"],
          ["preview", "Listing preview"],
          ["payload", "Payload"],
          ["audit", "Audit"],
        ].map(([k, label]) => (
          <Link
            key={k}
            href={`/vaults/live/${encodeURIComponent(String(l.id))}?tab=${encodeURIComponent(k)}`}
            className={buttonClass({ variant: k === tab ? "primary" : "outline" })}
          >
            {label}
          </Link>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Field label="Current Price" value={l.actual_price == null ? "-" : `$${l.actual_price.toFixed(2)}`} testId="field-price" />
        <Field label="Views" value={l.view_count ?? 0} testId="field-views" />
        <Field label="Watchers" value={l.watch_count ?? 0} testId="field-watchers" />
        <Field label="Last Synced" value={l.last_synced_at || "-"} testId="field-last-synced" />
      </div>

      {tab === "overview" ? (
        <>
          {l.trust_report && !l.trust_report.is_trusted ? (
            <SectionCard title="Trust blockers" className="border-amber-200 bg-amber-50">
              <ul className="list-disc pl-5 text-sm text-amber-950" data-testid="trust-blocker-list">
                {l.trust_report.blockers.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
            </SectionCard>
          ) : null}

          <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
            <SectionCard title="Profitability">
              <pre className="max-h-[420px] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-900 font-mono" data-testid="profitability-preview">
                {JSON.stringify(l.profitability_preview || {}, null, 2)}
              </pre>
            </SectionCard>
            <SectionCard title="Lifecycle recommendation">
              <pre className="max-h-[420px] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-900 font-mono" data-testid="lifecycle-recommendation">
                {JSON.stringify(l.lifecycle_recommendation || {}, null, 2)}
              </pre>
            </SectionCard>
          </div>

          <SectionCard title="Actions" className="bg-slate-50/50">
            <ListingActions listingDbId={l.id} tmListingId={l.tm_listing_id} internalProductId={l.internal_product_id} />
          </SectionCard>
        </>
      ) : null}

      {tab === "preview" ? (
        <SectionCard title="Listing preview">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Title</div>
            <div className="mt-1 text-base font-semibold text-slate-900">{l.internal_product?.title || "-"}</div>
            <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
              <Field label="Trade Me ID" value={l.tm_listing_id || "-"} />
              <Field label="Price" value={l.actual_price == null ? "-" : `$${l.actual_price.toFixed(2)}`} />
              <Field label="Category" value={l.category_id || "-"} />
            </div>
          </div>
        </SectionCard>
      ) : null}

      {tab === "payload" ? (
        <SectionCard title="Payload snapshot" subtitle={`Hash: ${l.payload_hash || "-"}`}>
          <pre className="max-h-[520px] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-900 font-mono" data-testid="payload-snapshot">
            {l.payload_snapshot || "-"}
          </pre>
        </SectionCard>
      ) : null}

      {tab === "audit" ? (
        <SectionCard title="Audit">
          <div className="text-sm text-slate-600">
            For full audit history, use the <Link className="underline" href="/ops/audits">Audit log</Link>.
          </div>
        </SectionCard>
      ) : null}
    </div>
  );
}
