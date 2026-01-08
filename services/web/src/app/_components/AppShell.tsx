import Link from "next/link";

import { apiGet } from "./api";
import { RoleSwitcher } from "./RoleSwitcher";
import { NavItem } from "./NavItem";
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
              <div className="px-3 py-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Core</div>
              <NavItem href="/ops/summary" label="Dashboard" />
              {canSee(who.role, "power") ? <NavItem href="/pipeline" label="Pipeline" /> : null}
              {canSee(who.role, "power") ? <NavItem href="/ops/bulk" label="Publish Console" /> : null}
              <NavItem href="/vaults/live" label="Live Listings" />
              {canSee(who.role, "power") ? <NavItem href="/ops/inbox" label="Inbox" /> : null}
            </div>

            {/* ADVANCED SECTION */}
            <details className="group space-y-1 border-t pt-2 mt-2">
              <summary className="cursor-pointer rounded-md px-3 py-2 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground select-none flex items-center gap-2 outline-none">
                <svg className="h-4 w-4 transition-transform group-open:rotate-90 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
                Advanced
              </summary>

              <div className="space-y-6 mt-2">
                <div className="space-y-1">
                  <div className="px-3 py-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground pl-8">Products</div>
                  <NavItem href="/vaults/raw" label="Products (Raw)" indent />
                  <NavItem href="/vaults/enriched" label="Products (Ready)" indent />
                  <NavItem href="/products" label="Master View" indent />
                </div>

                <div className="space-y-1">
                  <div className="px-3 py-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground pl-8">Ops Details</div>
                  {canSee(who.role, "power") ? <NavItem href="/ops/commands" label="Command Log" indent /> : null}
                  {canSee(who.role, "power") ? <NavItem href="/ops/alerts" label="Alerts" indent /> : null}
                  {canSee(who.role, "power") ? <NavItem href="/ops/trademe" label="Trade Me Health" indent /> : null}
                  {canSee(who.role, "power") ? <NavItem href="/ops/llm" label="LLM Health" indent /> : null}
                  {canSee(who.role, "power") ? <NavItem href="/ops/readiness" label="Publish Readiness" indent /> : null}
                  {canSee(who.role, "power") ? <NavItem href="/ops/removed" label="Removed Items" indent /> : null}
                  {canSee(who.role, "power") ? <NavItem href="/ops/jobs" label="Background Jobs" indent /> : null}
                </div>

                {canSee(who.role, "root") ? (
                  <div className="space-y-1">
                    <div className="px-3 py-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground pl-8">Diagnostics</div>
                    <NavItem href="/ops/audits" label="Audit Log" indent />
                  </div>
                ) : null}

                <div className="space-y-1">
                  <div className="px-3 py-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground pl-8">Commerce</div>
                  {canSee(who.role, "fulfillment") ? <NavItem href="/orders" label="Orders" indent /> : null}
                  {canSee(who.role, "fulfillment") ? <NavItem href="/fulfillment" label="Fulfillment" indent /> : null}
                  <NavItem href="/suppliers" label="Suppliers" indent />
                </div>

                <div className="space-y-1">
                  <div className="px-3 py-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground pl-8">External Links</div>
                  <NavItem href="https://www.trademe.co.nz" label="Trade Me Marketplace" indent target="_blank" />
                  <NavItem href="https://www.trademe.co.nz/a/my-trade-me" label="My Trade Me" indent target="_blank" />
                  <NavItem href="https://www.holidayhouses.co.nz/" label="Holiday Houses" indent target="_blank" />
                </div>

                <div className="space-y-1">
                  <div className="px-3 py-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground pl-8">Admin</div>
                  <NavItem href="/access" label="Access & Tokens" indent />
                  {canSee(who.role, "root") ? <NavItem href="/admin/settings" label="Settings" indent /> : null}
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

