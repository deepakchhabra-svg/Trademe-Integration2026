"use client";

import Link from "next/link";
import Image from "next/image";
import { PageHeader } from "../../components/ui/PageHeader";
import { DataTable, ColumnDef } from "../../components/tables/DataTable";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { buttonClass } from "../_components/ui";
import { formatNZT } from "../_components/time";
import type { MasterProductRow } from "./page";

function imgSrc(raw: string): string {
  if (raw.startsWith("/media/")) return raw.replace(/^\/media\//, "/api/media/");
  return raw;
}

export function ProductsClient({
  items,
  total,
  page,
  perPage,
  q,
  supplierId,
  sourceCategory,
  stage,
}: {
  items: MasterProductRow[];
  total: number;
  page: number;
  perPage: number;
  q: string;
  supplierId: string;
  sourceCategory: string;
  stage: string;
}) {
  const columns: ColumnDef<MasterProductRow>[] = [
    {
      key: "supplier_product_id",
      label: "Raw ID",
      render: (val) => (
        <Link className="underline" href={`/products/${val}`} data-testid={`lnk-master-raw-${val}`}>
          {val as number}
        </Link>
      ),
    },
    {
      key: "images",
      label: "Img",
      render: (val, row) =>
        (val as string[])?.length ? (
          <Link href={`/vaults/raw/${row.supplier_product_id}`} className="block w-12">
            <Image
              alt=""
              src={imgSrc((val as string[])[0])}
              width={48}
              height={40}
              unoptimized
              className="h-10 w-12 rounded-md border border-slate-200 object-cover"
            />
          </Link>
        ) : (
          <div className="h-10 w-12 rounded-md border border-dashed border-slate-200 bg-slate-50" />
        ),
    },
    {
      key: "title",
      label: "Product",
      render: (val, row) => (
        <div className="min-w-[360px]">
          <Link className="block truncate font-medium text-slate-900 hover:underline" title={(val as string) || ""} href={`/vaults/raw/${row.supplier_product_id}`}>
            {(val as string) || "-"}
          </Link>
          <div className="mt-0.5 text-[11px] text-slate-500">
            Supplier SKU: <span className="font-mono">{row.supplier_sku}</span>
            {row.internal_sku ? (
              <>
                {" · "}Internal:{" "}
                <Link className="underline" href={`/vaults/enriched/${row.internal_product_id}`}>
                  <span className="font-mono">{row.internal_sku}</span>
                </Link>
              </>
            ) : null}
          </div>
        </div>
      ),
    },
    { key: "cost_price", label: "Cost", render: (val) => (val == null ? "-" : `$${Number(val).toFixed(2)}`) },
    { key: "source_status", label: "Source", render: (val) => <StatusBadge status={(val as string) || "UNKNOWN"} /> },
    { key: "enrichment_status", label: "Enrichment", render: (val) => <StatusBadge status={(val as string) || "PENDING"} /> },
    {
      key: "listing_stage",
      label: "Listing",
      render: (_val, row) =>
        row.listing_stage === "live" ? <StatusBadge status="LIVE" label="Live" /> : row.listing_stage === "draft" ? <StatusBadge status="DRY_RUN" label="Draft" /> : "-",
    },
    {
      key: "blocked_reasons",
      label: "Blocked reason",
      render: (val) => {
        const arr = Array.isArray(val) ? (val as string[]) : [];
        return arr.length ? <span title={arr.join(" · ")} className="text-xs text-amber-900">{arr[0]}{arr.length > 1 ? ` (+${arr.length - 1})` : ""}</span> : "-";
      },
    },
    { key: "last_scraped_at", label: "Last scraped", render: (val) => formatNZT(val as string | null) },
  ];

  return (
    <div className="space-y-6">
      <PageHeader title="Products" subtitle="Single view across supplier → enriched → listing. Use filters to find what’s ready, blocked, or live." />

      <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-col gap-3 border-b border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between">
          <form className="flex flex-wrap items-end gap-3" method="get">
            <input type="hidden" name="page" value="1" />
            <label className="text-xs font-medium text-slate-600">
              <div className="mb-1">Search</div>
              <input name="q" defaultValue={q} className="w-56 rounded-md border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-900" placeholder="SKU or title" />
            </label>
            <label className="text-xs font-medium text-slate-600">
              <div className="mb-1">Supplier ID</div>
              <input name="supplier_id" defaultValue={supplierId} className="w-20 rounded-md border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-900" placeholder="id" />
            </label>
            <label className="text-xs font-medium text-slate-600">
              <div className="mb-1">Source category</div>
              <input name="source_category" defaultValue={sourceCategory} className="w-40 rounded-md border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-900" placeholder="e.g. all" />
            </label>
            <label className="text-xs font-medium text-slate-600">
              <div className="mb-1">Stage</div>
              <select name="stage" defaultValue={stage} className="w-40 rounded-md border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-900">
                <option value="all">All</option>
                <option value="raw">Raw only</option>
                <option value="enriched">Enriched (ready)</option>
                <option value="draft">Draft</option>
                <option value="live">Live</option>
                <option value="blocked">Blocked</option>
              </select>
            </label>
            <button type="submit" className={buttonClass({ variant: "primary" })}>Apply</button>
            <Link className={buttonClass({ variant: "link" })} href="/products">Reset</Link>
          </form>
        </div>

        <DataTable
          columns={columns}
          data={items}
          totalCount={total}
          currentPage={page}
          pageSize={perPage}
          rowIdKey="supplier_product_id"
          emptyState={
            <div className="text-center">
              <div className="text-sm font-semibold text-slate-900">No products match this filter.</div>
              <div className="mt-1 text-sm text-slate-600">Next action: open Pipeline and run Scrape (then Images/Enrich), or reset filters.</div>
              <div className="mt-3 flex justify-center gap-2">
                <Link className={buttonClass({ variant: "primary" })} href="/pipeline">
                  Open Pipeline
                </Link>
                <Link className={buttonClass({ variant: "outline" })} href="/products">
                  Reset filters
                </Link>
              </div>
            </div>
          }
        />
      </div>
    </div>
  );
}

