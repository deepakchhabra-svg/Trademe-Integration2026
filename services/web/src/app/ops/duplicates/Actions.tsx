"use client";

import { useState } from "react";
import { apiPostClient } from "../../_components/api_client";
import { buttonClass } from "../../_components/ui";

type Listing = {
    id: number;
    tm_id: string;
    price: number | null;
    last_synced?: string;
};

type DuplicateGroup = {
    internal_product_id: number;
    listings: Listing[];
};

export function ResolveButton({ group }: { group: DuplicateGroup }) {
    const [busy, setBusy] = useState(false);
    const [done, setDone] = useState(false);

    // Default strategy: Keep the one with the lowest ID (oldest) or best price?
    // Let's Keep Oldest (lowest ID) as it likely has the history/views.
    const sorted = [...group.listings].sort((a, b) => a.id - b.id);
    const keep = sorted[0];
    const remove = sorted.slice(1);

    async function resolve() {
        if (!confirm(`Keep listing ${keep.tm_id} (ID ${keep.id}) and withdraw ${remove.length} duplicates?`)) return;
        setBusy(true);
        try {
            for (const l of remove) {
                await apiPostClient("/ops/enqueue", {
                    type: "WITHDRAW_LISTING",
                    payload: { listing_id: l.id, reason: "Duplicate cleanup" },
                    priority: 80,
                });
            }
            setDone(true);
        } catch (e) {
            alert(e instanceof Error ? e.message : "Failed");
        } finally {
            setBusy(false);
        }
    }

    if (done) {
        return <span className="text-xs font-semibold text-emerald-600">Resolved (Enqueued)</span>;
    }

    return (
        <button
            onClick={resolve}
            disabled={busy}
            className={buttonClass({ variant: "danger", size: "sm", disabled: busy })}
        >
            {busy ? "Resolving..." : `Withdraw ${remove.length} Extras`}
        </button>
    );
}
