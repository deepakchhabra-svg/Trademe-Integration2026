"use client";

import { type ReactNode } from "react";
import Link from "next/link";
import { useUISettings } from "../../app/_components/UISettingsProvider";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react";

export interface ColumnDef<T> {
    key: string;
    label: string;
    sortable?: boolean;
    render?: (value: unknown, row: T) => ReactNode;
    className?: string;
}

export interface DataTableProps<T> {
    columns: ColumnDef<T>[];
    data: T[];
    totalCount: number;
    currentPage: number;
    pageSize: number;
    sortColumn?: string;
    sortDirection?: "asc" | "desc";
    onSort?: (column: string) => void;
    emptyMessage?: string;
    emptyState?: ReactNode;
    stickyHeader?: boolean;
    loading?: boolean;
    rowIdKey?: string;
    density?: "compact" | "comfortable";
}

export function DataTable<T extends Record<string, unknown>>({
    columns,
    data,
    totalCount,
    currentPage,
    pageSize,
    sortColumn,
    sortDirection,
    onSort,
    emptyMessage = "No data available",
    emptyState,
    stickyHeader = true,
    loading = false,
    rowIdKey = "id",
    density,
}: DataTableProps<T>) {
    const { density: uiDensity } = useUISettings();
    const _effectiveDensity = density ?? uiDensity ?? "compact";
    void _effectiveDensity; // Reserved for future use

    if (loading) {
        return (
            <div className="space-y-2 animate-pulse">
                <div className="h-10 bg-muted rounded w-full" />
                <div className="h-10 bg-muted/50 rounded w-full" />
                <div className="h-10 bg-muted/50 rounded w-full" />
            </div>
        );
    }

    if (data.length === 0) {
        return (
            <div className="flex items-center justify-center rounded-md border border-dashed border-muted bg-muted/10 py-12 text-center text-sm text-muted-foreground">
                {emptyState || emptyMessage}
            </div>
        );
    }

    const totalPages = Math.ceil(totalCount / pageSize);
    const startRow = (currentPage - 1) * pageSize + 1;
    const endRow = Math.min(currentPage * pageSize, totalCount);

    return (
        <div className="space-y-4">
            <div className="text-sm text-muted-foreground">
                Showing {startRow}-{endRow} of {totalCount}
            </div>

            <div className="rounded-md border">
                <Table>
                    <TableHeader className={stickyHeader ? "sticky top-0 bg-background z-10" : ""}>
                        <TableRow>
                            {columns.map((column) => (
                                <TableHead key={column.key} className={column.className}>
                                    {column.sortable && onSort ? (
                                        <button
                                            type="button"
                                            onClick={() => onSort(column.key)}
                                            className="flex items-center gap-1 hover:text-foreground font-medium"
                                        >
                                            {column.label}
                                            {sortColumn === column.key && (
                                                <span className="text-muted-foreground">
                                                    {sortDirection === "asc" ? "↑" : "↓"}
                                                </span>
                                            )}
                                        </button>
                                    ) : (
                                        column.label
                                    )}
                                </TableHead>
                            ))}
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {data.map((row, rowIndex) => {
                            const rowId = String(row[rowIdKey] || rowIndex);
                            return (
                                <TableRow key={rowId}>
                                    {columns.map((column) => (
                                        <TableCell key={column.key} className={column.className}>
                                            {column.render ? column.render(row[column.key], row) : String(row[column.key] ?? "-")}
                                        </TableCell>
                                    ))}
                                </TableRow>
                            );
                        })}
                    </TableBody>
                </Table>
            </div>

            {totalPages > 1 && (
                <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                        <Button
                            variant="outline"
                            size="icon"
                            asChild
                            disabled={currentPage <= 1}
                        >
                            <Link href={`?page=1`}>
                                <ChevronsLeft className="h-4 w-4" />
                            </Link>
                        </Button>
                        <Button
                            variant="outline"
                            size="icon"
                            asChild
                            disabled={currentPage <= 1}
                        >
                            <Link href={`?page=${Math.max(1, currentPage - 1)}`}>
                                <ChevronLeft className="h-4 w-4" />
                            </Link>
                        </Button>
                    </div>

                    <div className="text-sm font-medium">
                        Page {currentPage} of {totalPages}
                    </div>

                    <div className="flex items-center space-x-2">
                        <Button
                            variant="outline"
                            size="icon"
                            asChild
                            disabled={currentPage >= totalPages}
                        >
                            <Link href={`?page=${Math.min(totalPages, currentPage + 1)}`}>
                                <ChevronRight className="h-4 w-4" />
                            </Link>
                        </Button>
                        <Button
                            variant="outline"
                            size="icon"
                            asChild
                            disabled={currentPage >= totalPages}
                        >
                            <Link href={`?page=${totalPages}`}>
                                <ChevronsRight className="h-4 w-4" />
                            </Link>
                        </Button>
                    </div>
                </div>
            )}
        </div>
    );
}
