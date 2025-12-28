"use client";

import Link from "next/link";
import { PageHeader } from "../../../components/ui/PageHeader";
import { DataTable, ColumnDef } from "../../../components/tables/DataTable";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import { buttonClass } from "../../_components/ui";

type EnrichedItem = {
    id: number;
    sku: string;
    title: string | null;
    supplier_product_id: number | null;
    supplier_id: number | null;
    cost_price: number | null;
    enriched_title: string | null;
    enriched_description: string | null;
    images?: string[];
    source_category?: string | null;
    product_url?: string | null;
    sync_status?: string | null;
    enrichment_status?: string | null;
};

function imgSrc(raw: string): string {
    const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
    if (raw.startsWith("/media/")) return `${base}${raw}`;
    return raw;
}

export function EnrichedVaultClient({
    items,
    total,
    page,
    perPage,
    q,
    supplierId,
    enrichment,
    sourceCategory
}: {
    items: EnrichedItem[],
    total: number,
    page: number,
    perPage: number,
    q: string,
    supplierId: string,
    enrichment: string,
    sourceCategory: string
}) {
    const columns: ColumnDef<EnrichedItem>[] = [
        {
            key: "id",
            label: "ID",
            render: (val) => (
                <Link className="text-slate-900 underline" href={`/vaults/enriched/${val}`} data-testid={`lnk-id-${val}`}>
                    {val as number}
                </Link>
            )
        },
        {
            key: "images",
            label: "Img",
            render: (val, row) => (val as string[])?.length ? (
                <Link href={`/vaults/enriched/${row.id}`} className="block w-12" data-testid={`lnk-img-${row.id}`}>
                    <img
                        alt=""
                        src={imgSrc((val as string[])[0])}
                        className="h-10 w-12 rounded-md border border-slate-200 object-cover"
                    />
                </Link>
            ) : (
                <div className="h-10 w-12 rounded-md border border-dashed border-slate-200 bg-slate-50" />
            )
        },
        { key: "sku", label: "SKU", className: "font-mono text-xs" },
        {
            key: "title",
            label: "Title",
            render: (val, row) => (
                <Link className="text-slate-900 hover:underline" href={`/vaults/enriched/${row.id}`} data-testid={`lnk-title-${row.id}`}>
                    {val as string || "-"}
                </Link>
            )
        },
        { key: "cost_price", label: "Cost", render: (val) => val == null ? "-" : `$${(val as number).toFixed(2)}` },
        {
            key: "product_url",
            label: "Source",
            render: (val) => val ? (
                <a href={val as string} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                    Link
                </a>
            ) : "-"
        },
        { key: "sync_status", label: "Sync", render: (val) => <StatusBadge status={val as string} /> },
        { key: "source_category", label: "Category", className: "font-mono text-[11px] text-slate-700" },
        {
            key: "enrichment_status",
            label: "Enrichment",
            render: (val, row) => <StatusBadge status={val as string || (row.enriched_description ? "SUCCESS" : "NOT_ENRICHED")} />
        },
    ];

    return (
        <div className="space-y-6">
            <PageHeader
                title="Vault 2 · Enriched"
                subtitle="Internal products (click a row for trust + gate inspector)"
            />

            <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
                <div className="flex flex-col gap-3 border-b border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between">
                    <form className="flex flex-wrap items-center gap-4" method="get" data-testid="search-form">
                        <input type="hidden" name="page" value="1" />
                        <label className="flex flex-col gap-1 text-xs font-medium text-slate-600">
                            <span>Search Title/Text</span>
                            <input
                                name="q"
                                defaultValue={q}
                                data-testid="inp-search-q"
                                className="w-56 rounded-md border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-900 focus:border-slate-400 focus:outline-none"
                                placeholder="search..."
                            />
                        </label>
                        <label className="flex flex-col gap-1 text-xs font-medium text-slate-600">
                            <span>Supplier ID</span>
                            <input
                                name="supplier_id"
                                defaultValue={supplierId}
                                data-testid="inp-search-supplier"
                                className="w-20 rounded-md border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-900 focus:border-slate-400 focus:outline-none"
                                placeholder="id"
                            />
                        </label>
                        <label className="flex flex-col gap-1 text-xs font-medium text-slate-600">
                            <span>Enrichment</span>
                            <select
                                name="enrichment"
                                defaultValue={enrichment}
                                data-testid="sel-search-enrichment"
                                className="rounded-md border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-900 focus:border-slate-400 focus:outline-none"
                            >
                                <option value="">All</option>
                                <option value="Enriched">Enriched</option>
                                <option value="Not Enriched">Not Enriched</option>
                            </select>
                        </label>
                        <div className="flex items-end gap-2">
                            <button
                                type="submit"
                                className={buttonClass({ variant: "primary" })}
                                data-testid="btn-search-apply"
                            >
                                Apply
                            </button>
                            <Link
                                className="flex h-8 items-center text-xs text-slate-500 hover:text-slate-800"
                                href="/vaults/enriched"
                                data-testid="lnk-search-reset"
                            >
                                Reset
                            </Link>
                        </div>
                    </form>
                </div>

                <DataTable
                    columns={columns}
                    data={items}
                    totalCount={total}
                    currentPage={page}
                    pageSize={perPage}
                />
            </div>
        </div>
    );
}
