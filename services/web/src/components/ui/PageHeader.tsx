import type { ReactNode } from "react";

export interface PageHeaderProps {
    title: string;
    subtitle?: ReactNode;
    actions?: ReactNode;
    breadcrumbs?: ReactNode;
}

export function PageHeader({ title, subtitle, actions, breadcrumbs }: PageHeaderProps) {
    return (
        <div
            className="space-y-3"
            data-testid={`page-header-${title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
        >
            {breadcrumbs && <div data-testid="page-breadcrumbs">{breadcrumbs}</div>}
            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div>
                    <h1 className="text-xl font-semibold tracking-tight text-slate-900" data-testid="page-title">{title}</h1>
                    {subtitle && (
                        <div className="mt-1 text-sm text-slate-600" data-testid="page-subtitle">
                            {subtitle}
                        </div>
                    )}
                </div>
                {actions && <div className="flex flex-wrap gap-2" data-testid="page-actions">{actions}</div>}
            </div>
        </div>
    );
}
