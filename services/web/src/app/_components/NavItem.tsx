"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";

type NavItemProps = {
    href: string;
    label: string;
    indent?: boolean;
    target?: string;
};

export function NavItem({ href, label, indent, target }: NavItemProps) {
    const pathname = usePathname() || "";
    const isExternal = target === "_blank";

    // Active state logic: Exact match OR prefix match for nested routes (e.g. /vaults/raw -> /vaults/raw/123)
    // Ensure we don't match partial words by checking for boundary (end of string or next char is /)
    // For simplicity based on user request: pathname === href OR pathname.startsWith(href + "/")
    const isActive = !isExternal && (pathname === href || pathname.startsWith(href + "/"));

    const baseClasses = "block rounded-md text-sm font-medium transition-colors whitespace-nowrap";
    const paddingClasses = indent ? "pl-10 pr-3 py-2" : "px-3 py-2";

    const stateClasses = isActive
        ? "bg-primary text-primary-foreground"
        : "text-muted-foreground hover:bg-muted hover:text-foreground";

    const className = clsx(baseClasses, paddingClasses, stateClasses);

    if (isExternal) {
        return (
            <a
                href={href}
                target="_blank"
                rel="noreferrer noopener"
                className={className}
            >
                {label}
                <span className="ml-1 opacity-70">↗</span>
            </a>
        );
    }

    return (
        <Link
            href={href}
            suppressHydrationWarning
            data-testid={`lnk-nav-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
            className={className}
        >
            {label}
        </Link>
    );
}
