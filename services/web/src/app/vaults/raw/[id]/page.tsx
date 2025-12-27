import Link from "next/link";

import { apiGet } from "../../../_components/api";
import { Badge } from "../../../_components/Badge";

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

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-sm text-slate-900">{value}</div>
    </div>
  );
}

function imgSrc(raw: string): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  if (raw.startsWith("/media/")) return `${base}${raw}`;
  return raw;
}

export default async function RawDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const sp = await apiGet<SupplierProduct>(`/supplier-products/${encodeURIComponent(id)}`);

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Link className="text-sm text-slate-600 underline" href="/vaults/raw">
              Vault 1
            </Link>
            <span className="text-sm text-slate-400">/</span>
            <span className="text-sm font-medium text-slate-900">SupplierProduct #{sp.id}</span>
          </div>
          <h1 className="mt-2 text-lg font-semibold tracking-tight">{sp.title || "(no title)"}</h1>
          <p className="mt-1 text-sm text-slate-600">
            Supplier: {sp.supplier_name || sp.supplier_id || "-"} · SKU:{" "}
            <span className="font-mono text-xs">{sp.external_sku}</span>
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <Badge tone={sp.sync_status === "PRESENT" ? "emerald" : sp.sync_status === "REMOVED" ? "red" : "amber"}>
            {sp.sync_status || "unknown"}
          </Badge>
          <Badge tone={sp.enrichment_status === "SUCCESS" ? "emerald" : sp.enrichment_status === "FAILED" ? "red" : "slate"}>
            enrich: {sp.enrichment_status || "unknown"}
          </Badge>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        <Field label="Cost price" value={sp.cost_price == null ? "-" : `$${sp.cost_price.toFixed(2)}`} />
        <Field label="Stock level" value={sp.stock_level ?? "-"} />
        <Field label="Source category" value={<span className="font-mono text-xs">{sp.source_category || "-"}</span>} />
        <Field label="Last scraped" value={sp.last_scraped_at || "-"} />
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="text-sm font-semibold">Raw description</div>
            {sp.product_url ? (
              <a
                className="text-xs text-slate-700 underline"
                href={sp.product_url}
                target="_blank"
                rel="noreferrer"
              >
                Open supplier page
              </a>
            ) : null}
          </div>
          <pre className="mt-3 max-h-[420px] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-900">
            {sp.description || "-"}
          </pre>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="text-sm font-semibold">Enriched copy</div>
            <div className="text-xs text-slate-500">{sp.enriched_title ? "title+desc" : "desc only"}</div>
          </div>
          {sp.enrichment_error ? (
            <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-800">
              {sp.enrichment_error}
            </div>
          ) : null}
          <pre className="mt-3 max-h-[420px] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-900">
            {sp.enriched_description || "-"}
          </pre>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="text-sm font-semibold">Images</div>
        {sp.images?.length ? (
          <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
            {sp.images.map((src, idx) => (
              <a key={idx} href={imgSrc(src)} target="_blank" rel="noreferrer" className="group">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  alt={`image-${idx + 1}`}
                  src={imgSrc(src)}
                  className="h-28 w-full rounded-lg border border-slate-200 object-cover group-hover:opacity-90"
                />
              </a>
            ))}
          </div>
        ) : (
          <div className="mt-2 text-sm text-slate-600">No images.</div>
        )}
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="text-sm font-semibold">Specs (JSON)</div>
        <pre className="mt-3 max-h-[420px] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-900">
          {JSON.stringify(sp.specs || {}, null, 2)}
        </pre>
        <div className="mt-2 text-xs text-slate-500">
          Snapshot: <span className="font-mono">{sp.snapshot_hash || "-"}</span>
        </div>
      </div>
    </div>
  );
}

