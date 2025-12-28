export type StatusType =
    | "SUCCESS"
    | "FAILED"
    | "PRESENT"
    | "REMOVED"
    | "HUMAN_REQUIRED"
    | "PENDING"
    | "EXECUTING"
    | "LIVE"
    | "DRY_RUN"
    | "WITHDRAWN"
    | "ACTIVE"
    | "ENRICHED"
    | "NOT_ENRICHED";

export interface StatusBadgeProps {
    status: StatusType | string;
    className?: string;
}

const statusColors: Record<string, string> = {
    SUCCESS: "bg-emerald-100 text-emerald-800 border-emerald-200",
    FAILED: "bg-red-100 text-red-800 border-red-200",
    PRESENT: "bg-emerald-100 text-emerald-800 border-emerald-200",
    REMOVED: "bg-slate-100 text-slate-600 border-slate-200",
    HUMAN_REQUIRED: "bg-amber-100 text-amber-800 border-amber-200",
    PENDING: "bg-blue-100 text-blue-800 border-blue-200",
    EXECUTING: "bg-purple-100 text-purple-800 border-purple-200",
    LIVE: "bg-emerald-100 text-emerald-800 border-emerald-200",
    DRY_RUN: "bg-amber-100 text-amber-800 border-amber-200",
    WITHDRAWN: "bg-slate-100 text-slate-600 border-slate-200",
    ACTIVE: "bg-emerald-100 text-emerald-800 border-emerald-200",
    ENRICHED: "bg-emerald-100 text-emerald-800 border-emerald-200",
    NOT_ENRICHED: "bg-slate-100 text-slate-600 border-slate-200",
};

export function StatusBadge({ status, className = "" }: StatusBadgeProps) {
    const colorClass = statusColors[status.toUpperCase()] || "bg-slate-100 text-slate-600 border-slate-200";

    return (
        <span
            className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${colorClass} ${className}`}
            data-testid={`badge-status-${status.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
        >
            {status}
        </span>
    );
}
