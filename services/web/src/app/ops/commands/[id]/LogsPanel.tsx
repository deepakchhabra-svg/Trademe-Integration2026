"use client";

import { useEffect, useMemo, useState } from "react";

import { apiGetClient } from "../../../_components/api_client";
import { formatNZT } from "../../../_components/time";

type LogLine = {
  id: number;
  created_at: string | null;
  level: string | null;
  logger: string | null;
  message: string | null;
};

type LogsResp = {
  command_id: string;
  next_after_id: number;
  logs: LogLine[];
};

function isActiveStatus(status: string): boolean {
  return status === "PENDING" || status === "EXECUTING" || status === "FAILED_RETRYABLE";
}

export function CommandLogsPanel({
  commandId,
  initialStatus,
}: {
  commandId: string;
  initialStatus: string;
}) {
  const [auto, setAuto] = useState<boolean>(true);
  const [afterId, setAfterId] = useState<number>(0);
  const [lines, setLines] = useState<LogLine[]>([]);
  const [err, setErr] = useState<string | null>(null);

  const active = useMemo(() => isActiveStatus(initialStatus), [initialStatus]);

  useEffect(() => {
    let cancelled = false;

    const loadTail = async () => {
      try {
        const resp = await apiGetClient<LogsResp>(
          `/commands/${encodeURIComponent(commandId)}/logs?tail=true&limit=200`,
        );
        if (cancelled) return;
        setLines(resp.logs || []);
        setAfterId(resp.next_after_id || 0);
        setErr(null);
      } catch (e) {
        if (cancelled) return;
        setErr(e instanceof Error ? e.message : "Failed to load logs");
      }
    };

    void loadTail();
    return () => {
      cancelled = true;
    };
  }, [commandId]);

  useEffect(() => {
    if (!auto) return;

    let cancelled = false;
    const intervalMs = 1200;

    const tick = async () => {
      try {
        const resp = await apiGetClient<LogsResp>(
          `/commands/${encodeURIComponent(commandId)}/logs?after_id=${afterId}&limit=200`,
        );
        if (cancelled) return;

        const newLines = resp.logs || [];
        if (newLines.length) {
          setLines((prev) => {
            const next = prev.concat(newLines);
            // Keep the UI bounded even for noisy commands.
            return next.length > 600 ? next.slice(next.length - 600) : next;
          });
          setAfterId(resp.next_after_id || afterId);
        }
        setErr(null);
      } catch (e) {
        if (cancelled) return;
        setErr(e instanceof Error ? e.message : "Log poll failed");
      }
    };

    // Poll aggressively only while command is active; otherwise poll slowly.
    void tick();
    const t = window.setInterval(() => void tick(), active ? intervalMs : 5000);
    return () => {
      cancelled = true;
      window.clearInterval(t);
    };
  }, [auto, active, afterId, commandId]);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold">Logs</div>
          <div className="mt-1 text-xs text-slate-600">Live tail + persisted history for this command.</div>
        </div>
        <label className="flex items-center gap-2 text-xs text-slate-700">
          <input
            type="checkbox"
            className="h-4 w-4"
            checked={auto}
            onChange={(e) => setAuto(e.target.checked)}
          />
          Auto-tail
        </label>
      </div>

      {err ? (
        <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-2 text-[11px] text-amber-900">{err}</div>
      ) : null}

      <pre className="mt-3 max-h-[420px] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-[11px] text-slate-900">
        {lines.length
          ? lines
              .map((l) => {
                const ts = l.created_at || "";
                const lvl = l.level || "INFO";
                const msg = l.message || "";
                return `${formatNZT(ts)} [${lvl}] ${msg}`;
              })
              .join("\n")
          : "No logs yet."}
      </pre>
    </div>
  );
}

