import type { ReactNode } from "react";

export interface SectionCardProps {
    title?: string;
    children: ReactNode;
    actions?: ReactNode;
    className?: string;
}

export function SectionCard({ title, children, actions, className = "" }: SectionCardProps) {
    return (
        <div className={`rounded-xl border border-slate-200 bg-white shadow-sm ${className}`}>
            {title && (
                <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
                    <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
                    {actions && <div className="flex gap-2">{actions}</div>}
                </div>
            )}
            <div className="p-5">{children}</div>
        </div>
    );
}
