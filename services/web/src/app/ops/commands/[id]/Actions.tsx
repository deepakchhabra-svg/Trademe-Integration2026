"use client";

import { useState } from "react";
import { apiPostClient } from "../../../_components/api_client";
import { buttonClass } from "../../../_components/ui";

export function CommandActions({ commandId }: { commandId: string }) {
  const [msg, setMsg] = useState<string | null>(null);
  const [busyKey, setBusyKey] = useState<"retry" | "ack" | "cancel" | null>(null);

  async function act(action: "retry" | "ack" | "cancel") {
    if (busyKey) return;
    setBusyKey(action);
    setMsg(null);
    try {
      await apiPostClient(`/commands/${encodeURIComponent(commandId)}/${action}`, {});
      setMsg(`${action.toUpperCase()} OK`);
      window.location.reload();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Action failed");
      setBusyKey(null);
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="text-sm font-semibold">Actions</div>
      <div className="mt-2 flex flex-wrap gap-2">
        <button
          type="button"
          disabled={!!busyKey}
          aria-busy={busyKey === "retry"}
          className={buttonClass({ variant: "primary", disabled: !!busyKey })}
          onClick={() => act("retry")}
        >
          {busyKey === "retry" ? "Working…" : "Retry"}
        </button>
        <button
          type="button"
          disabled={!!busyKey}
          aria-busy={busyKey === "ack"}
          className={buttonClass({ variant: "outline", disabled: !!busyKey })}
          onClick={() => act("ack")}
        >
          {busyKey === "ack" ? "Working…" : "Acknowledge"}
        </button>
        <button
          type="button"
          disabled={!!busyKey}
          aria-busy={busyKey === "cancel"}
          className={buttonClass({ variant: "danger", disabled: !!busyKey })}
          onClick={() => act("cancel")}
        >
          {busyKey === "cancel" ? "Working…" : "Cancel"}
        </button>
      </div>
      {msg ? <div className="mt-2 text-xs text-slate-600">{msg}</div> : null}
    </div>
  );
}

