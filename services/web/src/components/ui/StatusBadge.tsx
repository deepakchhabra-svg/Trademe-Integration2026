import { Badge } from "@/components/ui/badge";

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

type BadgeVariant = "default" | "secondary" | "outline" | "slate" | "emerald" | "red" | "amber" | "blue" | "indigo" | "destructive";

const variantMap: Record<string, BadgeVariant> = {
    SUCCESS: "emerald",
    FAILED: "destructive",
    PRESENT: "emerald",
    REMOVED: "slate",
    HUMAN_REQUIRED: "destructive",
    PENDING: "blue",
    EXECUTING: "indigo",
    LIVE: "emerald",
    DRY_RUN: "amber",
    BLOCKED: "destructive",
    WITHDRAWN: "slate",
    ACTIVE: "emerald",
    ENRICHED: "emerald",
    NOT_ENRICHED: "slate",
};

const statusLabels: Record<string, string> = {
    SUCCESS: "Success",
    FAILED: "Failed",
    PRESENT: "Active",
    REMOVED: "Removed",
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
    REMOVED: "Not present in the latest supplier scrape.",
    DRY_RUN: "Draft listing created for review.",
    HUMAN_REQUIRED: "A human decision is required.",
    FAILED: "The job failed.",
    BLOCKED: "Draft blocked by hard gates.",
};

export function StatusBadge({ status, label, children, className = "" }: StatusBadgeProps) {
    const key = String(status || "").toUpperCase();
    // Default to outline if unknown
    const variant = variantMap[key] || "outline";
    const text = String(label || children || statusLabels[key] || status);
    const tooltip = statusTooltips[key];

    return (
        <Badge variant={variant} className={className} title={tooltip}>
            {text}
        </Badge>
    );
}
