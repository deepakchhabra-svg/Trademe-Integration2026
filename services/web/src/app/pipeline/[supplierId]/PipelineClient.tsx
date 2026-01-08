"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { apiGetClient, apiPostClient } from "../../_components/api_client";
import { useEnqueue } from "../../_hooks/useEnqueue";
import { buttonClass } from "../../_components/ui";
import { formatNZT } from "../../_components/time";
import { SectionCard } from "../../../components/ui/SectionCard";
import { StatusBadge } from "../../../components/ui/StatusBadge";

type PipelineResp = {
  utc: string;
  supplier: { id: number; name: string; base_url: string | null; is_active: boolean | null };
  summary: {
    utc: string;
    supplier: { id: number; name: string };
    counts: {
      raw_total: number;
      raw_present: number;
      raw_removed: number;
      images_missing: number;
      enrich_ready: number;
      drafts_dry_run: number;
      live: number;
    };
    top_blockers: [string, number][];
  };
  active_commands: Array<{
    id: string;
    type: string;
    status: string;
    priority: number;
    attempts: number;
    max_attempts: number;
    error_code: string | null;
    error_message: string | null;
    payload: Record<string, unknown>;
    created_at: string | null;
    updated_at: string | null;
    progress:
    | {
      phase: string | null;
      done: number | null;
      total: number | null;
      eta_seconds: number | null;
      message: string | null;
      updated_at: string | null;
    }
    | null;
  }>;
};

function pct(done: number | null | undefined, total: number | null | undefined): number | null {
  if (done == null || total == null) return null;
  if (total <= 0) return null;
  return Math.max(0, Math.min(100, Math.round((done / total) * 100)));
}



