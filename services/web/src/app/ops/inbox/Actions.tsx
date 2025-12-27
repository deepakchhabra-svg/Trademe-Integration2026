"use client";

import { useState } from "react";
import { apiPostClient } from "../../_components/api_client";

export function InboxCommandActions({ commandId }: { commandId: string }) {
  const [msg, setMsg] = useState<string | null>(null);

  async function act(action: "retry" | "cancel" | "ack") {
    setMsg(null);
    try {
      await apiPostClient(`/commands/${encodeURIComponent(commandId)}/${action}`, {});
      setMsg(`${action.toUpperCase()} OK`);
      // simplest refresh
      window.location.reload();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Action failed");
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className="rounded-md bg-slate-900 px-2.5 py-1 text-[11px] font-medium text-white"
          onClick={() => act("retry")}
        >
          Retry
        </button>
        <button
          type="button"
          className="rounded-md border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-medium text-slate-900"
          onClick={() => act("ack")}
        >
          Ack
        </button>
        <button
          type="button"
          className="rounded-md border border-red-200 bg-red-50 px-2.5 py-1 text-[11px] font-medium text-red-900"
          onClick={() => act("cancel")}
        >
          Cancel
        </button>
      </div>
      {msg ? <div className="text-[11px] text-slate-600">{msg}</div> : null}
    </div>
  );
}

