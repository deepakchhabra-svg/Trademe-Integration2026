"use client";

import { type ReactNode } from "react";
import Link from "next/link";
import { useUISettings } from "../../app/_components/UISettingsProvider";

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
    const effectiveDensity = density ?? uiDensity ?? "compact";
    if (loading) {
        return (
            <div className="animate-pulse space-y-2" data-testid="table-loading">
                {Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="h-12 rounded bg-slate-100" />
                ))}
            </div>
        );
    }

    if (data.length === 0) {
        return (
            <div
                className="flex items-center justify-center rounded-xl border-2 border-dashed border-slate-200 bg-slate-50 py-12"
                data-testid="table-empty"
            >
                {emptyState ? <div className="px-6">{emptyState}</div> : <p className="text-sm text-slate-600">{emptyMessage}</p>}
            </div>
        );
    }

    const totalPages = Math.ceil(totalCount / pageSize);
    const startRow = (currentPage - 1) * pageSize + 1;
    const endRow = Math.min(currentPage * pageSize, totalCount);

    const thPad = effectiveDensity === "comfortable" ? "px-4 py-3" : "px-3 py-2";
    const tdPad = effectiveDensity === "comfortable" ? "px-4 py-3" : "px-3 py-2";

    return (
        <div className="space-y-4" data-testid="data-table">
            <div className="text-sm text-slate-600" data-testid="table-pagination-info">
                Showing {startRow}-{endRow} of {totalCount}
            </div>

            <div className="overflow-x-auto rounded-xl border ros-border ros-surface ros-shadow">
                <table className="w-full border-collapse text-left text-sm tabular-nums">
                    <thead
                        className={`ros-surface-strong text-[11px] uppercase tracking-wide ros-muted ${stickyHeader ? "sticky top-0 z-10 shadow-sm" : ""
                            }`}
                    >
                        <tr>
                            {columns.map((column) => (
                                <th key={column.key} className={`${thPad} border-b ros-border ${column.className || ""}`}>
                                    {column.sortable && onSort ? (
                                        <button
                                            type="button"
                                            onClick={() => onSort(column.key)}
                                            className="flex items-center gap-1 hover:text-slate-700"
                                            data-testid={`col-sort-${column.key}`}
                                        >
                                            {column.label}
                                            {sortColumn === column.key && (
                                                <span className="text-slate-400">
                                                    {sortDirection === "asc" ? "↑" : "↓"}
                                                </span>
                                            )}
                                        </button>
                                    ) : (
                                        <span data-testid={`col-label-${column.key}`}>{column.label}</span>
                                    )}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {data.map((row, rowIndex) => {
                            const rowId = row[rowIdKey] || rowIndex;
                            return (
                                <tr
                                    key={rowIndex}
                                    className="align-top odd:bg-white even:bg-slate-50/40 hover:bg-indigo-50/40"
                                    data-testid={`row-${rowId}`}
                                >
                                    {columns.map((column) => {
                                        const value = row[column.key];
                                        return (
                                            <td
                                                key={column.key}
                                                className={`${tdPad} border-t ros-border ${column.className || ""}`}
                                                data-testid={`cell-${rowId}-${column.key}`}
                                            >
                                                {column.render ? column.render(value, row) : String(value ?? "-")}
                                            </td>
                                        );
                                    })}
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>

            {totalPages > 1 ? (
                <div className="flex items-center justify-between text-sm" data-testid="table-pagination-controls">
                    <div className="flex gap-2">
                        <Link
                            href="?page=1"
                            data-testid="pagination-first"
                            className={`rounded-md border px-3 py-1.5 ${currentPage === 1
                                ? "cursor-not-allowed border-slate-200 bg-slate-50 text-slate-400"
                                : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                                }`}
                            aria-disabled={currentPage === 1}
                        >
                            First
                        </Link>
                        <Link
                            href={`?page=${Math.max(1, currentPage - 1)}`}
                            data-testid="pagination-prev"
                            className={`rounded-md border px-3 py-1.5 ${currentPage === 1
                                ? "cursor-not-allowed border-slate-200 bg-slate-50 text-slate-400"
                                : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                                }`}
                            aria-disabled={currentPage === 1}
                        >
                            Prev
                        </Link>
                    </div>

                    <div className="text-xs text-slate-600" data-testid="pagination-current">
                        Page {currentPage} of {totalPages}
                    </div>

                    <div className="flex gap-2">
                        <Link
                            href={`?page=${Math.min(totalPages, currentPage + 1)}`}
                            data-testid="pagination-next"
                            className={`rounded-md border px-3 py-1.5 ${currentPage === totalPages
                                ? "cursor-not-allowed border-slate-200 bg-slate-50 text-slate-400"
                                : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                                }`}
                            aria-disabled={currentPage === totalPages}
                        >
                            Next
                        </Link>
                        <Link
                            href={`?page=${totalPages}`}
                            data-testid="pagination-last"
                            className={`rounded-md border px-3 py-1.5 ${currentPage === totalPages
                                ? "cursor-not-allowed border-slate-200 bg-slate-50 text-slate-400"
                                : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                                }`}
                            aria-disabled={currentPage === totalPages}
                        >
                            Last
                        </Link>
                    </div>
                </div>
            ) : null}
        </div>
    );
}
