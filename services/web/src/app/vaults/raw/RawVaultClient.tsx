"use client";

import Link from "next/link";
import Image from "next/image";
import { useEffect, useMemo, useState } from "react";
import { PageHeader } from "../../../components/ui/PageHeader";
import { FilterChips } from "../../../components/ui/FilterChips";
import { DataTable, ColumnDef } from "../../../components/tables/DataTable";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import { buttonClass } from "../../_components/ui";
import { apiGetClient } from "../../_components/api_client";

type RawItem = {
    id: number;
    supplier_id: number | null;
    external_sku: string;
    title: string | null;
    cost_price: number | null;
    stock_level: number | null;
    sync_status: string | null;
    source_category?: string | null;
    final_category_id?: string | null;
    final_category_name?: string | null;
    final_category_is_default?: boolean;
    enrichment_status?: string | null;
    enriched_title?: string | null;
    product_url: string | null;
    images: string[];
    last_scraped_at: string | null;
};

function formatNZT(iso: string | null): string {
    if (!iso) return "-";
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

function domainLabel(url: string): string {
    try {
        const u = new URL(url);
        return u.hostname.replace(/^www\./, "");
    } catch {
        return "Open";
    }
}

function imgSrc(raw: string): string {
    if (raw.startsWith("/media/")) return raw.replace(/^\/media\//, "/api/media/");
    return raw;
}

export function RawVaultClient({
    items,
    total,
    page,
    perPage,
    q,
    supplierId,
    syncStatus,
    sourceCategory
}: {
    items: RawItem[],
    total: number,
    page: number,
    perPage: number,
    q: string,
    supplierId: string,
    syncStatus: string,
    sourceCategory: string
}) {
    const [liveItems, setLiveItems] = useState<RawItem[]>(items);
    const [liveTotal, setLiveTotal] = useState<number>(total);
    const [auto, setAuto] = useState<boolean>(false);
    const [refreshing, setRefreshing] = useState<boolean>(false);
    const [lastRefresh, setLastRefresh] = useState<string | null>(null);
    const [err, setErr] = useState<string | null>(null);

    const base = new URLSearchParams();
    if (q) base.set("q", q);
    if (supplierId) base.set("supplier_id", supplierId);
    // keep explicit so chip can clear it to "All"
    if (syncStatus) base.set("sync_status", syncStatus);
    if (sourceCategory) base.set("source_category", sourceCategory);
    base.set("page", String(page));
    base.set("per_page", String(perPage));

    const isNarrow = useMemo(() => {
        // Safety: only allow auto-refresh when the operator has narrowed scope.
        return Boolean(q) || Boolean(supplierId) || Boolean(sourceCategory);
    }, [q, supplierId, sourceCategory]);

    useEffect(() => {
        setLiveItems(items);
        setLiveTotal(total);
    }, [items, total]);

    async function refreshNow() {
        if (refreshing) return;
        setRefreshing(true);
        setErr(null);
        try {
            const resp = await apiGetClient<{ items: RawItem[]; total: number }>(`/vaults/raw?${base.toString()}`);
            setLiveItems(resp.items || []);
            setLiveTotal(resp.total || 0);
            setLastRefresh(new Date().toISOString());
        } catch (e) {
            setErr(e instanceof Error ? e.message : "Refresh failed");
        } finally {
            setRefreshing(false);
        }
    }

    useEffect(() => {
        if (!auto) return;
        if (!isNarrow) return;
        const t = window.setInterval(() => void refreshNow(), 3000);
        return () => window.clearInterval(t);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [auto, isNarrow, base.toString()]);
    const clear = (key: string) => {
        const p = new URLSearchParams(base.toString());
        if (key === "sync_status") {
            // Server defaults to PRESENT when missing; explicit empty disables filtering.
            p.set("sync_status", "");
        } else {
            p.delete(key);
        }
        p.set("page", "1");
        return `/vaults/raw?${p.toString()}`;
    };
    const chips = [
        { label: "Supplier ID", value: supplierId || null, href: clear("supplier_id") },
        { label: "Source status", value: syncStatus || null, href: clear("sync_status") },
        { label: "Source category", value: sourceCategory || null, href: clear("source_category") },
        { label: "Search", value: q || null, href: clear("q") },
    ];
    const columns: ColumnDef<RawItem>[] = [
        {
            key: "id",
            label: "ID",
            render: (val) => (
                <Link className="text-slate-900 underline" href={`/vaults/raw/${val}`} data-testid={`lnk-id-${val}`}>
                    {val as number}
                </Link>
            )
        },
        {
            key: "images",
            label: "Img",
            render: (val, row) => (val as string[])?.length ? (
                <Link href={`/vaults/raw/${row.id}`} className="block w-12" data-testid={`lnk-img-${row.id}`}>
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
            )
        },
        { key: "external_sku", label: "SKU", className: "font-mono text-xs" },
        {
            key: "title",
            label: "Title",
            render: (val, row) => (
                <Link
                    className="block max-w-[520px] truncate text-slate-900 hover:underline"
                    title={(val as string) || ""}
                    href={`/vaults/raw/${row.id}`}
                    data-testid={`lnk-title-${row.id}`}
                >
                    {(val as string) || "-"}
                </Link>
            )
        },
        { key: "cost_price", label: "Supplier price", render: (val) => val == null ? "-" : `$${(val as number).toFixed(2)}` },
        {
            key: "product_url",
            label: "Supplier page",
            render: (val) => val ? (
                <a
                    href={val as string}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-indigo-700 hover:underline"
                    title={val as string}
                >
                    {domainLabel(val as string)}
                </a>
            ) : "-"
        },
        { key: "sync_status", label: "Source status", render: (val) => <StatusBadge status={val as string} /> },
        {
            key: "source_category",
            label: "Source category",
            className: "font-mono text-[11px] text-slate-700",
            render: (val) => {
                const v = (val as string | null) || "";
                if (v.trim()) return v;
                return <span title="Supplier did not provide a category/handle for this item.">Unknown</span>;
            },
        },
        {
            key: "final_category_id",
            label: "Final category",
            className: "font-mono text-[11px] text-slate-700",
            render: (_val, row) => {
                const id = row.final_category_id || "-";
                const name = row.final_category_name || "";
                const isDefault = Boolean(row.final_category_is_default);
                return (
                    <span title={isDefault ? "Unmapped: default Trade Me category. Next: add/adjust mapping for this source category." : (name ? `${name} (${id})` : String(id))}>
                        {isDefault ? "Unmapped (default)" : (name ? name : id)}
                    </span>
                );
            }
        },
        { key: "last_scraped_at", label: "Last scraped", render: (val) => formatNZT(val as string | null) },
    ];

    return (
        <div className="space-y-6">
            <PageHeader
                title="Vault 1 · Raw"
                subtitle="Supplier products (click a row for full inspector)"
            />
            <FilterChips chips={chips} />

            <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
                <div className="flex flex-col gap-3 border-b border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between">
                    <form className="flex flex-wrap items-center gap-4" method="get" data-testid="search-form">
                        <input type="hidden" name="page" value="1" />
                        <label className="flex flex-col gap-1 text-xs font-medium text-slate-600">
                            <span>Search SKU/Title</span>
                            <input
                                name="q"
                                defaultValue={q}
                                data-testid="inp-search-q"
                                className="w-52 rounded-md border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-900 focus:border-slate-400 focus:outline-none"
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
                            <span>Sync Status</span>
                            <select
                                name="sync_status"
                                defaultValue={syncStatus}
                                data-testid="sel-search-sync"
                                className="w-32 rounded-md border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-900 focus:border-slate-400 focus:outline-none"
                            >
                                <option value="">All</option>
                                <option value="PRESENT">PRESENT</option>
                                <option value="REMOVED">REMOVED</option>
                            </select>
                        </label>
                        <label className="flex flex-col gap-1 text-xs font-medium text-slate-600">
                            <span>Source category</span>
                            <input
                                name="source_category"
                                defaultValue={sourceCategory}
                                data-testid="inp-search-source-category"
                                className="w-56 rounded-md border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-900 focus:border-slate-400 focus:outline-none"
                                placeholder="e.g. all"
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
                                href="/vaults/raw"
                                data-testid="lnk-search-reset"
                            >
                                Reset
                            </Link>
                        </div>
                    </form>

                    <div className="flex items-center gap-3">
                        <button
                            type="button"
                            className={buttonClass({ variant: "outline", disabled: refreshing })}
                            onClick={() => void refreshNow()}
                        >
                            {refreshing ? "Refreshing…" : "Refresh"}
                        </button>
                        <label className={`flex items-center gap-2 text-xs ${isNarrow ? "text-slate-700" : "text-slate-400"}`}>
                            <input
                                type="checkbox"
                                className="h-4 w-4"
                                checked={auto}
                                disabled={!isNarrow}
                                onChange={(e) => setAuto(e.target.checked)}
                            />
                            Auto-refresh
                        </label>
                    </div>
                </div>

                {err ? (
                    <div className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-[11px] text-amber-900">
                        {err}
                    </div>
                ) : null}
                {auto && !isNarrow ? (
                    <div className="border-b border-slate-200 bg-slate-50 px-4 py-2 text-[11px] text-slate-600">
                        Auto-refresh is disabled until you set a filter (Supplier ID, Source category, or search) to avoid heavy polling.
                    </div>
                ) : null}
                {lastRefresh ? (
                    <div className="border-b border-slate-200 bg-slate-50 px-4 py-2 text-[11px] text-slate-600">
                        Last refreshed: {formatNZT(lastRefresh)}
                    </div>
                ) : null}

                <DataTable
                    columns={columns}
                    data={liveItems}
                    totalCount={liveTotal}
                    currentPage={page}
                    pageSize={perPage}
                />
            </div>
        </div>
    );
}
