import Link from "next/link";

import { apiGet } from "./api";
import { RoleSwitcher } from "./RoleSwitcher";
import { NavLink } from "./NavLink";
import { Badge } from "./Badge";
import { ThemeDensityToggles } from "./ThemeDensityToggles";

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
  const backendTone = health.status === "ok" ? "emerald" : health.status === "degraded" ? "amber" : "red";
  const backendLabel = health.status === "ok" ? "Backend: Online" : health.status === "degraded" ? "Backend: Degraded" : "Backend: Offline";

  return (
    <div className="min-h-screen ros-fg">
      <div className="flex min-h-screen">
        <aside className="hidden w-64 flex-col border-r ros-border ros-surface sm:flex">
          <div className="border-b ros-border px-4 py-4">
            <div className="flex items-center justify-between">
              <Link href="/" className="text-sm font-semibold tracking-tight">
                RetailOS
              </Link>
              <span title="Backend API health (Online/Offline).">
                <Badge tone={backendTone}>{backendLabel}</Badge>
              </span>
            </div>
            <div className="mt-2 text-xs ros-muted">
              Access: <span className="font-mono ros-fg">{who.role}</span>
            </div>
          </div>

          <div className="flex-1 space-y-6 px-3 py-4">
            {/* CORE NAVIGATION (5 Items) */}
            <div className="space-y-1">
              <div className="px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Core</div>
              <NavLink href="/ops/summary" label="Dashboard" />
              {canSee(who.role, "power") ? <NavLink href="/pipeline" label="Pipeline" /> : null}
              {canSee(who.role, "power") ? <NavLink href="/ops/bulk" label="Publish Console" /> : null}
              <NavLink href="/vaults/live" label="Live Listings" />
              {canSee(who.role, "power") ? <NavLink href="/ops/inbox" label="Inbox" /> : null}
            </div>

            {/* ADVANCED SECTION */}
            <details className="group space-y-2">
              <summary className="cursor-pointer rounded-md px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50 hover:text-indigo-600 select-none flex items-center gap-2">
                <svg className="h-4 w-4 transition-transform group-open:rotate-90 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
                Advanced
              </summary>

              <div className="pl-4 space-y-6 border-l ml-5 my-2 border-slate-100">
                <div className="space-y-1">
                  <div className="px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-400">Products</div>
                  <NavLink href="/vaults/raw" label="Products (Raw)" />
                  <NavLink href="/vaults/enriched" label="Products (Ready)" />
                  <NavLink href="/products" label="Master View" />
                </div>

                <div className="space-y-1">
                  <div className="px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-400">Ops Details</div>
                  {canSee(who.role, "power") ? <NavLink href="/ops/commands" label="Command Log" /> : null}
                  {canSee(who.role, "power") ? <NavLink href="/ops/alerts" label="Alerts" /> : null}
                  {canSee(who.role, "power") ? <NavLink href="/ops/trademe" label="Trade Me Health" /> : null}
                  {canSee(who.role, "power") ? <NavLink href="/ops/llm" label="LLM Health" /> : null}
                  {canSee(who.role, "power") ? <NavLink href="/ops/readiness" label="Publish Readiness" /> : null}
                  {canSee(who.role, "power") ? <NavLink href="/ops/removed" label="Removed Items" /> : null}
                  {canSee(who.role, "power") ? <NavLink href="/ops/jobs" label="Background Jobs" /> : null}
                </div>

                {canSee(who.role, "root") ? (
                  <div className="space-y-1">
                    <div className="px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-400">Diagnostics</div>
                    <NavLink href="/ops/audits" label="Audit Log" />
                  </div>
                ) : null}

                <div className="space-y-1">
                  <div className="px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-400">Commerce</div>
                  {canSee(who.role, "fulfillment") ? <NavLink href="/orders" label="Orders" /> : null}
                  {canSee(who.role, "fulfillment") ? <NavLink href="/fulfillment" label="Fulfillment" /> : null}
                  <NavLink href="/suppliers" label="Suppliers" />
                </div>

                <div className="space-y-1">
                  <div className="px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-400">External Links</div>
                  <a href="https://www.trademe.co.nz" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50 hover:text-indigo-600 rounded-md">Trade Me Marketplace ↗</a>
                  <a href="https://www.trademe.co.nz/a/my-trade-me" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50 hover:text-indigo-600 rounded-md">My Trade Me ↗</a>
                  <a href="https://www.holidayhouses.co.nz/" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50 hover:text-indigo-600 rounded-md">Holiday Houses ↗</a>
                </div>

                <div className="space-y-1">
                  <div className="px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-400">Admin</div>
                  <NavLink href="/access" label="Access & Tokens" />
                  {canSee(who.role, "root") ? <NavLink href="/admin/settings" label="Settings" /> : null}
                </div>
              </div>
            </details>
          </div>

          <div className="border-t ros-border px-4 py-4 space-y-4">
            <ThemeDensityToggles />
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs ros-muted">Access</div>
              <RoleSwitcher />
            </div>
            <div className="mt-2 text-[11px] ros-muted">
              Use roles to keep day-to-day operation focused.
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

