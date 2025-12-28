import type { ReactNode } from "react";

export interface EmptyStateProps {
    icon?: ReactNode;
    title: string;
    message?: string;
    action?: ReactNode;
}

export function EmptyState({ icon, title, message, action }: EmptyStateProps) {
    return (
        <div
            className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-200 bg-slate-50 px-6 py-12 text-center"
            data-testid="empty-state"
        >
            {icon && <div className="mb-4 text-slate-400" data-testid="empty-icon">{icon}</div>}
            <h3 className="text-sm font-semibold text-slate-900" data-testid="empty-title">{title}</h3>
            {message && <p className="mt-1 text-sm text-slate-600" data-testid="empty-message">{message}</p>}
            {action && <div className="mt-4" data-testid="empty-action">{action}</div>}
        </div>
    );
}
