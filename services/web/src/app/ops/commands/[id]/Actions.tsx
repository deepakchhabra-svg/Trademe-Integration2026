"use client";

import { useState } from "react";
import { apiPostClient } from "../../../_components/api_client";

export function CommandActions({ commandId }: { commandId: string }) {
  const [msg, setMsg] = useState<string | null>(null);

  async function act(action: "retry" | "ack" | "cancel") {
    setMsg(null);
    try {
      await apiPostClient(`/commands/${encodeURIComponent(commandId)}/${action}`, {});
      setMsg(`${action.toUpperCase()} OK`);
      window.location.reload();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Action failed");
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="text-sm font-semibold">Actions</div>
      <div className="mt-2 flex flex-wrap gap-2">
        <button
          type="button"
          className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white"
          onClick={() => act("retry")}
        >
          Retry
        </button>
        <button
          type="button"
          className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-900"
          onClick={() => act("ack")}
        >
          Ack
        </button>
        <button
          type="button"
          className="rounded-md border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-medium text-red-900"
          onClick={() => act("cancel")}
        >
          Cancel
        </button>
      </div>
      {msg ? <div className="mt-2 text-xs text-slate-600">{msg}</div> : null}
    </div>
  );
}

