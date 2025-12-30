"use client";

import { useEffect, useMemo, useState } from "react";

import { apiGetClient } from "../../../_components/api_client";

type CommandDetail = {
  id: string;
  type: string;
  status: string;
  priority: number;
  attempts: number;
  max_attempts: number;
  last_error: string | null;
  error_code?: string | null;
  error_message?: string | null;
  payload: Record<string, unknown>;
  created_at: string | null;
  updated_at: string | null;
};

type Progress = {
  phase?: string;
  supplier?: string;
  collection?: string;
  scraped?: number;
  upserted?: number;
  done?: boolean;
  updated_at?: string;
};

function toneForStatus(status: string): "emerald" | "red" | "amber" | "slate" {
  if (status === "SUCCEEDED") return "emerald";
  if (status.includes("FAILED")) return "red";
  if (status === "HUMAN_REQUIRED") return "red";
  if (status === "CANCELLED") return "slate";
  return "amber";
}

function Badge({ tone, children }: { tone: "emerald" | "red" | "amber" | "slate"; children: React.ReactNode }) {
  const cls =
    tone === "emerald"
      ? "border-emerald-200 bg-emerald-50 text-emerald-900"
      : tone === "red"
        ? "border-red-200 bg-red-50 text-red-900"
        : tone === "amber"
          ? "border-amber-200 bg-amber-50 text-amber-900"
          : "border-slate-200 bg-slate-50 text-slate-900";
  return <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium ${cls}`}>{children}</span>;
}

function isActiveStatus(status: string): boolean {
  return status === "PENDING" || status === "EXECUTING" || status === "FAILED_RETRYABLE";
}

export function LiveCommandPanel({ commandId, initial }: { commandId: string; initial: CommandDetail }) {
  const [cmd, setCmd] = useState<CommandDetail>(initial);
  const [auto, setAuto] = useState<boolean>(true);
  const [pollError, setPollError] = useState<string | null>(null);

  const active = useMemo(() => isActiveStatus(cmd.status), [cmd.status]);
  const progress = useMemo(() => (cmd.payload?.progress as Progress | undefined) || undefined, [cmd.payload]);

  useEffect(() => {
    if (!auto) return;
    if (!active) return;

    let cancelled = false;
    const intervalMs = 1500;

    const tick = async () => {
      try {
        const next = await apiGetClient<CommandDetail>(`/commands/${encodeURIComponent(commandId)}`);
        if (cancelled) return;
        setCmd(next);
        setPollError(null);
      } catch (e) {
        if (cancelled) return;
        setPollError(e instanceof Error ? e.message : "Poll failed");
      }
    };

    void tick();
    const t = window.setInterval(() => void tick(), intervalMs);
    return () => {
      cancelled = true;
      window.clearInterval(t);
    };
  }, [auto, active, commandId]);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold">Live status</div>
          <div className="mt-1 text-xs text-slate-600">
            {active ? "Auto-refreshing while command is active." : "Command is not active; auto-refresh paused."}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 text-xs text-slate-700">
            <input
              type="checkbox"
              className="h-4 w-4"
              checked={auto}
              onChange={(e) => setAuto(e.target.checked)}
            />
            Auto-refresh
          </label>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Badge tone={toneForStatus(cmd.status)}>{cmd.status}</Badge>
        {cmd.error_code ? <Badge tone="red">{cmd.error_code}</Badge> : null}
        <Badge tone="slate">
          attempts {cmd.attempts}/{cmd.max_attempts}
        </Badge>
        <Badge tone="slate">updated {cmd.updated_at || "-"}</Badge>
      </div>

      {pollError ? (
        <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-2 text-[11px] text-amber-900">
          Poll error: {pollError}
        </div>
      ) : null}

      {progress ? (
        <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Progress</div>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-slate-900">
            <Badge tone="slate">{progress.phase || "running"}</Badge>
            {progress.supplier ? <Badge tone="slate">{progress.supplier}</Badge> : null}
            {progress.collection ? <Badge tone="slate">collection {progress.collection}</Badge> : null}
            {typeof progress.scraped === "number" ? <Badge tone="amber">scraped {progress.scraped}</Badge> : null}
            {typeof progress.upserted === "number" ? <Badge tone="emerald">saved {progress.upserted}</Badge> : null}
            {progress.updated_at ? <Badge tone="slate">progress updated {progress.updated_at}</Badge> : null}
          </div>
          <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-200">
            {/* Unknown total: show an indeterminate bar while active */}
            <div className={`h-full ${active ? "w-1/2 animate-pulse bg-amber-400" : "w-full bg-slate-400"}`} />
          </div>
        </div>
      ) : active ? (
        <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-2 text-[11px] text-slate-700">
          No progress reported yet. This usually means the worker isn’t emitting cmd_id-tagged progress logs yet.
        </div>
      ) : null}

      {cmd.error_message || cmd.last_error ? (
        <pre className="mt-3 max-h-40 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-2 text-[11px] text-slate-900">
          {(cmd.error_message || "") + (cmd.last_error ? `\n${cmd.last_error}` : "")}
        </pre>
      ) : null}
    </div>
  );
}

