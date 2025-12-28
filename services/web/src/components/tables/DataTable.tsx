"use client";

import { type ReactNode } from "react";
import Link from "next/link";

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
    stickyHeader?: boolean;
    loading?: boolean;
    rowIdKey?: string;
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
    stickyHeader = true,
    loading = false,
    rowIdKey = "id",
}: DataTableProps<T>) {
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
                <p className="text-sm text-slate-600">{emptyMessage}</p>
            </div>
        );
    }

    const totalPages = Math.ceil(totalCount / pageSize);
    const startRow = (currentPage - 1) * pageSize + 1;
    const endRow = Math.min(currentPage * pageSize, totalCount);

    return (
        <div className="space-y-4" data-testid="data-table">
            <div className="text-sm text-slate-600" data-testid="table-pagination-info">
                Showing {startRow}-{endRow} of {totalCount}
            </div>

            <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
                <table className="w-full text-left text-sm">
                    <thead
                        className={`bg-slate-50 text-xs uppercase tracking-wide text-slate-500 ${stickyHeader ? "sticky top-0 z-10" : ""
                            }`}
                    >
                        <tr>
                            {columns.map((column) => (
                                <th key={column.key} className={`px-4 py-3 ${column.className || ""}`}>
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
                                    className="border-t border-slate-100 align-top hover:bg-slate-50"
                                    data-testid={`row-${rowId}`}
                                >
                                    {columns.map((column) => {
                                        const value = row[column.key];
                                        return (
                                            <td
                                                key={column.key}
                                                className={`px-4 py-3 ${column.className || ""}`}
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
        </div>
    );
}
