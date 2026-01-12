"use client";

import Link from "next/link";
import Image from "next/image";
import { DataTable, ColumnDef } from "../../../components/tables/DataTable";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import { formatNZT } from "../../_components/time";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";

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
    if (raw.startsWith("/media/")) return raw.replace(/^\/media\//, "/api/media/");
    return raw;
}

export function LiveVaultClient({
    items,
    total,
    page,
    perPage,
    q,
    status,
    supplierId,
    sourceCategory
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
    const base = new URLSearchParams();
    if (q) base.set("q", q);
    if (status) base.set("status", status);
    if (supplierId) base.set("supplier_id", supplierId);
    if (sourceCategory) base.set("source_category", sourceCategory);

    // Columns definition
    const columns: ColumnDef<LiveItem>[] = [
        {
            key: "id",
            label: "ID",
            render: (val) => (
                <Link className="text-primary hover:underline font-mono" href={`/vaults/live/${val}`} data-testid={`lnk-id-${val}`}>
                    {val as number}
                </Link>
            )
        },
        {
            key: "thumb",
            label: "Img",
            render: (val, row) => (val as string) ? (
                <Link href={`/vaults/live/${row.id}`} className="block w-10 h-10 relative" data-testid={`lnk-img-${row.id}`}>
                    <Image
                        alt=""
                        src={imgSrc(val as string)}
                        fill
                        unoptimized
                        className="rounded-sm border object-cover"
                    />
                </Link>
            ) : (
                <div className="w-10 h-10 rounded-sm border border-dashed bg-muted" />
            )
        },
        {
            key: "tm_listing_id",
            label: "TM ID",
            className: "font-mono text-xs",
            render: (val) => val ? (
                <a href={`https://www.trademe.co.nz/Browse/Listing.aspx?id=${val}`} target="_blank" className="hover:underline text-blue-600">
                    {val as string}
                </a>
            ) : "-"
        },
        {
            key: "title",
            label: "Title",
            render: (val, row) => (
                <Link className="text-foreground hover:underline font-medium line-clamp-1 max-w-[200px]" href={`/vaults/live/${row.id}`} title={val as string}>
                    {val as string || "-"}
                </Link>
            )
        },
        { key: "actual_state", label: "State", render: (val) => <StatusBadge status={val as string} /> },
        { key: "lifecycle_state", label: "Lifecycle", render: (val) => <StatusBadge status={val as string} /> },
        { key: "actual_price", label: "Price", render: (val) => val == null ? "-" : `$${(val as number).toFixed(2)}` },
        { key: "view_count", label: "Views" },
        { key: "watch_count", label: "Watch" },
        { key: "last_synced_at", label: "Synced", render: (val) => <span className="text-xs text-muted-foreground whitespace-nowrap">{formatNZT(val as string | null)}</span> },
    ];

    return (
        <div className="space-y-6">
            <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Vault Listings</h1>
                    <p className="text-muted-foreground">Live inventory management and audit.</p>
                </div>
                <div className="flex gap-2 text-sm">
                    {status && <Badge variant="secondary" className="flex gap-1">Status: {status} <Link href="?status=" className="ml-1 hover:text-destructive">×</Link></Badge>}
                    {supplierId && <Badge variant="secondary" className="flex gap-1">Supplier: {supplierId} <Link href="?supplier_id=" className="ml-1 hover:text-destructive">×</Link></Badge>}
                </div>
            </div>

            <Card>
                <div className="flex flex-col gap-3 border-b p-4 bg-muted/20">
                    <form className="flex flex-wrap items-end gap-3" method="get" data-testid="search-form">
                        <input type="hidden" name="page" value="1" />
                        <div className="space-y-1">
                            <label className="text-xs font-semibold uppercase text-muted-foreground">Search</label>
                            <div className="relative">
                                <Search className="absolute left-2 top-2.5 h-3 w-3 text-muted-foreground" />
                                <Input
                                    name="q"
                                    defaultValue={q}
                                    className="h-8 w-52 pl-8"
                                    placeholder="Title or TM ID"
                                />
                            </div>
                        </div>
                        <div className="space-y-1">
                            <label className="text-xs font-semibold uppercase text-muted-foreground">Status</label>
                            <select
                                name="status"
                                defaultValue={status}
                                className="h-8 w-32 rounded-md border border-input bg-background px-2 text-xs"
                            >
                                <option value="Live">Live</option>
                                <option value="DRY_RUN">Draft</option>
                                <option value="BLOCKED">Blocked</option>
                                <option value="Withdrawn">Withdrawn</option>
                                <option value="All">All</option>
                            </select>
                        </div>
                        <div className="space-y-1">
                            <label className="text-xs font-semibold uppercase text-muted-foreground">Supplier ID</label>
                            <Input
                                name="supplier_id"
                                defaultValue={supplierId}
                                className="h-8 w-20"
                                placeholder="ID"
                            />
                        </div>

                        <Button type="submit" size="sm" className="h-8">Apply</Button>
                        <Button asChild variant="ghost" size="sm" className="h-8">
                            <Link href="/vaults/live?status=Live">Reset</Link>
                        </Button>
                    </form>
                </div>

                <DataTable
                    columns={columns}
                    data={items}
                    totalCount={total}
                    currentPage={page}
                    pageSize={perPage}
                    emptyState={
                        <div className="text-center py-8">
                            <div className="text-lg font-semibold">No listings match this filter.</div>
                            <div className="mt-2 text-sm text-muted-foreground">
                                Try adjusting your search or filters.
                            </div>
                            <div className="mt-4 flex justify-center gap-2">
                                <Button asChild variant="default">
                                    <Link href="/pipeline">Open Pipeline</Link>
                                </Button>
                                <Button asChild variant="outline">
                                    <Link href="/vaults/live?status=DRY_RUN">View Drafts</Link>
                                </Button>
                            </div>
                        </div>
                    }
                />
            </Card>
        </div>
    );
}
