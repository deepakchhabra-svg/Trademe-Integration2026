"use client";

import { useState } from "react";
import { apiPostClient } from "../_components/api_client";

export type EnqueueParams = {
    type: string;
    payload?: Record<string, unknown>;
    priority?: number;
};

export function useEnqueue() {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    /**
     * Enqueue a background command.
     * Uses the canonical /ops/enqueue endpoint (unless overridden).
     */
    async function enqueue(params: EnqueueParams) {
        setLoading(true);
        setError(null);
        try {
            // Canonical path per refactor plan
            const res = await apiPostClient<{ id: string; status: string; enqueued?: number }>(
                "/ops/enqueue",
                params
            );
            return res;
        } catch (e) {
            const msg = e instanceof Error ? e.message : "Failed to enqueue command";
            setError(msg);
            throw e;
        } finally {
            setLoading(false);
        }
    }

    return { enqueue, loading, error };
}
