"use client";

import { useState } from "react";
import { apiPostClient } from "../../_components/api_client";

export function InboxCommandActions({ commandId }: { commandId: string }) {
  const [msg, setMsg] = useState<string | null>(null);
  const [busyKey, setBusyKey] = useState<"retry" | "cancel" | "ack" | null>(null);

  async function act(action: "retry" | "cancel" | "ack") {
    if (busyKey) return;
    setBusyKey(action);
    setMsg(null);
    try {
      await apiPostClient(`/commands/${encodeURIComponent(commandId)}/${action}`, {});
      setMsg(`${action.toUpperCase()} OK`);
      // simplest refresh
      window.location.reload();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Action failed");
      setBusyKey(null);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={!!busyKey}
          aria-busy={busyKey === "retry"}
          className={`rounded-md bg-slate-900 px-2.5 py-1 text-[11px] font-medium text-white ${
            busyKey ? "cursor-not-allowed opacity-60" : "hover:bg-slate-800"
          }`}
          onClick={() => act("retry")}
        >
          {busyKey === "retry" ? "Working…" : "Retry"}
        </button>
        <button
          type="button"
          disabled={!!busyKey}
          aria-busy={busyKey === "ack"}
          className={`rounded-md border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-medium text-slate-900 ${
            busyKey ? "cursor-not-allowed opacity-60" : "hover:bg-slate-50"
          }`}
          onClick={() => act("ack")}
        >
          {busyKey === "ack" ? "Working…" : "Ack"}
        </button>
        <button
          type="button"
          disabled={!!busyKey}
          aria-busy={busyKey === "cancel"}
          className={`rounded-md border border-red-200 bg-red-50 px-2.5 py-1 text-[11px] font-medium text-red-900 ${
            busyKey ? "cursor-not-allowed opacity-60" : "hover:bg-red-100"
          }`}
          onClick={() => act("cancel")}
        >
          {busyKey === "cancel" ? "Working…" : "Cancel"}
        </button>
      </div>
      {msg ? <div className="text-[11px] text-slate-600">{msg}</div> : null}
    </div>
  );
}

