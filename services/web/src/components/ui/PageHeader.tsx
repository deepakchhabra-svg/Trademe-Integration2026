import type { ReactNode } from "react";

export interface PageHeaderProps {
    title: string;
    subtitle?: string;
    actions?: ReactNode;
}

export function PageHeader({ title, subtitle, actions }: PageHeaderProps) {
    return (
        <div
            className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between"
            data-testid={`page-header-${title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
        >
            <div>
                <h1 className="text-xl font-semibold tracking-tight text-slate-900" data-testid="page-title">{title}</h1>
                {subtitle && <p className="mt-1 text-sm text-slate-600">{subtitle}</p>}
            </div>
            {actions && <div className="flex flex-wrap gap-2" data-testid="page-actions">{actions}</div>}
        </div>
    );
}
