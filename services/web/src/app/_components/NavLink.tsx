"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";

export function NavLink({
  href,
  label,
}: {
  href: string;
  label: string;
}) {
  const pathname = usePathname() || "";
  // This can differ between server render and client hydration in dev,
  // so we suppress hydration warning on the link element.
  const active = pathname === href || (href !== "/" && pathname.startsWith(href));
  return (
    <Link
      href={href}
      suppressHydrationWarning
      data-testid={`lnk-nav-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
      className={clsx(
        "block rounded-md px-3 py-2 text-sm font-medium",
        active ? "bg-indigo-600 text-white" : "text-slate-700 hover:bg-slate-100",
      )}
    >
      {label}
    </Link>
  );
}

