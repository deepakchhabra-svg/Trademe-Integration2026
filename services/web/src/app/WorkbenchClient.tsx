"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { apiGetClient } from "./_components/api_client";
import { PageHeader } from "../components/ui/PageHeader";
import { SectionCard } from "../components/ui/SectionCard";
import { buttonClass } from "./_components/ui";
import { formatNZT } from "./_components/time";

type OpsSummary = {
  utc?: string;
  commands: { total: number; pending: number; executing: number; human_required: number; failed: number };
  vaults: {
    raw_total: number;
    raw_present: number;
    enriched_total: number;
    enriched_ready: number;
    listings_total: number;
    listings_dry_run: number;
    listings_live: number;
  };
  orders: { total: number; pending_fulfillment: number };
};

type Supplier = { id: number; name: string };
type TradeMeHealth = { configured?: boolean; auth_ok?: boolean; utc?: string; offline?: boolean; error?: string };

export function WorkbenchClient({ initial }: { initial: OpsSummary }) {
  const [summary, setSummary] = useState<OpsSummary>(initial);
  const [refreshing, setRefreshing] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [_suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [tmHealth, setTmHealth] = useState<TradeMeHealth | null>(null);


  useEffect(() => {
    let cancelled = false;
    async function loadSuppliers() {
      try {
        const s = await apiGetClient<Supplier[]>("/suppliers");
        if (cancelled) return;
        setSuppliers(s);
      } catch {
        // ignore; UI can still work with manual IDs
      }
    }
    void loadSuppliers();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function loadTradeMeHealth() {
      try {
        const s = await apiGetClient<TradeMeHealth>("/trademe/account_summary");
        if (cancelled) return;
        setTmHealth(s);
      } catch {
        if (cancelled) return;
        setTmHealth({ configured: false, auth_ok: false, offline: true, error: "Trade Me health unavailable" });
      }
    }
    void loadTradeMeHealth();
    return () => {
      cancelled = true;
    };
  }, []);

  const updatedLabel = useMemo(() => formatNZT(summary.utc), [summary.utc]);

  async function refresh() {
    if (refreshing) return;
    setRefreshing(true);
    setMsg(null);
    try {
      const next = await apiGetClient<OpsSummary>("/ops/summary");
      setSummary(next);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Refresh failed");
    } finally {
      setRefreshing(false);
    }
  }

  const canPublish = Boolean(tmHealth?.configured) && Boolean(tmHealth?.auth_ok) && !Boolean(tmHealth?.offline);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Ops Workbench"
        subtitle="Overview dashboard. Canonical flow: Pipeline → Inbox → Command log."
        actions={
          <div className="flex flex-wrap items-center gap-3">
            <div className="text-xs text-slate-500">
              Updated: <span className="font-mono text-slate-700">{updatedLabel}</span>
            </div>
            <button type="button" className={buttonClass({ variant: "outline", disabled: refreshing })} onClick={refresh}>
              {refreshing ? "Refreshing…" : "Refresh"}
            </button>
            <Link className={buttonClass({ variant: "primary" })} href="/pipeline">
              Open Pipeline
            </Link>
            <Link className={buttonClass({ variant: "outline" })} href="/ops/inbox">
              Inbox
            </Link>
            <Link className={buttonClass({ variant: "outline" })} href="/ops/commands">
              Command log
            </Link>
          </div>
        }
      />

      {msg ? <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-900">{msg}</div> : null}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SectionCard title="Commands" className="h-full">
          <div className="text-sm text-slate-900">
            <Link className="hover:underline" href="/ops/commands?status=ACTIVE">
              queued <span className="font-semibold">{summary.commands.pending}</span> · running{" "}
              <span className="font-semibold">{summary.commands.executing}</span>
            </Link>
          </div>
          <div className="mt-1 text-sm text-slate-900">
            <Link className="hover:underline" href="/ops/commands?status=NEEDS_ATTENTION">
              needs attention <span className="font-semibold">{summary.commands.human_required}</span> · failed{" "}
              <span className="font-semibold">{summary.commands.failed}</span>
            </Link>
          </div>
          <div className="mt-2 flex gap-2">
            <Link className={buttonClass({ variant: "link" })} href="/ops/commands?status=NEEDS_ATTENTION">
              View needs attention →
            </Link>
            <Link className={buttonClass({ variant: "link" })} href="/ops/jobs?status=FAILED">
              Failed jobs →
            </Link>
          </div>
        </SectionCard>

        <SectionCard title="Vaults" className="h-full">
          <div className="text-sm text-slate-900">
            <Link className="hover:underline" href="/vaults/raw">
              raw <span className="font-semibold">{summary.vaults.raw_present}</span>/<span className="font-semibold">{summary.vaults.raw_total}</span>
            </Link>
          </div>
          <div className="mt-1 text-sm text-slate-900">
            <Link className="hover:underline" href="/vaults/enriched?enrichment=Enriched">
              enriched-ready <span className="font-semibold">{summary.vaults.enriched_ready}</span>/<span className="font-semibold">{summary.vaults.enriched_total}</span>
            </Link>
          </div>
        </SectionCard>

        <SectionCard title="Listings" className="h-full">
          <div className="text-sm text-slate-900">
            <Link className="hover:underline" href="/vaults/live?status=DRY_RUN">
              Draft <span className="font-semibold">{summary.vaults.listings_dry_run}</span>
            </Link>
          </div>
          <div className="mt-1 text-sm text-slate-900">
            <Link className="hover:underline" href="/vaults/live?status=Live">
              Live <span className="font-semibold">{summary.vaults.listings_live}</span>
            </Link>
          </div>
        </SectionCard>

        <SectionCard title="Fulfillment" className="h-full">
          <div className="text-sm text-slate-900">
            <Link className="hover:underline" href="/orders?fulfillment_status=PENDING">
              pending orders <span className="font-semibold">{summary.orders.pending_fulfillment}</span>
            </Link>
          </div>
          <div className="mt-2">
            <Link className={buttonClass({ variant: "link" })} href="/orders?fulfillment_status=PENDING">
              View orders →
            </Link>
          </div>
        </SectionCard>
      </div>

      <SectionCard title="Next actions" subtitle="Single canonical flow: Pipeline → Inbox → Command log.">
        <div className="flex flex-wrap items-center gap-2">
          <Link className={buttonClass({ variant: "primary" })} href="/pipeline">
            Open Pipeline
          </Link>
          <Link className={buttonClass({ variant: "outline" })} href="/ops/inbox">
            Inbox
          </Link>
          <Link className={buttonClass({ variant: "outline" })} href="/ops/commands?status=NEEDS_ATTENTION">
            Needs attention
          </Link>
          <Link className={buttonClass({ variant: "outline" })} href="/ops/readiness">
            Publish Readiness
          </Link>
          <Link className={buttonClass({ variant: "outline" })} href="/ops/trademe">
            Trade Me Health
          </Link>
          <Link className={buttonClass({ variant: "outline" })} href="/ops/removed">
            Removed items
          </Link>
          <Link className={buttonClass({ variant: "outline" })} href="/ops/bulk">
            Bulk ops (advanced)
          </Link>
        </div>
        {!canPublish ? (
          <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
            Publishing is gated until Trade Me Health is <span className="font-semibold">configured</span> and <span className="font-semibold">auth ok</span>.
          </div>
        ) : null}
      </SectionCard>
    </div>
  );
}

