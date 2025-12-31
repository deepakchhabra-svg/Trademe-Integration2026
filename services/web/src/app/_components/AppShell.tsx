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
            <div className="space-y-1">
              <div className="px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Workbench</div>
              <NavLink href="/" label="Ops Workbench" />
            </div>

            <div className="space-y-1">
              <div className="px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Products
              </div>
              <NavLink href="/products" label="Master product view" />
            </div>

            <div className="space-y-1">
              <div className="px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Vaults
              </div>
              <NavLink href="/vaults/raw" label="Vault 1 · Supplier data" />
              <NavLink href="/vaults/enriched" label="Vault 2 · Enriched products" />
              <NavLink href="/vaults/live" label="Vault 3 · Listings" />
            </div>

            <div className="space-y-1">
              <div className="px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Ops
              </div>
              {canSee(who.role, "power") ? <NavLink href="/ops/inbox" label="Inbox" /> : null}
              {canSee(who.role, "power") ? <NavLink href="/ops/queue" label="Queue" /> : null}
              {canSee(who.role, "power") ? <NavLink href="/ops/alerts" label="Alerts" /> : null}
              {canSee(who.role, "power") ? <NavLink href="/ops/trademe" label="Trade Me Health" /> : null}
              {canSee(who.role, "power") ? <NavLink href="/ops/llm" label="LLM Health" /> : null}
              {canSee(who.role, "power") ? <NavLink href="/ops/readiness" label="Publish Readiness" /> : null}
              {canSee(who.role, "power") ? <NavLink href="/pipeline" label="Pipeline" /> : null}
              {canSee(who.role, "power") ? <NavLink href="/ops/removed" label="Removed items" /> : null}
              {canSee(who.role, "power") ? <NavLink href="/ops/bulk" label="Runbook" /> : null}
              {canSee(who.role, "power") ? <NavLink href="/ops/jobs" label="Jobs" /> : null}
            </div>

            {canSee(who.role, "root") ? (
              <div className="space-y-1">
                <div className="px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Diagnostics</div>
                <NavLink href="/ops/commands" label="Command log" />
                <NavLink href="/ops/audits" label="Audit log" />
              </div>
            ) : null}

            <div className="space-y-1">
              <div className="px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Commerce
              </div>
              {canSee(who.role, "fulfillment") ? <NavLink href="/orders" label="Orders" /> : null}
              {canSee(who.role, "fulfillment") ? <NavLink href="/fulfillment" label="Fulfillment" /> : null}
              <NavLink href="/suppliers" label="Suppliers" />
            </div>

            <div className="space-y-1">
              <div className="px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Admin
              </div>
              <NavLink href="/access" label="Access & tokens" />
              {canSee(who.role, "root") ? <NavLink href="/admin/settings" label="Settings" /> : null}
            </div>
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

