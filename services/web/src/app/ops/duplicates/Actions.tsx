"use client";

import { useState } from "react";
import { useEnqueue } from "../../_hooks/useEnqueue";
import { Button } from "@/components/ui/button";
import { Loader2, Trash2 } from "lucide-react";

type Listing = {
    id: number;
    tm_id: string;
};

type DuplicateGroup = {
    internal_product_id: number;
    listings: Listing[];
};

export function ResolveButton({ group }: { group: DuplicateGroup }) {
    const [busy, setBusy] = useState(false);
    const [done, setDone] = useState(false);
    const { enqueue } = useEnqueue();

    const sorted = [...group.listings].sort((a, b) => a.id - b.id);
    const keep = sorted[0];
    const remove = sorted.slice(1);

    async function resolve() {
        if (!confirm(`Keep listing ${keep.tm_id} (ID ${keep.id}) and withdraw ${remove.length} duplicates?`)) return;
        setBusy(true);
        try {
            for (const l of remove) {
                await enqueue({
                    type: "WITHDRAW_LISTING",
                    payload: { listing_id: l.id },
                    priority: 80,
                });
            }
            setDone(true);
        } catch (e) {
            alert("Failed: " + e);
            setBusy(false);
        }
    }

    if (done) return <span className="text-sm font-medium text-emerald-600">Resolved</span>;

    return (
        <Button variant="destructive" size="sm" onClick={resolve} disabled={busy}>
            {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Trash2 className="mr-2 h-4 w-4" />}
            Resolve ({remove.length})
        </Button>
    );
}
