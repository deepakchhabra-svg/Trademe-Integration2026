import Link from "next/link";
import Image from "next/image";

import { apiGet } from "../../_components/api";
import { PageHeader } from "../../../components/ui/PageHeader";
import { SectionCard } from "../../../components/ui/SectionCard";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import { formatNZT } from "../../_components/time";
import { buttonClass } from "../../_components/ui";

type Inspector = {
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
    last_scraped_at: string | null;
    internal_product_id: number | null;
  };
  internal_product: { id: number; sku: string; title: string | null; supplier_product: Record<string, unknown> } | null;
  listings: Array<{
    id: number;
    tm_listing_id: string | null;
    actual_state: string | null;
    actual_price: number | null;
    category_id: string | null;
    last_synced_at: string | null;
    payload_hash: string | null;
    supplier_product?: Record<string, unknown>;
    internal_product?: Record<string, unknown>;
  }>;
};

function imgSrc(raw: string): string {
  if (raw.startsWith("/media/")) return raw.replace(/^\/media\//, "/api/media/");
  return raw;
}

export default async function ProductInspectorPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const data = await apiGet<Inspector>(`/inspector/supplier-products/${encodeURIComponent(id)}`);
  const sp = data.supplier_product;
  const latest = data.listings?.[0] || null;

  const breadcrumbs = (
    <div className="flex items-center gap-2 text-sm">
      <Link className="text-slate-600 hover:text-slate-900 underline" href="/products">
        Products
      </Link>
      <span className="text-slate-400">/</span>
      <span className="font-medium text-slate-900">#{sp.id}</span>
    </div>
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title={sp.title || "(no title)"}
        subtitle="Single truth screen: Raw → Enriched → Listing + gates."
        breadcrumbs={breadcrumbs}
        actions={
          <div className="flex items-center gap-2">
            <StatusBadge status={sp.sync_status || "UNKNOWN"} />
            <StatusBadge status={sp.enrichment_status || "PENDING"} />
            {latest ? <StatusBadge status={latest.actual_state || "UNKNOWN"} /> : <StatusBadge status="BLOCKED" label="No draft" />}
          </div>
        }
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <SectionCard title="Vault 1 · Supplier truth">
          <div className="grid grid-cols-1 gap-3">
            <div className="text-xs text-slate-500">Supplier</div>
            <div className="text-sm text-slate-900">{sp.supplier_name || sp.supplier_id || "-"}</div>
            <div className="text-xs text-slate-500">Source category</div>
            <div className="text-sm font-mono text-slate-900">{sp.source_category || "Unknown"}</div>
            <div className="text-xs text-slate-500">Source price / Stock</div>
            <div className="text-sm text-slate-900">
              {sp.cost_price == null ? "-" : `$${sp.cost_price.toFixed(2)}`} · {sp.stock_level == null ? "-" : sp.stock_level}
            </div>
            <div className="text-xs text-slate-500">Last scraped</div>
            <div className="text-sm text-slate-900">{formatNZT(sp.last_scraped_at)}</div>
            {sp.product_url ? (
              <a className={buttonClass({ variant: "link" })} href={sp.product_url} target="_blank" rel="noreferrer">
                Supplier page →
              </a>
            ) : (
              <div className="text-sm text-slate-600">No source URL (blocked).</div>
            )}
          </div>
        </SectionCard>

        <SectionCard title="Vault 2 · Enriched">
          <div className="grid grid-cols-1 gap-3">
            <div className="text-xs text-slate-500">Enriched title</div>
            <div className="text-sm text-slate-900">{sp.enriched_title || "Missing (blocked)"}</div>
            <div className="text-xs text-slate-500">Enriched description</div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-900 whitespace-pre-wrap">
              {sp.enriched_description || "Missing (blocked)"}
            </div>
            {sp.enrichment_error ? (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
                {sp.enrichment_error}
              </div>
            ) : null}
            {sp.internal_product_id ? (
              <Link className={buttonClass({ variant: "link" })} href={`/vaults/enriched/${sp.internal_product_id}`}>
                Open Vault 2 →
              </Link>
            ) : (
              <div className="text-sm text-slate-600">No internal product yet.</div>
            )}
          </div>
        </SectionCard>

        <SectionCard title="Vault 3 · Listing">
          {latest ? (
            <div className="space-y-3">
              <div className="text-xs text-slate-500">State</div>
              <div className="text-sm text-slate-900">{latest.actual_state || "-"}</div>
              <div className="text-xs text-slate-500">Sell price</div>
              <div className="text-sm text-slate-900">{latest.actual_price == null ? "Not set (blocked)" : `$${latest.actual_price.toFixed(2)}`}</div>
              <div className="text-xs text-slate-500">Last synced</div>
              <div className="text-sm text-slate-900">{formatNZT(latest.last_synced_at)}</div>
              <Link className={buttonClass({ variant: "primary" })} href={`/vaults/live/${latest.id}?tab=preview`}>
                View buyer preview
              </Link>
            </div>
          ) : (
            <div className="text-sm text-slate-700">
              No Draft/Live listing exists yet. Next: create drafts from Ops Workbench.
            </div>
          )}
        </SectionCard>
      </div>

      {sp.images?.length ? (
        <SectionCard title="Images (uploadable)">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 md:grid-cols-6">
            {sp.images.slice(0, 12).map((u, idx) => (
              <a key={idx} href={imgSrc(u)} target="_blank" rel="noreferrer">
                <Image alt="" src={imgSrc(u)} width={240} height={160} unoptimized className="h-24 w-full rounded-md border border-slate-200 object-cover" />
              </a>
            ))}
          </div>
        </SectionCard>
      ) : null}
    </div>
  );
}

