import type { ReactNode } from "react";

export interface SectionCardProps {
    title?: string;
    subtitle?: ReactNode;
    children: ReactNode;
    actions?: ReactNode;
    className?: string;
}

export function SectionCard({ title, subtitle, children, actions, className = "" }: SectionCardProps) {
    return (
        <div
            className={`rounded-xl border ros-border ros-surface ros-shadow ros-shadow-hover transition-shadow ${className}`}
            data-testid={title ? `section-card-${title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}` : "section-card"}
        >
            {title && (
                <div className="flex items-center justify-between border-b ros-border px-5 py-4">
                    <div>
                        <h2 className="text-sm font-semibold ros-fg" data-testid="section-title">{title}</h2>
                        {subtitle && <div className="mt-0.5 text-xs ros-muted" data-testid="section-subtitle">{subtitle}</div>}
                    </div>
                    {actions && <div className="flex gap-2" data-testid="section-actions">{actions}</div>}
                </div>
            )}
            <div className="p-5" data-testid="section-content">{children}</div>
        </div>
    );
}
