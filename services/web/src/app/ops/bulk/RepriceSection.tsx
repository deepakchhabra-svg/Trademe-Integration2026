"use client";

import { useState } from "react";
import { apiPostClient } from "../../_components/api_client";
import { buttonClass } from "../../_components/ui";

type RepriceItem = {
    listing_id: string;
    tm_listing_id: string;
    title: string;
    cost: number;
    current_price: number;
    new_price: number;
    net_profit: number;
    roi: number;
    is_safe: boolean;
    safety_reason: string | null;
};

type RepriceResponse = {
    dry_run?: boolean;
    enqueued?: number;
    items: RepriceItem[];
};

export function RepriceSection({
    supplierId,
    supplierName,
    sourceCategory,
}: {
    supplierId: string;
    supplierName: string;
    sourceCategory: string;
}) {
    const [ruleType, setRuleType] = useState<"percentage" | "fixed_markup">("percentage");
    const [ruleValue, setRuleValue] = useState<string>("0.15"); // default 15% margin
    const [minMargin, setMinMargin] = useState<string>("0.10");
    const [results, setResults] = useState<RepriceItem[] | null>(null);
    const [busy, setBusy] = useState(false);
    const [msg, setMsg] = useState<string | null>(null);

    async function call(dryRun: boolean) {
        setBusy(true);
        setMsg(null);
        setResults(null);
        try {
            const val = parseFloat(ruleValue);
            const min = parseFloat(minMargin);
            const res = await apiPostClient<RepriceResponse>("/ops/bulk/reprice", {
                supplier_id: supplierId ? Number(supplierId) : undefined,
                category_id: sourceCategory || undefined,
                rule_type: ruleType,
                rule_value: val,
                min_margin: min,
                dry_run: dryRun,
                limit: 50, // Hardcoded limit for safety in V1 UI
            });

            if (dryRun) {
                setResults(res.items);
                setMsg(`Dry run complete. Found ${res.items.length} items.`);
            } else {
                setMsg(`Success: Enqueued ${res.enqueued} price updates.`);
            }
        } catch (e) {
            setMsg(e instanceof Error ? e.message : "Failed");
        } finally {
            setBusy(false);
        }
    }

    return (
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="text-sm font-semibold">Bulk Reprice (Advanced)</div>

            <div className="mt-3 flex flex-wrap items-end gap-3 rounded-lg border border-slate-100 bg-slate-50 p-3">
                <label className="text-xs text-slate-600">
                    <div className="mb-1 uppercase tracking-wide">Strategy</div>
                    <select
                        className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs"
                        value={ruleType}
                        onChange={(e) => setRuleType(e.target.value as any)}
                    >
                        <option value="percentage">Target Margin % (e.g. 0.15)</option>
                        <option value="fixed_markup">Fixed Markup $ (e.g. 10.0)</option>
                    </select>
                </label>

                <label className="text-xs text-slate-600">
                    <div className="mb-1 uppercase tracking-wide">Value</div>
                    <input
                        className="w-20 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs"
                        value={ruleValue}
                        onChange={(e) => setRuleValue(e.target.value)}
                    />
                </label>

                <label className="text-xs text-slate-600">
                    <div className="mb-1 uppercase tracking-wide font-bold text-red-700">Min Margin</div>
                    <input
                        className="w-20 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs"
                        value={minMargin}
                        onChange={(e) => setMinMargin(e.target.value)}
                    />
                </label>

                <div className="flex gap-2">
                    <button
                        onClick={() => call(true)}
                        disabled={busy}
                        className={buttonClass({ variant: "primary", disabled: busy })}
                    >
                        {busy ? "Thinking..." : "Preview (Dry Run)"}
                    </button>

                    {results && results.length > 0 && (
                        <button
                            onClick={() => {
                                if (confirm("DANGER: This will update live prices. Confirm?")) {
                                    call(false);
                                }
                            }}
                            disabled={busy}
                            className={buttonClass({ variant: "danger", disabled: busy })}
                        >
                            APPLY LIVE
                        </button>
                    )}
                </div>
            </div>

            {msg && <div className="mt-2 text-xs font-semibold text-slate-700">{msg}</div>}

            {results && (
                <div className="mt-3 overflow-x-auto">
                    <table className="w-full text-left text-xs">
                        <thead className="bg-slate-100 uppercase text-slate-500">
                            <tr>
                                <th className="p-2">Item</th>
                                <th className="p-2">Cost</th>
                                <th className="p-2">Current</th>
                                <th className="p-2">New</th>
                                <th className="p-2">Profit</th>
                                <th className="p-2">Status</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {results.map(r => (
                                <tr key={r.listing_id} className={r.is_safe ? "" : "bg-red-50"}>
                                    <td className="p-2 max-w-[200px] truncate" title={r.title}>{r.tm_listing_id}</td>
                                    <td className="p-2">${r.cost.toFixed(2)}</td>
                                    <td className="p-2 text-slate-500">${r.current_price.toFixed(2)}</td>
                                    <td className="p-2 font-bold">${r.new_price.toFixed(2)}</td>
                                    <td className="p-2">
                                        ${r.net_profit.toFixed(2)} <span className="text-slate-400">({r.roi.toFixed(0)}%)</span>
                                    </td>
                                    <td className="p-2">
                                        {r.is_safe ? (
                                            <span className="text-emerald-600 font-semibold">Safe</span>
                                        ) : (
                                            <span className="text-red-600 font-bold">{r.safety_reason}</span>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
