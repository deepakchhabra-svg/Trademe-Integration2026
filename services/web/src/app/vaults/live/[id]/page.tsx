import Link from "next/link";
import { apiGet } from "../../../_components/api";
import { PageHeader } from "../../../../components/ui/PageHeader";
import { SectionCard } from "../../../../components/ui/SectionCard";
import { StatusBadge } from "../../../../components/ui/StatusBadge";
import { buttonClass } from "../../../_components/ui";
import { ListingActions } from "./Actions";
import { formatNZT } from "../../../_components/time";

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
  payload_preview?: Record<string, unknown> | null;
  launchlock?: { ready: boolean; top_blocker: string | null; checks: { key: string; ok: boolean; reason?: string | null }[] };
  profitability_preview?: Record<string, unknown>;
  lifecycle_recommendation?: Record<string, unknown>;
  trust_report?: { score: number; is_trusted: boolean; blockers: string[]; breakdown: Record<string, string> };
  supplier_product?: {
    id: number;
    external_sku: string;
    source_category: string | null;
    product_url: string | null;
    cost_price?: number | null;
    condition?: string | null;
    sync_status?: string | null;
    images?: string[] | null;
  } | null;
  internal_product?: { id: number; sku: string; title: string | null } | null;
};

function paymentLabel(bitflags: unknown): string {
  const v = Number(bitflags);
  if (!Number.isFinite(v) || v <= 0) return "-";
  const labels: string[] = [];
  // Trade Me V1 common bitflags: 1=Bank Deposit, 2=Credit Card, 4=Cash
  if (v & 1) labels.push("Bank deposit");
  if (v & 2) labels.push("Credit card");
  if (v & 4) labels.push("Cash");
  return labels.length ? labels.join(" + ") : String(v);
}

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
      {l.launchlock ? (
        <StatusBadge status={l.launchlock.ready ? "SUCCESS" : "BLOCKED"} label={l.launchlock.ready ? "READY" : "BLOCKED"} />
      ) : null}
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
        {l.launchlock && !l.launchlock.ready && l.launchlock.top_blocker ? (
          <div className="mt-2 text-sm text-slate-900">
            <span className="font-semibold">Top blocker:</span> {l.launchlock.top_blocker}
          </div>
        ) : null}
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
        <Field
          label="Source price"
          value={l.supplier_product?.cost_price == null ? "-" : `$${Number(l.supplier_product?.cost_price).toFixed(2)}`}
          testId="field-source-price"
        />
        <Field
          label="Cost price"
          value={l.supplier_product?.cost_price == null ? "-" : `$${Number(l.supplier_product?.cost_price).toFixed(2)}`}
          testId="field-cost-price"
        />
        <Field
          label="Sell price"
          value={(l.payload_preview as any)?.StartPrice != null ? `$${Number((l.payload_preview as any)?.StartPrice).toFixed(2)}` : "Not set (blocked)"}
          testId="field-sell-price"
        />
        <Field
          label="Margin"
          value={(() => {
            const cost = l.supplier_product?.cost_price;
            const sell = (l.payload_preview as any)?.StartPrice;
            if (cost == null || sell == null) return "Not available";
            const amt = Number(sell) - Number(cost);
            const pct = Number(cost) ? amt / Number(cost) : null;
            return `${amt >= 0 ? "" : "-"}$${Math.abs(amt).toFixed(2)}${pct != null ? ` (${(pct * 100).toFixed(1)}%)` : ""}`;
          })()}
          testId="field-margin"
        />
        <Field label="Views" value={l.view_count ?? 0} testId="field-views" />
        <Field label="Watchers" value={l.watch_count ?? 0} testId="field-watchers" />
        <Field label="Last synced" value={formatNZT(l.last_synced_at)} testId="field-last-synced" />
      </div>

      {tab === "overview" ? (
        <>
          {l.launchlock ? (
            <SectionCard title="Hard gates (LaunchLock)">
              <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                {l.launchlock.checks.map((c) => (
                  <div key={c.key} className="flex items-start gap-2 rounded-lg border border-slate-200 bg-white p-3">
                    <StatusBadge status={c.ok ? "SUCCESS" : "BLOCKED"} label={c.ok ? "OK" : "BLOCKED"} />
                    <div>
                      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{c.key.replace(/_/g, " ")}</div>
                      <div className="mt-1 text-sm text-slate-900">{c.ok ? "Pass" : (c.reason || "Blocked")}</div>
                    </div>
                  </div>
                ))}
              </div>
            </SectionCard>
          ) : null}

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
        <SectionCard title="Listing preview (what buyers will see)">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Title</div>
            <div className="mt-1 text-base font-semibold text-slate-900">
              {String((l.payload_preview as any)?.Title || l.internal_product?.title || "-")}
            </div>
            <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
              <Field label="Trade Me ID" value={l.tm_listing_id || "-"} />
              <Field label="Sell price" value={(l.payload_preview as any)?.StartPrice != null ? `$${Number((l.payload_preview as any)?.StartPrice).toFixed(2)}` : (l.actual_price == null ? "Not set (blocked)" : `$${l.actual_price.toFixed(2)}`)} />
              <Field label="Category" value={String((l.payload_preview as any)?.Category || l.category_id || "-")} />
            </div>

            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Field label="Condition" value={l.supplier_product?.condition || "-"} />
              <Field label="Payment" value={paymentLabel((l.payload_preview as any)?.PaymentOptions)} />
              <Field
                label="Shipping"
                value={
                  Array.isArray((l.payload_preview as any)?.ShippingOptions)
                    ? `${(l.payload_preview as any)?.ShippingOptions?.length} options`
                    : "-"
                }
              />
              <Field label="Pickup" value={String((l.payload_preview as any)?.Pickup ?? "-")} />
            </div>

            {Array.isArray((l.payload_preview as any)?.ShippingOptions) && (l.payload_preview as any)?.ShippingOptions?.length ? (
              <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-900">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Shipping options</div>
                <ul className="mt-2 list-disc pl-5">
                  {(l.payload_preview as any)?.ShippingOptions?.slice(0, 8).map((s: any, idx: number) => (
                    <li key={idx}>
                      {String(s?.Method || "Shipping")} · ${Number(s?.Price || 0).toFixed(2)}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            <div className="mt-4 text-xs font-semibold uppercase tracking-wide text-slate-500">Description</div>
            {(() => {
              const d0 = (l.payload_preview as any)?.Description;
              const d = Array.isArray(d0) ? String(d0?.[0] || "") : String(d0 || "");
              const looksHtml = d.includes("<") && d.includes(">");
              if (!d) {
                return <div className="mt-2 text-sm text-slate-500">No description in payload.</div>;
              }
              return (
                <div className="mt-2 grid grid-cols-1 gap-3 lg:grid-cols-2">
                  <div className="rounded-lg border border-slate-200 bg-white p-3">
                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Rendered</div>
                    <div className="mt-2 text-sm text-slate-900">
                      {looksHtml ? (
                        <div dangerouslySetInnerHTML={{ __html: d }} />
                      ) : (
                        <div className="whitespace-pre-wrap">{d}</div>
                      )}
                    </div>
                  </div>
                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Raw</div>
                    <pre className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap text-[11px] text-slate-900">{d}</pre>
                  </div>
                </div>
              );
            })()}

            <div className="mt-4 text-xs font-semibold uppercase tracking-wide text-slate-500">Images</div>
            <div className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-4 md:grid-cols-6">
              {Array.isArray((l.payload_preview as any)?.PhotoUrls) && (l.payload_preview as any)?.PhotoUrls?.length ? (
                (l.payload_preview as any)?.PhotoUrls?.slice(0, 12).map((u: string, idx: number) => (
                  <a key={idx} href={String(u)} target="_blank" rel="noreferrer" className="block">
                    {/* Image is served via API base when /media/ */}
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      alt={`photo-${idx + 1}`}
                      src={String(u).startsWith("/media/") ? `${process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000"}${u}` : String(u)}
                      className="h-24 w-full rounded-md border border-slate-200 object-cover"
                    />
                  </a>
                ))
              ) : (
                <div className="text-sm text-slate-500">No images in draft payload.</div>
              )}
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
