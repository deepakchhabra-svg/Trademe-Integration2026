"use client";

import { Badge } from "./Badge";

export function NotImplemented({
  title,
  notes,
}: {
  title: string;
  notes?: Array<{ label: string; detail: string }>;
}) {
  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-amber-900">{title}</div>
          <div className="mt-1 text-xs text-amber-900/80">
            This area is intentionally present for review, but the underlying automation is not implemented yet.
          </div>
        </div>
        <Badge tone="amber">not implemented</Badge>
      </div>

      {notes?.length ? (
        <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-2">
          {notes.map((n) => (
            <div key={n.label} className="rounded-lg border border-amber-200 bg-white p-3">
              <div className="text-[11px] font-semibold uppercase tracking-wide text-amber-900/70">{n.label}</div>
              <div className="mt-1 text-xs text-slate-900">{n.detail}</div>
            </div>
          ))}
        </div>
      ) : null}

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          className="cursor-not-allowed rounded-md bg-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600"
          disabled
        >
          Action disabled
        </button>
        <div className="text-[11px] text-amber-900/70">
          These buttons will be wired to Trade Me + workflows (messages, tracking, refunds) in the fulfillment sprint.
        </div>
      </div>
    </div>
  );
}

