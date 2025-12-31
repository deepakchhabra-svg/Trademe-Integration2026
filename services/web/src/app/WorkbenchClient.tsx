"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { apiGetClient, apiPostClient } from "./_components/api_client";
import { PageHeader } from "../components/ui/PageHeader";
import { SectionCard } from "../components/ui/SectionCard";
import { StatusBadge } from "../components/ui/StatusBadge";
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

async function enqueue(type: string, payload: Record<string, unknown>, priority = 60): Promise<{ id: string }> {
  return await apiPostClient<{ id: string }>("/ops/enqueue", { type, payload, priority });
}

export function WorkbenchClient({ initial }: { initial: OpsSummary }) {
  const [summary, setSummary] = useState<OpsSummary>(initial);
  const [refreshing, setRefreshing] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [tmHealth, setTmHealth] = useState<TradeMeHealth | null>(null);

  // Runbook inputs
  const [supplierId, setSupplierId] = useState<string>("");
  const [supplierName, setSupplierName] = useState<string>("");
  const [sourceCategory, setSourceCategory] = useState<string>("");
  const [pages, setPages] = useState<string>("1");
  const [batchSize, setBatchSize] = useState<string>("25");
  const [draftLimit, setDraftLimit] = useState<string>("10");
  const [publishLimit, setPublishLimit] = useState<string>("10");

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

  async function runStep(name: string, fn: () => Promise<string>) {
    setMsg(`Working: ${name}…`);
    try {
      const out = await fn();
      setMsg(out);
      await refresh();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Action failed");
    }
  }

  const supplierParam = supplierId ? `supplier_id=${encodeURIComponent(supplierId)}` : "";
  const sourceCatParam = sourceCategory ? `source_category=${encodeURIComponent(sourceCategory)}` : "";
  const canPublish = Boolean(tmHealth?.configured) && Boolean(tmHealth?.auth_ok) && !Boolean(tmHealth?.offline);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Ops Workbench"
        subtitle="What is this? Your daily operator console. What changed? Use refresh. What’s next? Follow the runbook below."
        actions={
          <div className="flex flex-wrap items-center gap-3">
            <div className="text-xs text-slate-500">
              Updated: <span className="font-mono text-slate-700">{updatedLabel}</span>
            </div>
            <button type="button" className={buttonClass({ variant: "outline", disabled: refreshing })} onClick={refresh}>
              {refreshing ? "Refreshing…" : "Refresh"}
            </button>
            <Link className={buttonClass({ variant: "primary" })} href="/ops/bulk">
              Runbook (advanced)
            </Link>
            <Link className={buttonClass({ variant: "outline" })} href="/ops/inbox">
              Inbox
            </Link>
          </div>
        }
      />

      {msg ? <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-900">{msg}</div> : null}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SectionCard title="Queue" className="h-full">
          <div className="text-sm text-slate-900">
            <Link className="hover:underline" href="/ops/queue?view=active">
              queued <span className="font-semibold">{summary.commands.pending}</span> · running{" "}
              <span className="font-semibold">{summary.commands.executing}</span>
            </Link>
          </div>
          <div className="mt-1 text-sm text-slate-900">
            <Link className="hover:underline" href="/ops/queue?view=attention">
              needs attention <span className="font-semibold">{summary.commands.human_required}</span> · failed{" "}
              <span className="font-semibold">{summary.commands.failed}</span>
            </Link>
          </div>
          <div className="mt-2 flex gap-2">
            <Link className={buttonClass({ variant: "link" })} href="/ops/queue?view=attention">
              View queue →
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

      <SectionCard
        title="Runbook: Scrape → Enrich → Draft → Publish"
        subtitle="A new operator should be able to run ONECHEQ end-to-end without guessing."
      >
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="text-sm font-semibold">Required inputs</div>
            <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
              <label className="text-xs text-slate-600">
                <div className="mb-1 font-semibold uppercase tracking-wide">Supplier</div>
                <select
                  className="w-full rounded-md border border-slate-200 bg-white px-2 py-2 text-sm text-slate-900"
                  value={supplierId && supplierName ? `${supplierId}:${supplierName}` : ""}
                  onChange={(e) => {
                    const v = e.target.value;
                    if (!v) {
                      setSupplierId("");
                      setSupplierName("");
                      return;
                    }
                    const [id, name] = v.split(":");
                    setSupplierId(id);
                    setSupplierName(name);
                  }}
                >
                  <option value="">Select supplier…</option>
                  {suppliers.map((s) => (
                    // Noel Leeming is blocked; do not offer it as a supported option.
                    s.name !== "NOEL_LEEMING" ? (
                      <option key={s.id} value={`${s.id}:${s.name}`}>
                        {s.name} (id {s.id})
                      </option>
                    ) : null
                  ))}
                </select>
              </label>

              <label className="text-xs text-slate-600">
                <div className="mb-1 font-semibold uppercase tracking-wide">Source category</div>
                <input
                  className="w-full rounded-md border border-slate-200 bg-white px-2 py-2 text-sm text-slate-900"
                  value={sourceCategory}
                  onChange={(e) => setSourceCategory(e.target.value)}
                  placeholder="e.g. all"
                />
              </label>

              <label className="text-xs text-slate-600">
                <div className="mb-1 font-semibold uppercase tracking-wide">Pages</div>
                <input className="w-full rounded-md border border-slate-200 bg-white px-2 py-2 text-sm text-slate-900" value={pages} onChange={(e) => setPages(e.target.value)} />
              </label>

              <label className="text-xs text-slate-600">
                <div className="mb-1 font-semibold uppercase tracking-wide">Batch size (enrich)</div>
                <input className="w-full rounded-md border border-slate-200 bg-white px-2 py-2 text-sm text-slate-900" value={batchSize} onChange={(e) => setBatchSize(e.target.value)} />
              </label>
            </div>
            <div className="mt-3 text-[11px] text-slate-500">
              Tip: start with pages=1, draftLimit=10 to validate end-to-end safely.
            </div>
          </div>

          <div className="space-y-3">
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold">1) Scrape</div>
                  <div className="mt-1 text-xs text-slate-600">Success looks like: new rows appear in Vault 1.</div>
                </div>
                <StatusBadge status="PENDING" label="Ready" />
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  className={buttonClass({ variant: "primary", disabled: !supplierId })}
                  onClick={() =>
                    runStep("Scrape", async () => {
                      const res = await enqueue(
                        "SCRAPE_SUPPLIER",
                        { supplier_id: Number(supplierId), supplier_name: supplierName || undefined, source_category: sourceCategory || undefined, pages: Number(pages || "1") },
                        70,
                      );
                      return `Scrape started (job ${res.id.slice(0, 12)}…)`;
                    })
                  }
                >
                  Start scrape
                </button>
                <Link className={buttonClass({ variant: "outline" })} href={`/vaults/raw?${[supplierParam, sourceCatParam].filter(Boolean).join("&")}`}>
                  View results
                </Link>
                <Link className={buttonClass({ variant: "link" })} href="/ops/queue?view=attention&type=SCRAPE_SUPPLIER">
                  If it fails: Queue →
                </Link>
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold">2) Enrich & standardise</div>
                  <div className="mt-1 text-xs text-slate-600">Success looks like: Vault 2 has enriched copy and draft payload previews.</div>
                </div>
                <StatusBadge status="PENDING" label="Ready" />
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  className={buttonClass({ variant: "primary", disabled: !supplierId })}
                  onClick={() =>
                    runStep("Enrich", async () => {
                      const res = await enqueue(
                        "ENRICH_SUPPLIER",
                        { supplier_id: Number(supplierId), supplier_name: supplierName || undefined, source_category: sourceCategory || undefined, batch_size: Number(batchSize || "25"), delay_seconds: 0 },
                        60,
                      );
                      return `Enrichment queued (job ${res.id.slice(0, 12)}…)`;
                    })
                  }
                >
                  Enrich now
                </button>
                <Link className={buttonClass({ variant: "outline" })} href={`/vaults/enriched?${[supplierParam, sourceCatParam].filter(Boolean).join("&")}`}>
                  View results
                </Link>
                <Link className={buttonClass({ variant: "link" })} href="/ops/jobs?status=FAILED&job_type=ENRICH_SUPPLIER">
                  If it fails: Jobs →
                </Link>
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold">3) Create drafts</div>
                  <div className="mt-1 text-xs text-slate-600">Success looks like: Vault 3 shows Draft listings.</div>
                </div>
                <StatusBadge status="DRY_RUN" label="Draft" />
              </div>
              <div className="mt-3 flex flex-wrap items-end gap-2">
                <label className="text-xs text-slate-600">
                  <div className="mb-1 font-semibold uppercase tracking-wide">Limit</div>
                  <input className="w-24 rounded-md border border-slate-200 bg-white px-2 py-2 text-sm text-slate-900" value={draftLimit} onChange={(e) => setDraftLimit(e.target.value)} />
                </label>
                <button
                  type="button"
                  className={buttonClass({ variant: "primary", disabled: !supplierId })}
                  onClick={() =>
                    runStep("Create drafts", async () => {
                      const lim = Number(draftLimit || "0");
                      if (!Number.isFinite(lim) || lim < 1 || lim > 1000) throw new Error("Draft limit must be 1–1000");
                      const res = await apiPostClient<{ enqueued: number }>(
                        "/ops/bulk/dryrun_publish",
                        { supplier_id: Number(supplierId), source_category: sourceCategory || undefined, limit: lim, priority: 60 },
                      );
                      return `Drafts queued: ${res.enqueued}`;
                    })
                  }
                >
                  Create drafts
                </button>
                <Link className={buttonClass({ variant: "outline" })} href="/vaults/live?status=DRY_RUN">
                  View drafts
                </Link>
                <Link className={buttonClass({ variant: "link" })} href="/ops/queue?view=attention&type=PUBLISH_LISTING">
                  If it fails: Queue →
                </Link>
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold">4) Publish approved</div>
                  <div className="mt-1 text-xs text-slate-600">Success looks like: Vault 3 shows Live listings.</div>
                </div>
                <StatusBadge status="LIVE" label="Live" />
              </div>
              <div className="mt-3 flex flex-wrap items-end gap-2">
                <label className="text-xs text-slate-600">
                  <div className="mb-1 font-semibold uppercase tracking-wide">Limit</div>
                  <input className="w-24 rounded-md border border-slate-200 bg-white px-2 py-2 text-sm text-slate-900" value={publishLimit} onChange={(e) => setPublishLimit(e.target.value)} />
                </label>
                <button
                  type="button"
                  className={buttonClass({ variant: "success", disabled: !supplierId || !canPublish })}
                  onClick={() =>
                    runStep("Publish approved", async () => {
                      const lim = Number(publishLimit || "0");
                      if (!Number.isFinite(lim) || lim < 1 || lim > 1000) throw new Error("Publish limit must be 1–1000");
                      if (!canPublish) throw new Error("Trade Me not configured/auth failed. Publishing disabled.");
                      const res = await apiPostClient<{ enqueued: number }>(
                        "/ops/bulk/approve_publish",
                        { supplier_id: Number(supplierId), source_category: sourceCategory || undefined, limit: lim, priority: 60, stop_on_failure: true },
                      );
                      return `Publish queued: ${res.enqueued}`;
                    })
                  }
                >
                  Publish approved drafts
                </button>
                <Link className={buttonClass({ variant: "outline" })} href="/vaults/live?status=Live">
                  View live
                </Link>
                <Link className={buttonClass({ variant: "link" })} href="/ops/trademe">
                  If it fails: Trade Me health →
                </Link>
              </div>
              {!canPublish ? (
                <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-2 text-xs text-amber-900">
                  Publishing disabled: Trade Me is <span className="font-semibold">{tmHealth?.configured ? "auth failed" : "not configured"}</span>.
                  Go to <Link className="underline" href="/ops/trademe">Trade Me Health</Link>.
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </SectionCard>
    </div>
  );
}

