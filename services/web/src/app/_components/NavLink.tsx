"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import { useEffect, useState } from "react";

export function NavLink({
  href,
  label,
}: {
  href: string;
  label: string;
}) {
  // Avoid SSR/CSR hydration mismatch: render inactive on first pass,
  // then compute active state after mount.
  const pathname = usePathname();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const active = mounted ? pathname === href || (href !== "/" && pathname?.startsWith(href)) : false;
  return (
    <Link
      href={href}
      className={clsx(
        "block rounded-md px-3 py-2 text-sm",
        active ? "bg-slate-900 text-white" : "text-slate-700 hover:bg-slate-100",
      )}
    >
      {label}
    </Link>
  );
}

