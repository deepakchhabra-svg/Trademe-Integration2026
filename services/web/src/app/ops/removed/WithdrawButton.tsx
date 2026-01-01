"use client";

import { useState } from "react";
import { apiPostClient } from "../../_components/api_client";
import { buttonClass } from "../../_components/ui";

export function WithdrawButton({ supplierId }: { supplierId: number | null }) {
    const [busy, setBusy] = useState(false);
    const [msg, setMsg] = useState<string | null>(null);

    async function handle() {
        if (busy) return;
        setBusy(true);
        setMsg(null);
        try {
            const res = await apiPostClient<{ enqueued: number }>("/ops/bulk/withdraw_removed", { supplier_id: supplierId });
            setMsg(`Enqueued ${res.enqueued} withdrawal commands.`);
        } catch (e) {
            setMsg(e instanceof Error ? e.message : "Failed to trigger withdrawal");
        } finally {
            setBusy(false);
        }
    }

    return (
        <div className="flex flex-col items-end gap-2">
            <button type="button" className={buttonClass({ variant: "primary", disabled: busy })} onClick={handle}>
                {busy ? "Queuing..." : "Withdraw all removed items"}
            </button>
            {msg && <div className="text-[10px] text-slate-600">{msg}</div>}
        </div>
    );
}