export function PipelineClient({ supplierId, initial }: { supplierId: number; initial: PipelineResp }) {
  const [data, setData] = useState<PipelineResp>(initial);
  const [refreshing, setRefreshing] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const { enqueue: runEnqueue } = useEnqueue();

  const topBlocker = data.summary.top_blockers?.[0]?.[0] || null;
  const topBlockerCount = data.summary.top_blockers?.[0]?.[1] || 0;

  const activeByPhase = useMemo(() => {
    const out: Record<string, PipelineResp["active_commands"][number][]> = {};
    for (const c of data.active_commands || []) {
      const ph = (c.progress?.phase || c.type || "unknown").toString().toLowerCase();
      out[ph] = out[ph] || [];
      out[ph].push(c);
    }
    return out;
  }, [data.active_commands]);

  async function refresh() {
    if (refreshing) return;
    setRefreshing(true);
    try {
      const next = await apiGetClient<PipelineResp>(`/ops/suppliers/${supplierId}/pipeline`);
      setData(next);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Refresh failed");
    } finally {
      setRefreshing(false);
    }
  }

  useEffect(() => {
    // Auto-refresh while any command is active.
    if (!data.active_commands?.length) return;
    const t = window.setInterval(() => void refresh(), 2500);
    return () => window.clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data.active_commands?.length]);

  async function runStep(label: string, fn: () => Promise<string>) {
    setMsg(`Working: ${label}…`);
    try {
      const out = await fn();
      setMsg(out);
      await refresh();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Action failed");
    }
  }

  return (
    <div className="space-y-6">
      {msg ? <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-900">{msg}</div> : null}

      <SectionCard
        title="Pipeline health"
        subtitle={`Last updated: ${formatNZT(data.utc)}${topBlocker ? ` · Top blocker: ${topBlocker} (${topBlockerCount})` : ""}`}
        actions={
          <div className="flex items-center gap-2">
            <button type="button" className={buttonClass({ variant: "outline", disabled: refreshing })} onClick={refresh}>
              {refreshing ? "Refreshing…" : "Refresh"}
            </button>
            <Link className={buttonClass({ variant: "outline" })} href="/ops/queue?view=active">
              Queue →
            </Link>
          </div>
        }
      >
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <div className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Vault 1 (raw)</div>
            <div className="mt-1 text-sm text-slate-900">
              <span className="font-semibold">{data.summary.counts.raw_present}</span> present ·{" "}
              <span className="font-semibold">{data.summary.counts.raw_removed}</span> removed
            </div>
            <div className="mt-2 flex gap-2">
              <Link className={buttonClass({ variant: "link" })} href={`/vaults/raw?supplier_id=${supplierId}`}>
                Open Vault 1 →
              </Link>
              <Link className={buttonClass({ variant: "link" })} href={`/ops/removed?supplier_id=${supplierId}`}>
                Removed items →
              </Link>
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Enrichment</div>
            <div className="mt-1 text-sm text-slate-900">
              <span className="font-semibold">{data.summary.counts.enrich_ready}</span> enriched-ready
            </div>
            <div className="mt-2">
              <Link className={buttonClass({ variant: "link" })} href={`/vaults/enriched?supplier_id=${supplierId}`}>
                Open Vault 2 →
              </Link>
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Listings</div>
            <div className="mt-1 text-sm text-slate-900">
              <span className="font-semibold">{data.summary.counts.drafts_dry_run}</span> drafts ·{" "}
              <span className="font-semibold">{data.summary.counts.live}</span> live
            </div>
            <div className="mt-2 flex gap-2">
              <Link className={buttonClass({ variant: "link" })} href={`/vaults/live?supplier_id=${supplierId}&status=DRY_RUN`}>
                Drafts →
              </Link>
              <Link className={buttonClass({ variant: "link" })} href={`/vaults/live?supplier_id=${supplierId}&status=Live`}>
                Live →
              </Link>
            </div>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="Run pipeline" subtitle="Single supplier flow: Scrape → Enrich → Draft → Validate → Publish">
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="text-sm font-semibold">Scrape</div>
            <div className="mt-1 text-xs text-slate-500">Pull latest supplier truth into Vault 1 (includes specs extraction).</div>
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                type="button"
                className={buttonClass({ variant: "primary" })}
                onClick={() =>
                  runStep("Scrape", async () => {
                    const out = await runEnqueue({
                      type: "SCRAPE_SUPPLIER",
                      payload: { supplier_id: supplierId, supplier_name: data.supplier.name },
                      priority: 70,
                    });
                    return `Queued scrape command ${out.id.slice(0, 8)}…`;
                  })
                }
              >
                Run scrape
              </button>
              <Link className={buttonClass({ variant: "outline" })} href={`/ops/queue?view=active&type=SCRAPE_SUPPLIER`}>
                View running →
              </Link>
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="text-sm font-semibold">Images</div>
            <div className="mt-1 text-xs text-slate-500">Backfill local, listing-usable images (idempotent; safe to re-run).</div>
            <div className="mt-2 text-xs text-slate-600">
              Missing images (best-effort): <span className="font-semibold">{data.summary.counts.images_missing}</span>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                type="button"
                className={buttonClass({ variant: "primary" })}
                onClick={() =>
                  runStep("Backfill images", async () => {
                    const out = await runEnqueue({
                      type: "BACKFILL_IMAGES_ONECHEQ",
                      payload: { supplier_id: supplierId, supplier_name: data.supplier.name, batch: 5000, concurrency: 16, max_seconds: 600 },
                      priority: 65,
                    });
                    return `Queued image backfill ${out.id.slice(0, 8)}…`;
                  })
                }
              >
                Backfill images
              </button>
              <Link className={buttonClass({ variant: "outline" })} href={`/ops/queue?view=active&type=BACKFILL_IMAGES_ONECHEQ`}>
                View running →
              </Link>
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="text-sm font-semibold">Enrich</div>
            <div className="mt-1 text-xs text-slate-500">Generate operator-grade titles/descriptions (Vault 2 truth).</div>
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                type="button"
                className={buttonClass({ variant: "primary" })}
                onClick={() =>
                  runStep("Enrich", async () => {
                    const out = await runEnqueue({
                      type: "ENRICH_SUPPLIER",
                      payload: { supplier_id: supplierId, supplier_name: data.supplier.name, batch_size: 1000, delay_seconds: 0 },
                      priority: 60,
                    });
                    return `Queued enrich command ${out.id.slice(0, 8)}…`;
                  })
                }
              >
                Run enrich
              </button>
              <Link className={buttonClass({ variant: "outline" })} href={`/ops/queue?view=active&type=ENRICH_SUPPLIER`}>
                View running →
              </Link>
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="text-sm font-semibold">Draft</div>
            <div className="mt-1 text-xs text-slate-500">Build Trade Me draft payloads (Vault 3 drafts).</div>
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                type="button"
                className={buttonClass({ variant: "primary" })}
                onClick={() =>
                  runStep("Build drafts", async () => {
                    const res = await apiPostClient<{ enqueued: number; skipped_existing_cmd: number; skipped_already_listed: number; skipped_blocked?: number }>(
                      "/ops/bulk/dryrun_publish",
                      {
                        supplier_id: supplierId,
                        limit: 100,
                        priority: 50,
                        stop_on_failure: false,
                      },
                    );
                    return `Drafts queued: enqueued=${res.enqueued}, skipped_existing=${res.skipped_existing_cmd}, skipped_listed=${res.skipped_already_listed}${res.skipped_blocked ? `, blocked=${res.skipped_blocked}` : ""
                      }`;
                  })
                }
              >
                Build drafts
              </button>
              <Link className={buttonClass({ variant: "outline" })} href={`/vaults/live?supplier_id=${supplierId}&status=DRY_RUN`}>
                View drafts →
              </Link>
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="text-sm font-semibold">Validate + publish</div>
            <div className="mt-1 text-xs text-slate-500">Validate against Trade Me, then publish READY drafts only.</div>
            <div className="mt-3 flex flex-wrap gap-2">
              <Link className={buttonClass({ variant: "outline" })} href="/ops/trademe">
                Trade Me health →
              </Link>
              <Link className={buttonClass({ variant: "outline" })} href={`/ops/readiness?supplier=${encodeURIComponent(data.supplier.name)}`}>
                Readiness →
              </Link>
              <Link className={buttonClass({ variant: "outline" })} href="/ops/bulk">
                Publish console →
              </Link>
            </div>
          </div>
        </div >
      </SectionCard >

      <SectionCard title={`Active work (${data.active_commands.length})`} subtitle="Live commands for this supplier (auto-refresh while active).">
        {data.active_commands.length ? (
          <div className="space-y-2">
            {data.active_commands.map((c) => {
              const p = c.progress;
              const percent = pct(p?.done ?? null, p?.total ?? null);
              return (
                <div key={c.id} className="rounded-xl border border-slate-200 bg-white p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <StatusBadge status={c.status} />
                      <div className="text-sm font-semibold text-slate-900">{c.type}</div>
                      <Link className="text-xs text-indigo-700 hover:underline" href={`/ops/commands/${c.id}`}>
                        cmd {c.id.slice(0, 8)}…
                      </Link>
                    </div>
                    <div className="text-xs text-slate-500">Updated: {formatNZT(c.updated_at)}</div>
                  </div>

                  {p?.message ? <div className="mt-1 text-xs text-slate-600">{p.message}</div> : null}

                  {percent != null ? (
                    <div className="mt-2">
                      <div className="h-2 w-full overflow-hidden rounded bg-slate-100">
                        <div className="h-2 bg-indigo-600" style={{ width: `${percent}%` }} />
                      </div>
                      <div className="mt-1 text-[11px] text-slate-500">
                        {p?.done ?? 0}/{p?.total ?? 0} · {percent}%
                        {p?.eta_seconds != null ? ` · ETA ~${Math.max(0, Math.round(p.eta_seconds))}s` : ""}
                      </div>
                    </div>
                  ) : p?.done != null ? (
                    <div className="mt-2 text-[11px] text-slate-500">Processed: {p.done}{p.total != null ? `/${p.total}` : ""}</div>
                  ) : null}
                </div>
              );
            })}
          </div>
        ) : (
          <div className="rounded-xl border-2 border-dashed border-slate-200 bg-slate-50 p-6 text-sm text-slate-700">
            No active work right now. Next action:{" "}
            <button
              type="button"
              className="underline"
              onClick={() =>
                runStep("Scrape", async () => {
                  const out = await runEnqueue({ type: "SCRAPE_SUPPLIER", payload: { supplier_id: supplierId, supplier_name: data.supplier.name }, priority: 70 });
                  return `Queued scrape command ${out.id.slice(0, 8)}…`;
                })
              }
            >
              run scrape
            </button>
            .
          </div>
        )}
      </SectionCard>

      {Object.keys(activeByPhase).length ? null : null}
    </div >
  );
}

