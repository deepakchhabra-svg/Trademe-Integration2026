"use client";

import { useState } from "react";
import { apiPostClient } from "../../_components/api_client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, CheckCircle, RefreshCw, Play } from "lucide-react";

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
        <Card>
            <CardHeader>
                <CardTitle className="text-lg">Bulk Reprice</CardTitle>
                <CardDescription>Adjust prices based on margin targets. Safe mode enabled.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="flex flex-wrap items-end gap-3 rounded-lg border bg-muted/50 p-4">
                    <div className="space-y-1">
                        <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Strategy</span>
                        <select
                            className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                            value={ruleType}
                            onChange={(e) => setRuleType(e.target.value as any)}
                        >
                            <option value="percentage">Target Margin % (e.g. 0.15)</option>
                            <option value="fixed_markup">Fixed Markup $ (e.g. 10.0)</option>
                        </select>
                    </div>

                    <div className="space-y-1">
                        <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Value</span>
                        <Input
                            className="w-24"
                            value={ruleValue}
                            onChange={(e) => setRuleValue(e.target.value)}
                        />
                    </div>

                    <div className="space-y-1">
                        <span className="text-xs font-medium uppercase tracking-wide text-red-600">Min Margin</span>
                        <Input
                            className="w-24 border-red-200"
                            value={minMargin}
                            onChange={(e) => setMinMargin(e.target.value)}
                        />
                    </div>

                    <div className="flex gap-2 ml-auto">
                        <Button variant="secondary" disabled={busy} onClick={() => call(true)}>
                            {busy ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
                            Preview
                        </Button>

                        {results && results.length > 0 && (
                            <Button
                                variant="destructive"
                                disabled={busy}
                                onClick={() => {
                                    if (confirm("DANGER: This will update live prices. Confirm?")) {
                                        call(false);
                                    }
                                }}
                            >
                                APPLY LIVE
                            </Button>
                        )}
                    </div>
                </div>

                {msg && <div className="text-sm font-medium text-muted-foreground">{msg}</div>}

                {results && (
                    <div className="rounded-md border">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Item</TableHead>
                                    <TableHead>Cost</TableHead>
                                    <TableHead>Current</TableHead>
                                    <TableHead>New</TableHead>
                                    <TableHead>Profit</TableHead>
                                    <TableHead>Status</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {results.map(r => (
                                    <TableRow key={r.listing_id} className={!r.is_safe ? "bg-red-50 dark:bg-red-900/20" : ""}>
                                        <TableCell className="font-mono text-xs max-w-[200px] truncate" title={r.title}>{r.tm_listing_id}</TableCell>
                                        <TableCell>${r.cost.toFixed(2)}</TableCell>
                                        <TableCell className="text-muted-foreground">${r.current_price.toFixed(2)}</TableCell>
                                        <TableCell className="font-bold">${r.new_price.toFixed(2)}</TableCell>
                                        <TableCell>
                                            ${r.net_profit.toFixed(2)} <span className="text-muted-foreground">({r.roi.toFixed(0)}%)</span>
                                        </TableCell>
                                        <TableCell>
                                            {r.is_safe ? (
                                                <Badge variant="outline" className="text-emerald-600 border-emerald-200 bg-emerald-50">Safe</Badge>
                                            ) : (
                                                <Badge variant="destructive">{r.safety_reason}</Badge>
                                            )}
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
