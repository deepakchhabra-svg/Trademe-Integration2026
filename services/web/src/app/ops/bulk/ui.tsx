"use client";

import { useEffect, useState } from "react";
import { apiGetClient, apiPostClient } from "../../_components/api_client";
import { RepriceSection } from "./RepriceSection";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Loader2, Play, RefreshCw, UploadCloud, CheckCircle, ShieldAlert, Sparkles, AlertCircle } from "lucide-react";

type Resp = { id: string; status: string };
type Supplier = { id: number; name: string };

function Spinner() {
  return <Loader2 className="h-4 w-4 animate-spin" />;
}

export function BulkOpsForm({ suppliers }: { suppliers: Supplier[] }) {
  const [supplierId, setSupplierId] = useState<string>("");
  const [supplierName, setSupplierName] = useState<string>("");
  const [sourceCategory, setSourceCategory] = useState<string>("");
  const [activeTab, setActiveTab] = useState("sourcing");

  // Limits
  const [pages, setPages] = useState<string>("1");
  const [batchSize, setBatchSize] = useState<string>("25");
  const [dryRunLimit, setDryRunLimit] = useState<string>("50");
  const [approveLimit, setApproveLimit] = useState<string>("50");
  const [resetEnrichLimit, setResetEnrichLimit] = useState<string>("200");

  const [msg, setMsg] = useState<string | null>(null);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [categoryPresets, setCategoryPresets] = useState<string[]>([]);
  const [presetsMsg, setPresetsMsg] = useState<string | null>(null);

  async function run(key: string, fn: () => Promise<string>) {
    if (busyKey) return;
    setBusyKey(key);
    setMsg(`Working: ${key}…`);
    try {
      const m = await fn();
      setMsg(m);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusyKey(null);
    }
  }

  async function enqueue(type: string, payload: Record<string, unknown>, priority = 60): Promise<string> {
    const res = await apiPostClient<Resp>("/ops/enqueue", { type, payload, priority });
    return `Queued action (${res.id.slice(0, 12)})`;
  }

  useEffect(() => {
    let cancelled = false;
    async function loadPresets() {
      setPresetsMsg(null);
      setCategoryPresets([]);
      const sid = Number(supplierId || "");
      if (!sid || Number.isNaN(sid)) return;
      try {
        const resp = await apiGetClient<{ supplier_id: number; policy: { scrape?: { category_presets?: string[] } } }>(
          `/suppliers/${encodeURIComponent(String(sid))}/policy`,
        );
        if (cancelled) return;
        const presets = resp?.policy?.scrape?.category_presets || [];
        setCategoryPresets(Array.isArray(presets) ? presets.filter((x) => typeof x === "string" && x.trim()) : []);
      } catch (e) {
        if (cancelled) return;
        setPresetsMsg(e instanceof Error ? e.message : "Failed to load presets");
      }
    }
    void loadPresets();
    return () => {
      cancelled = true;
    };
  }, [supplierId]);

  return (
    <div className="space-y-6">
      {msg && (
        <div className={`p-4 rounded-md border text-sm ${msg.includes("Queued") ? "bg-emerald-50 text-emerald-900 border-emerald-200" : "bg-muted text-foreground"}`}>
          {msg}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Scope</CardTitle>
          <CardDescription>Target specific suppliers and categories for bulk operations.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Supplier</label>
              <select
                className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                value={supplierId && supplierName ? `${supplierId}:${supplierName}` : ""}
                onChange={(e) => {
                  const v = e.target.value;
                  if (!v) { setSupplierId(""); setSupplierName(""); return; }
                  const [id, name] = v.split(":");
                  setSupplierId(id);
                  setSupplierName(name);
                }}
              >
                <option value="">Select supplier…</option>
                {suppliers.map((s) => (
                  <option key={s.id} value={`${s.id}:${s.name}`}>{s.name} (ID {s.id})</option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Category</label>
              <Input
                placeholder="e.g. smartphones-and-mobilephones"
                value={sourceCategory}
                onChange={(e) => setSourceCategory(e.target.value)}
              />
              <div className="text-xs text-muted-foreground">Optional filter. Supports collection handle or partial URL.</div>
            </div>
          </div>

          {presetsMsg && <div className="text-sm text-destructive">{presetsMsg}</div>}

          {categoryPresets.length > 0 && (
            <div className="space-y-2">
              <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Presets</span>
              <div className="flex flex-wrap gap-2">
                {categoryPresets.slice(0, 10).map(p => (
                  <Badge key={p} variant="secondary" className="cursor-pointer hover:bg-secondary/80" onClick={() => setSourceCategory(p)}>
                    {p}
                  </Badge>
                ))}
                {categoryPresets.length > 10 && <span className="text-xs text-muted-foreground">+{categoryPresets.length - 10} more</span>}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Tabs defaultValue="sourcing" className="w-full">
        <TabsList className="grid w-full grid-cols-4 lg:w-[600px]">
          <TabsTrigger value="sourcing">Sourcing</TabsTrigger>
          <TabsTrigger value="listing">Listing</TabsTrigger>
          <TabsTrigger value="maintenance">Maintenance</TabsTrigger>
          <TabsTrigger value="reprice">Reprice</TabsTrigger>
        </TabsList>

        <TabsContent value="sourcing" className="space-y-4 pt-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base flex items-center gap-2">
                    <UploadCloud className="h-4 w-4" /> Import & Enrich
                  </CardTitle>
                  <CardDescription>Bring data in from suppliers.</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap gap-3">
                <div className="space-y-1">
                  <label className="text-xs font-semibold uppercase">Pages</label>
                  <Input className="w-20" value={pages} onChange={e => setPages(e.target.value)} />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold uppercase">&nbsp;</label>
                  <Button
                    onClick={() => run("SCRAPE", () => enqueue("SCRAPE_SUPPLIER", { supplier_id: Number(supplierId), supplier_name: supplierName, source_category: sourceCategory, pages: Number(pages) }, 70))}
                    disabled={!!busyKey}
                  >
                    {busyKey === "SCRAPE" && <Spinner />} Scrape
                  </Button>
                </div>
              </div>

              <div className="border-t pt-4">
                <h4 className="text-sm font-medium mb-2">Backfill Options (OneCheq)</h4>
                <Button
                  variant="default"
                  className="bg-indigo-600 hover:bg-indigo-700"
                  disabled={!!busyKey || supplierName.toUpperCase() !== "ONECHEQ"}
                  onClick={() => run("ONECHEQ_FULL", async () => {
                    const res = await apiPostClient<Resp>("/ops/enqueue", {
                      type: "ONECHEQ_FULL_BACKFILL",
                      payload: {
                        supplier_id: Number(supplierId),
                        supplier_name: supplierName,
                        onecheq_source: "json",
                        image_batch: 5000,
                        image_concurrency: 24
                      },
                      priority: 90
                    });
                    return `Queued OneCheq Backfill (${res.id})`;
                  })}
                >
                  {busyKey === "ONECHEQ_FULL" && <Spinner />} Full Backfill
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2"><Sparkles className="h-4 w-4 text-emerald-600" /> Enrichment</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-end gap-3">
                <div className="space-y-1">
                  <label className="text-xs font-semibold uppercase">Batch Size</label>
                  <Input className="w-24" value={batchSize} onChange={e => setBatchSize(e.target.value)} />
                </div>
                <Button
                  variant="secondary"
                  className="bg-emerald-100 text-emerald-900 hover:bg-emerald-200"
                  onClick={() => run("ENRICH", () => enqueue("ENRICH_SUPPLIER", { supplier_id: Number(supplierId), supplier_name: supplierName, source_category: sourceCategory, batch_size: Number(batchSize), delay_seconds: 0 }, 60))}
                  disabled={!!busyKey}
                >
                  {busyKey === "ENRICH" && <Spinner />} Enrich Now
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="listing" className="space-y-4 pt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2"><ShieldAlert className="h-4 w-4 text-amber-600" /> Safe Review Pipeline</CardTitle>
              <CardDescription>Two-stage publishing: Create drafts → Review → Approve.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-end gap-3 justify-between border-b pb-4">
                <div className="space-y-1">
                  <div className="font-medium text-sm">Step 1: Create Drafts</div>
                  <div className="text-xs text-muted-foreground">Generates listing payloads for validation.</div>
                </div>
                <div className="flex gap-2">
                  <Input className="w-20" placeholder="Limit" value={dryRunLimit} onChange={e => setDryRunLimit(e.target.value)} />
                  <Button
                    variant="outline"
                    onClick={() => run("DRY_RUN", async () => {
                      const res = await apiPostClient<any>("/ops/bulk/dryrun_publish", {
                        supplier_id: Number(supplierId),
                        source_category: sourceCategory,
                        limit: Number(dryRunLimit),
                        priority: 60,
                        stop_on_failure: true
                      });
                      return `Drafts queued: ${res.enqueued}`;
                    })}
                    disabled={!!busyKey}
                  >
                    {busyKey === "DRY_RUN" && <Spinner />} Create Drafts
                  </Button>
                </div>
              </div>

              <div className="flex items-end gap-3 justify-between">
                <div className="space-y-1">
                  <div className="font-medium text-sm">Step 2: Publish Approved</div>
                  <div className="text-xs text-muted-foreground">Only publishes items that passed validation.</div>
                </div>
                <div className="flex gap-2">
                  <Input className="w-20" placeholder="Limit" value={approveLimit} onChange={e => setApproveLimit(e.target.value)} />
                  <Button
                    className="bg-emerald-600 hover:bg-emerald-700 text-white"
                    onClick={() => run("APPROVE", async () => {
                      const res = await apiPostClient<any>("/ops/bulk/approve_publish", {
                        supplier_id: Number(supplierId),
                        source_category: sourceCategory,
                        limit: Number(approveLimit),
                        priority: 60,
                        stop_on_failure: true
                      });
                      return `Published: ${res.enqueued}`;
                    })}
                    disabled={!!busyKey}
                  >
                    {busyKey === "APPROVE" && <Spinner />} Publish Live
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="maintenance" className="space-y-4 pt-4">
          <Card>
            <CardHeader><CardTitle className="text-base">Sync & Reset</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-3">
                <Button variant="outline" onClick={() => run("SYNC_SOLD", () => enqueue("SYNC_SOLD_ITEMS", {}, 80))} disabled={!!busyKey}>
                  Sync Sold Items
                </Button>
                <Button variant="outline" onClick={() => run("SYNC_SELLING", () => enqueue("SYNC_SELLING_ITEMS", { limit: 50 }, 70))} disabled={!!busyKey}>
                  Sync Selling Attributes
                </Button>
              </div>
              <div className="border-t pt-4">
                <div className="font-medium text-sm mb-2 text-destructive">Destructive Zone</div>
                <div className="flex gap-3 items-center">
                  <Input className="w-24" placeholder="Limit" value={resetEnrichLimit} onChange={e => setResetEnrichLimit(e.target.value)} />
                  <Button variant="destructive" onClick={() => run("RESET", async () => {
                    if (!confirm("Reset enrichment for these items?")) return "Cancelled";
                    const res = await apiPostClient<any>("/ops/bulk/reset_enrichment", {
                      supplier_id: Number(supplierId),
                      source_category: sourceCategory,
                      limit: Number(resetEnrichLimit)
                    });
                    return `Enqueued reset: ${res.enqueued}`;
                  })} disabled={!!busyKey}>
                    Reset Enrichment
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="reprice" className="pt-4">
          <RepriceSection supplierId={supplierId} supplierName={supplierName} sourceCategory={sourceCategory} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
