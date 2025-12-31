import Link from "next/link";
import Image from "next/image";
import { apiGet } from "../../../_components/api";
import { PageHeader } from "../../../../components/ui/PageHeader";
import { SectionCard } from "../../../../components/ui/SectionCard";
import { StatusBadge } from "../../../../components/ui/StatusBadge";
import { buttonClass } from "../../../_components/ui";
import { formatNZT } from "../../../_components/time";
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
    last_scraped_at?: string | null;
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

export default async function EnrichedDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ tab?: string }>;
}) {
  const { id } = await params;
  const spTab = await searchParams;

  const [ip, trust, validation, draft] = await Promise.all([
    apiGet<InternalProductDetail>(`/internal-products/${encodeURIComponent(id)}`),
    apiGet<TrustReport>(`/trust/internal-products/${encodeURIComponent(id)}`),
    apiGet<ValidationResult>(`/validate/internal-products/${encodeURIComponent(id)}`),
    apiGet<DraftPayload>(`/draft/internal-products/${encodeURIComponent(id)}/trademe`),
  ]);

  const sp = ip.supplier_product;
  const tab = (spTab.tab || "compare").toLowerCase();

  const draftStartPrice = draft?.payload?.StartPrice != null ? Number(draft.payload.StartPrice) : null;
  const sourcePrice = sp?.cost_price ?? null;
  const costPrice = sourcePrice;
  const sellPrice = draftStartPrice;
  const marginAmount = sellPrice != null && costPrice != null ? (sellPrice - costPrice) : null;
  const marginPct = marginAmount != null && costPrice ? (marginAmount / costPrice) : null;

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

      <div className="rounded-xl border border-slate-200 bg-white p-3">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">You are viewing</div>
        <div className="mt-1 text-sm font-semibold text-slate-900">Vault 2 · Enriched product</div>
        {String(sp?.sync_status || "").toUpperCase() === "REMOVED" ? (
          <div className="mt-2 text-sm text-slate-800">
            <StatusBadge status="REMOVED" />{" "}
            <span className="ml-1">
              Removed from supplier (last seen: <span className="font-mono text-xs">{formatNZT(sp?.last_scraped_at)}</span>). Blocked from listing.
            </span>
          </div>
        ) : null}
      </div>

      <div className="flex flex-wrap gap-2">
        {[
          ["compare", "Before vs after"],
          ["supplier", "Supplier truth"],
          ["enriched", "Enriched output"],
          ["pricing", "Pricing"],
          ["images", "Images"],
          ["preview", "Listing preview"],
          ["audit", "History"],
        ].map(([k, label]) => (
          <Link
            key={k}
            href={`/vaults/enriched/${encodeURIComponent(String(ip.id))}?tab=${encodeURIComponent(k)}`}
            className={buttonClass({ variant: k === tab ? "primary" : "outline" })}
          >
            {label}
          </Link>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Field label="Internal ID" value={ip.id} testId="field-internal-id" />
        <Field label="Supplier" value={sp?.supplier_name || sp?.supplier_id || "-"} testId="field-supplier" />
        <Field label="Supplier price" value={sp?.cost_price == null ? "-" : `$${sp.cost_price.toFixed(2)}`} testId="field-cost" />
        <Field label="Source category" value={<span className="font-mono text-xs">{sp?.source_category || "-"}</span>} testId="field-category" />
      </div>

      {tab === "compare" ? (
        <SectionCard title="Original vs enriched (fast judgement)">
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Supplier truth (original)</div>
              <div className="mt-3 grid grid-cols-1 gap-3">
                <Field label="Raw title" value={sp?.title || "-"} />
                <Field label="Raw description" value={(sp?.description || "").trim() ? "Present" : "Missing"} />
                <Field label="Source URL" value={sp?.product_url ? <a className="underline" href={sp.product_url} target="_blank" rel="noreferrer">Supplier page</a> : "Missing (blocked)"} />
                <Field label="Source price" value={sp?.cost_price == null ? "-" : `$${sp.cost_price.toFixed(2)}`} />
                <Field label="Cost price" value={sp?.cost_price == null ? "-" : `$${sp.cost_price.toFixed(2)}`} />
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Enriched output (what will list)</div>
              <div className="mt-3 grid grid-cols-1 gap-3">
                <Field label="Enriched title" value={sp?.enriched_title || "Missing (blocked)"} />
                <Field label="Enriched description" value={(sp?.enriched_description || "").trim() ? "Present" : "Missing (blocked)"} />
                <Field label="Sell price" value={draft?.payload?.StartPrice != null ? `$${Number(draft.payload.StartPrice).toFixed(2)}` : "Not set (blocked)"} />
                <Field
                  label="Margin"
                  value={(() => {
                    const cost = sp?.cost_price;
                    const sell = draft?.payload?.StartPrice;
                    if (cost == null || sell == null) return "Not available";
                    const amt = Number(sell) - Number(cost);
                    const pct = Number(cost) ? amt / Number(cost) : null;
                    return `${amt >= 0 ? "" : "-"}$${Math.abs(amt).toFixed(2)}${pct != null ? ` (${(pct * 100).toFixed(1)}%)` : ""}`;
                  })()}
                />
                <Field label="Last scraped" value={formatNZT(sp?.last_scraped_at)} />
              </div>
            </div>
          </div>
        </SectionCard>
      ) : null}

      {tab === "supplier" ? (
        <>
          <SectionCard
            title="Supplier truth (Vault 1)"
            subtitle="What was it originally? This is the scraped supplier data."
            actions={
              sp?.product_url ? (
                <a className={buttonClass({ variant: "link" })} href={sp.product_url} target="_blank" rel="noreferrer">
                  Supplier page →
                </a>
              ) : null
            }
          >
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <Field label="Raw title" value={sp?.title || "-"} />
              <Field label="External SKU" value={<span className="font-mono text-xs">{sp?.external_sku || "-"}</span>} />
              <Field label="Raw description" value={(sp?.description || "").trim() ? "Present" : "Missing"} />
              <Field label="Stock" value={sp?.stock_level == null ? "-" : String(sp.stock_level)} />
            </div>
            <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-900 whitespace-pre-wrap">
              {(sp?.description || "").trim() ? sp?.description : "No supplier description provided."}
            </div>
          </SectionCard>

          {!validation.ok && validation.reason ? (
            <SectionCard title="Publish gates (blocked)" className="border-red-200 bg-red-50">
              <pre className="whitespace-pre-wrap font-mono text-xs text-red-900" data-testid="gate-failure-reason">{validation.reason}</pre>
            </SectionCard>
          ) : null}

          {!trust.is_trusted && trust.blockers?.length ? (
            <SectionCard title="Trust blockers" className="border-amber-200 bg-amber-50">
              <ul className="list-disc pl-5 text-sm text-amber-950" data-testid="trust-blockers-list">
                {trust.blockers.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
            </SectionCard>
          ) : null}

          <SectionCard title="Actions" className="bg-slate-50/50">
            <EnrichedActions internalProductId={ip.id} supplierProductId={sp?.id ?? null} sourceStatus={sp?.sync_status ?? null} />
          </SectionCard>
        </>
      ) : null}

      {tab === "enriched" ? (
        <SectionCard title="Enriched output (Vault 2)" subtitle="What did we change? This is the listing-ready copy.">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <Field label="Enriched title" value={sp?.enriched_title || "-"} />
            <Field label="Enriched description" value={(sp?.enriched_description || "").trim() ? "Present" : "Missing"} />
          </div>
          <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-900 whitespace-pre-wrap">
            {(sp?.enriched_description || "").trim() ? sp?.enriched_description : "No enriched description yet. Run enrichment first."}
          </div>
        </SectionCard>
      ) : null}

      {tab === "pricing" ? (
        <SectionCard title="Pricing" subtitle="What will I sell it for? Margin is shown only when sell price exists.">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-5">
            <Field label="Source price" value={sourcePrice == null ? "-" : `$${sourcePrice.toFixed(2)}`} />
            <Field label="Cost price" value={costPrice == null ? "-" : `$${costPrice.toFixed(2)}`} />
            <Field label="Sell price" value={sellPrice == null ? "Not set (blocked)" : `$${sellPrice.toFixed(2)}`} />
            <Field
              label="Margin $"
              value={marginAmount == null ? "Not available" : `$${marginAmount.toFixed(2)}`}
            />
            <Field
              label="Margin %"
              value={marginPct == null ? "Not available" : `${(marginPct * 100).toFixed(1)}%`}
            />
          </div>
          <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
            <Field
              label="Draft start price (from listing preview)"
              value={draftStartPrice == null ? "-" : `$${draftStartPrice.toFixed(2)}`}
            />
          </div>
          <div className="mt-3 text-xs text-slate-600">Draft pricing comes from the listing preview payload. It is not an operator-set sell price.</div>
        </SectionCard>
      ) : null}

      {tab === "preview" ? (
        <SectionCard title="Listing preview (Draft payload)" subtitle={`Hash: ${draft.payload_hash}`}>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Title</div>
            <div className="mt-1 text-base font-semibold text-slate-900">{String(draft.payload?.Title || "-")}</div>

            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
              <Field label="Category" value={String(draft.payload?.Category || "-")} />
              <Field label="Start price" value={draft.payload?.StartPrice != null ? `$${Number(draft.payload.StartPrice).toFixed(2)}` : "-"} />
              <Field label="Duration" value={draft.payload?.Duration != null ? `${draft.payload.Duration} days` : "-"} />
            </div>

            <div className="mt-4 text-xs font-semibold uppercase tracking-wide text-slate-500">Description</div>
            <div className="mt-2 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-900 whitespace-pre-wrap">
              {Array.isArray(draft.payload?.Description) ? String(draft.payload?.Description?.[0] || "-") : String(draft.payload?.Description || "-")}
            </div>
          </div>
        </SectionCard>
      ) : null}

      {tab === "images" ? (
        sp?.images?.length ? (
          <SectionCard title="Images">
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
              {sp.images.map((src, idx) => (
                <a key={idx} href={imgSrc(src)} target="_blank" rel="noreferrer" className="group">
                  <Image
                    alt={`image-${idx + 1}`}
                    src={imgSrc(src)}
                    width={200}
                    height={128}
                    unoptimized
                    className="h-32 w-full rounded-lg border border-slate-200 object-cover transition-opacity group-hover:opacity-80"
                    data-testid={`product-img-${idx}`}
                  />
                </a>
              ))}
            </div>
          </SectionCard>
        ) : (
          <SectionCard title="Images">
            <div className="text-sm text-slate-500">No images available.</div>
          </SectionCard>
        )
      ) : null}

      {tab === "audit" ? (
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
          <SectionCard title="Trust breakdown">
            <pre className="max-h-[520px] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-900 font-mono" data-testid="trust-breakdown">
              {JSON.stringify(trust.breakdown || {}, null, 2)}
            </pre>
          </SectionCard>
          <SectionCard title="Draft payload (raw JSON)">
            <pre className="max-h-[520px] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-900 font-mono" data-testid="trademe-draft-payload">
              {JSON.stringify(draft.payload || {}, null, 2)}
            </pre>
          </SectionCard>
        </div>
      ) : null}
    </div>
  );
}
