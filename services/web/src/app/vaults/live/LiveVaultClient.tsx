"use client";

import Link from "next/link";
import Image from "next/image";
import { PageHeader } from "../../../components/ui/PageHeader";
import { DataTable, ColumnDef } from "../../../components/tables/DataTable";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import { buttonClass } from "../../_components/ui";

type LiveItem = {
    id: number;
    tm_listing_id: string | null;
    internal_product_id: number | null;
    actual_state: string | null;
    lifecycle_state: string | null;
    actual_price: number | null;
    view_count: number | null;
    watch_count: number | null;
    category_id: string | null;
    title?: string | null;
    thumb?: string | null;
    source_category?: string | null;
    last_synced_at: string | null;
};

function imgSrc(raw: string): string {
    const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
    if (raw.startsWith("/media/")) return `${base}${raw}`;
    return raw;
}

export function LiveVaultClient({
    items,
    total,
    page,
    perPage,
    q,
    status,
    supplierId
}: {
    items: LiveItem[],
    total: number,
    page: number,
    perPage: number,
    q: string,
    status: string,
    supplierId: string,
    sourceCategory: string
}) {
    const columns: ColumnDef<LiveItem>[] = [
        {
            key: "id",
            label: "ID",
            render: (val) => (
                <Link className="text-slate-900 underline" href={`/vaults/live/${val}`} data-testid={`lnk-id-${val}`}>
                    {val as number}
                </Link>
            )
        },
        {
            key: "thumb",
            label: "Img",
            render: (val, row) => (val as string) ? (
                <Link href={`/vaults/live/${row.id}`} className="block w-12" data-testid={`lnk-img-${row.id}`}>
                    <Image
                        alt=""
                        src={imgSrc(val as string)}
                        width={48}
                        height={40}
                        unoptimized
                        className="h-10 w-12 rounded-md border border-slate-200 object-cover"
                    />
                </Link>
            ) : (
                <div className="h-10 w-12 rounded-md border border-dashed border-slate-200 bg-slate-50" />
            )
        },
        { key: "tm_listing_id", label: "TM ID", className: "font-mono text-xs" },
        {
            key: "title",
            label: "Title",
            render: (val, row) => (
                <Link className="text-slate-900 hover:underline" href={`/vaults/live/${row.id}`} data-testid={`lnk-title-${row.id}`}>
                    {val as string || "-"}
                </Link>
            )
        },
        { key: "actual_state", label: "State", render: (val) => <StatusBadge status={val as string} /> },
        { key: "lifecycle_state", label: "Lifecycle", render: (val) => <StatusBadge status={val as string} /> },
        { key: "actual_price", label: "Price", render: (val) => val == null ? "-" : `$${(val as number).toFixed(2)}` },
        { key: "view_count", label: "Views" },
        { key: "watch_count", label: "Watch" },
        { key: "last_synced_at", label: "Synced" },
    ];

    return (
        <div className="space-y-6">
            <PageHeader
                title="Vault 3 · Listings"
                subtitle="Click to inspect trust, profitability, payload drift, lifecycle."
            />

            <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
                <div className="flex flex-col gap-3 border-b border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between">
                    <form className="flex flex-wrap items-center gap-4" method="get" data-testid="search-form">
                        <input type="hidden" name="page" value="1" />
                        <label className="flex flex-col gap-1 text-xs font-medium text-slate-600">
                            <span>Search Title/TM ID</span>
                            <input
                                name="q"
                                defaultValue={q}
                                data-testid="inp-search-q"
                                className="w-52 rounded-md border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-900 focus:border-slate-400 focus:outline-none"
                                placeholder="search..."
                            />
                        </label>
                        <label className="flex flex-col gap-1 text-xs font-medium text-slate-600">
                            <span>Status</span>
                            <select
                                name="status"
                                defaultValue={status}
                                data-testid="sel-search-status"
                                className="w-32 rounded-md border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-900 focus:border-slate-400 focus:outline-none"
                            >
                                <option value="Live">Live</option>
                                <option value="DRY_RUN">DRY_RUN</option>
                                <option value="Withdrawn">Withdrawn</option>
                                <option value="All">All</option>
                            </select>
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
                                href="/vaults/live?status=Live"
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
