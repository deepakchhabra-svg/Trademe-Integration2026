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
    | "BLOCKED"
    | "WITHDRAWN"
    | "ACTIVE"
    | "ENRICHED"
    | "NOT_ENRICHED";

export interface StatusBadgeProps {
    status: StatusType | string;
    label?: string;
    children?: React.ReactNode;
    className?: string;
}

const statusColors: Record<string, string> = {
    SUCCESS: "bg-emerald-100 text-emerald-800 border-emerald-200",
    FAILED: "bg-red-100 text-red-800 border-red-200",
    PRESENT: "bg-emerald-100 text-emerald-800 border-emerald-200",
    REMOVED: "bg-slate-100 text-slate-700 border-slate-200",
    HUMAN_REQUIRED: "bg-amber-100 text-amber-800 border-amber-200",
    PENDING: "bg-blue-100 text-blue-800 border-blue-200",
    EXECUTING: "bg-purple-100 text-purple-800 border-purple-200",
    LIVE: "bg-emerald-100 text-emerald-800 border-emerald-200",
    DRY_RUN: "bg-amber-100 text-amber-800 border-amber-200",
    BLOCKED: "bg-red-100 text-red-800 border-red-200",
    WITHDRAWN: "bg-slate-100 text-slate-600 border-slate-200",
    ACTIVE: "bg-emerald-100 text-emerald-800 border-emerald-200",
    ENRICHED: "bg-emerald-100 text-emerald-800 border-emerald-200",
    NOT_ENRICHED: "bg-slate-100 text-slate-600 border-slate-200",
};

const statusLabels: Record<string, string> = {
    SUCCESS: "Success",
    FAILED: "Failed",
    PRESENT: "Active",
    REMOVED: "Removed from source",
    HUMAN_REQUIRED: "Needs attention",
    PENDING: "Queued",
    EXECUTING: "Running",
    LIVE: "Live",
    DRY_RUN: "Draft",
    BLOCKED: "Blocked",
    WITHDRAWN: "Withdrawn",
    ACTIVE: "Active",
    ENRICHED: "Enriched",
    NOT_ENRICHED: "Not enriched",
};

const statusTooltips: Record<string, string> = {
    REMOVED: "Not present in the latest supplier scrape. Kept for audit/history, excluded from default views.",
    DRY_RUN: "Draft listing created for review. Nothing has been published to Trade Me yet.",
    HUMAN_REQUIRED: "A human decision or fix is required before the system can continue.",
    FAILED: "The job failed. Check Jobs/Inbox for the error and recommended action.",
    BLOCKED: "Draft created but blocked by hard gates. Open the listing to see the top blocker + full checklist.",
};

export function StatusBadge({ status, label, children, className = "" }: StatusBadgeProps) {
    const key = String(status || "").toUpperCase();
    const colorClass = statusColors[key] || "bg-slate-100 text-slate-700 border-slate-200";
    const text = String(label || children || statusLabels[key] || status);
    const tooltip = statusTooltips[key];

    return (
        <span
            className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${colorClass} ${className}`}
            data-testid={`badge-status-${String(status).toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
            title={tooltip}
        >
            {text}
        </span>
    );
}
