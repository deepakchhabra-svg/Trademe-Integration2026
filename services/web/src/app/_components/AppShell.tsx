import Link from "next/link";

import { apiGet } from "./api";
import { RoleSwitcher } from "./RoleSwitcher";
import { NavLink } from "./NavLink";
import { Badge } from "./Badge";

type WhoAmI = { role: string; rank: number };
type Health = { status: string; utc: string };

async function getTopStatus(): Promise<{ who: WhoAmI; health: Health }> {
  const [who, health] = await Promise.all([apiGet<WhoAmI>("/whoami"), apiGet<Health>("/health")]);
  return { who, health };
}

function canSee(role: string, min: "listing" | "fulfillment" | "power" | "root"): boolean {
  const rank: Record<string, number> = { listing: 10, fulfillment: 20, power: 80, root: 100 };
  return (rank[role] ?? 0) >= (rank[min] ?? 0);
}

export default async function AppShell({ children }: { children: React.ReactNode }) {
  const { who, health } = await getTopStatus();

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="flex min-h-screen">
        <aside className="hidden w-64 flex-col border-r border-slate-200 bg-white sm:flex">
          <div className="flex items-center justify-between border-b border-slate-200 px-4 py-4">
            <Link href="/" className="text-sm font-semibold tracking-tight">
              RetailOS Admin
            </Link>
            <Badge tone={health.status === "ok" ? "emerald" : "red"}>API {health.status}</Badge>
          </div>

          <div className="flex-1 space-y-6 px-3 py-4">
            <div className="space-y-1">
              <div className="px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Vaults
              </div>
              <NavLink href="/vaults/raw" label="Vault 1 · Raw" />
              <NavLink href="/vaults/enriched" label="Vault 2 · Enriched" />
              <NavLink href="/vaults/live" label="Vault 3 · Listings" />
            </div>

            <div className="space-y-1">
              <div className="px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Ops
              </div>
              {canSee(who.role, "power") ? <NavLink href="/ops/inbox" label="Inbox" /> : null}
              {canSee(who.role, "power") ? <NavLink href="/ops/alerts" label="Alerts" /> : null}
              {canSee(who.role, "power") ? <NavLink href="/ops/trademe" label="Trade Me Health" /> : null}
              {canSee(who.role, "power") ? <NavLink href="/ops/bulk" label="Bulk Ops" /> : null}
              <NavLink href="/ops/commands" label="Commands" />
              {canSee(who.role, "power") ? <NavLink href="/ops/jobs" label="Jobs" /> : null}
              {canSee(who.role, "power") ? <NavLink href="/ops/audits" label="Audits" /> : null}
            </div>

            <div className="space-y-1">
              <div className="px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Commerce
              </div>
              {canSee(who.role, "fulfillment") ? <NavLink href="/orders" label="Orders" /> : null}
              <NavLink href="/suppliers" label="Suppliers" />
            </div>

            <div className="space-y-1">
              <div className="px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Admin
              </div>
              {canSee(who.role, "root") ? <NavLink href="/admin/settings" label="Settings" /> : null}
            </div>
          </div>

          <div className="border-t border-slate-200 px-4 py-4">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs text-slate-600">
                Role: <span className="font-mono text-slate-900">{who.role}</span>
              </div>
              <RoleSwitcher />
            </div>
            <div className="mt-2 text-[11px] text-slate-500">
              Use RBAC to keep normal users focused.
            </div>
          </div>
        </aside>

        <main className="flex-1">
          <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">{children}</div>
        </main>
      </div>
    </div>
  );
}

