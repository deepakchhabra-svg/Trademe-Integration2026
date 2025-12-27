"use client";

import { useEffect, useState } from "react";
import { apiGetClient, apiPostClient } from "../../_components/api_client";

type Resp = { id: string; status: string };
type Supplier = { id: number; name: string };

function Spinner() {
  return (
    <span
      aria-hidden="true"
      className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-white/30 border-t-white"
    />
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="text-sm font-semibold">{title}</div>
      <div className="mt-3">{children}</div>
    </div>
  );
}

export function BulkOpsForm({ suppliers }: { suppliers: Supplier[] }) {
  const [supplierId, setSupplierId] = useState<string>("");
  const [supplierName, setSupplierName] = useState<string>("");
  const [sourceCategory, setSourceCategory] = useState<string>("");
  const [pages, setPages] = useState<string>("1");
  const [batchSize, setBatchSize] = useState<string>("25");
  const [dryRunLimit, setDryRunLimit] = useState<string>("50");
  const [approveLimit, setApproveLimit] = useState<string>("50");
  const [resetEnrichLimit, setResetEnrichLimit] = useState<string>("200");
  const [scanLimit, setScanLimit] = useState<string>("100");
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
    return `Enqueued ${type} (${res.id.slice(0, 12)})`;
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
    <div className="space-y-4">
      {msg ? <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-900">{msg}</div> : null}

      <Section title="How to use (recommended flow)">
        <ol className="list-decimal space-y-2 pl-5 text-sm text-slate-700">
          <li>
            Pick supplier + category scope below. Then run <span className="font-semibold">SCRAPE_SUPPLIER</span>.
          </li>
          <li>
            Run <span className="font-semibold">ENRICH_SUPPLIER</span> to populate Vault 2 (copy + internal products).
          </li>
          <li>
            Run <span className="font-semibold">DRY_RUN publish</span> and review in Vault 3 (status=DRY_RUN).
          </li>
          <li>
            Run <span className="font-semibold">Approve publish</span> to publish real listings (drift-safe + policy-safe).
          </li>
        </ol>
        <div className="mt-3 text-[11px] text-slate-500">
          Tip: if you’re unsure, start with pages=1 and limits=10 to validate end-to-end without flooding the queue.
        </div>
      </Section>

      <Section title="Scope">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <label className="text-xs text-slate-600 md:col-span-2">
            <div className="mb-1 font-semibold uppercase tracking-wide">Supplier picker</div>
            <select
              className="w-full rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
              value={supplierId && supplierName ? `${supplierId}:${supplierName}` : ""}
              onChange={(e) => {
                const v = e.target.value;
                if (!v) {
                  setSupplierId("");
                  setSupplierName("");
                  return;
                }
                const [id, name] = v.split(":");
                setSupplierId(id);
                setSupplierName(name);
              }}
            >
              <option value="">Select supplier…</option>
              {suppliers.map((s) => (
                <option key={s.id} value={`${s.id}:${s.name}`}>
                  {s.name} (id {s.id})
                </option>
              ))}
            </select>
            <div className="mt-1 text-[11px] text-slate-500">
              ONECHEQ / CASH_CONVERTERS / NOEL_LEEMING are supported.
            </div>
            <div className="mt-2 rounded-lg border border-slate-200 bg-slate-50 p-2 text-[11px] text-slate-700">
              <div className="font-semibold">Category presets (from Supplier policy)</div>
              {presetsMsg ? <div className="mt-1 text-amber-800">{presetsMsg}</div> : null}
              <div className="mt-1">
                {categoryPresets.length ? (
                  <div className="flex flex-wrap gap-1.5">
                    {categoryPresets.slice(0, 12).map((p) => (
                      <button
                        key={p}
                        type="button"
                        className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[11px] text-slate-900 hover:bg-slate-50"
                        onClick={() => setSourceCategory(p)}
                        disabled={!!busyKey}
                      >
                        {p}
                      </button>
                    ))}
                    {categoryPresets.length > 12 ? (
                      <span className="text-[11px] text-slate-500">+{categoryPresets.length - 12} more</span>
                    ) : null}
                  </div>
                ) : (
                  <div className="text-slate-600">No presets set yet. Add them in Suppliers → (supplier) → Supplier policy.</div>
                )}
              </div>
            </div>
          </label>
          <label className="text-xs text-slate-600">
            <div className="mb-1 font-semibold uppercase tracking-wide">supplier_id</div>
            <input
              className="w-full rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
              value={supplierId}
              onChange={(e) => setSupplierId(e.target.value)}
              placeholder="e.g. 1"
            />
          </label>
          <label className="text-xs text-slate-600">
            <div className="mb-1 font-semibold uppercase tracking-wide">supplier_name</div>
            <input
              className="w-full rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
              value={supplierName}
              onChange={(e) => setSupplierName(e.target.value)}
              placeholder="e.g. CASH_CONVERTERS"
            />
          </label>
          <label className="text-xs text-slate-600 md:col-span-2">
            <div className="mb-1 font-semibold uppercase tracking-wide">source_category</div>
            <input
              className="w-full rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
              value={sourceCategory}
              onChange={(e) => setSourceCategory(e.target.value)}
              placeholder="CC browse_url / NL category_url / OC collection handle"
            />
            <div className="mt-1 text-[11px] text-slate-500">
              ONECHEQ: collection handle (e.g. smartphones-and-mobilephones) · CASH_CONVERTERS: browse URL · NOEL_LEEMING: category URL
            </div>
          </label>
        </div>
      </Section>

      <Section title="Batch-first (no manual clicking)">
        <div className="text-xs text-slate-600">
          Uses supplier <span className="font-semibold">category presets</span> (recommended for scale). This enqueues a batch of commands
          so you don’t have to click per category.
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button
            type="button"
            disabled={!!busyKey || !categoryPresets.length}
            className={`rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white ${
              busyKey || !categoryPresets.length ? "cursor-not-allowed opacity-60" : "hover:bg-slate-800"
            }`}
            onClick={() =>
              run("SCRAPE_ALL_PRESETS", async () => {
                const sid = supplierId ? Number(supplierId) : undefined;
                const sname = supplierName || undefined;
                const pgs = Number(pages || "1");
                const presets = categoryPresets.slice(0, 50);
                let ok = 0;
                for (const cat of presets) {
                  await enqueue(
                    "SCRAPE_SUPPLIER",
                    { supplier_id: sid, supplier_name: sname, source_category: cat, pages: pgs },
                    70,
                  );
                  ok += 1;
                  setMsg(`Working: SCRAPE_ALL_PRESETS… ${ok}/${presets.length}`);
                }
                return `Enqueued SCRAPE_SUPPLIER for ${ok} categories (from presets)`;
              })
            }
          >
            {busyKey === "SCRAPE_ALL_PRESETS" ? (
              <span className="inline-flex items-center gap-2">
                <Spinner /> Enqueuing batch…
              </span>
            ) : (
              "Scrape all presets"
            )}
          </button>

          <button
            type="button"
            disabled={!!busyKey || !categoryPresets.length}
            className={`rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white ${
              busyKey || !categoryPresets.length ? "cursor-not-allowed opacity-60" : "hover:bg-emerald-700"
            }`}
            onClick={() =>
              run("ENRICH_ALL_PRESETS", async () => {
                const sid = supplierId ? Number(supplierId) : undefined;
                const sname = supplierName || undefined;
                const bs = Number(batchSize || "25");
                const presets = categoryPresets.slice(0, 50);
                let ok = 0;
                for (const cat of presets) {
                  await enqueue(
                    "ENRICH_SUPPLIER",
                    { supplier_id: sid, supplier_name: sname, source_category: cat, batch_size: bs, delay_seconds: 0 },
                    60,
                  );
                  ok += 1;
                  setMsg(`Working: ENRICH_ALL_PRESETS… ${ok}/${presets.length}`);
                }
                return `Enqueued ENRICH_SUPPLIER for ${ok} categories (from presets)`;
              })
            }
          >
            {busyKey === "ENRICH_ALL_PRESETS" ? (
              <span className="inline-flex items-center gap-2">
                <Spinner /> Enqueuing batch…
              </span>
            ) : (
              "Enrich all presets"
            )}
          </button>

          {!categoryPresets.length ? (
            <span className="text-[11px] text-slate-500">Disabled until presets exist.</span>
          ) : (
            <span className="text-[11px] text-slate-500">Will enqueue up to 50 categories per click.</span>
          )}
        </div>
      </Section>

      <Section title="Scrape supplier (category-scoped)">
        <div className="flex flex-wrap items-end gap-2">
          <label className="text-xs text-slate-600">
            <div className="mb-1 font-semibold uppercase tracking-wide">pages</div>
            <input
              className="w-20 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
              value={pages}
              onChange={(e) => setPages(e.target.value)}
            />
          </label>
          <button
            type="button"
            disabled={!!busyKey}
            aria-busy={busyKey === "SCRAPE_SUPPLIER"}
            className={`rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white ${
              busyKey ? "cursor-not-allowed opacity-60" : "hover:bg-slate-800"
            }`}
            onClick={() =>
              run("SCRAPE_SUPPLIER", () =>
                enqueue(
                "SCRAPE_SUPPLIER",
                {
                  supplier_id: supplierId ? Number(supplierId) : undefined,
                  supplier_name: supplierName || undefined,
                  source_category: sourceCategory || undefined,
                  pages: Number(pages || "1"),
                },
                70,
                ),
              )
            }
          >
            {busyKey === "SCRAPE_SUPPLIER" ? (
              <span className="inline-flex items-center gap-2">
                <Spinner /> Enqueuing…
              </span>
            ) : (
              "Enqueue SCRAPE_SUPPLIER"
            )}
          </button>
        </div>
      </Section>

      <Section title="Enrich supplier (category-scoped)">
        <div className="flex flex-wrap items-end gap-2">
          <label className="text-xs text-slate-600">
            <div className="mb-1 font-semibold uppercase tracking-wide">batch_size</div>
            <input
              className="w-24 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
              value={batchSize}
              onChange={(e) => setBatchSize(e.target.value)}
            />
          </label>
          <button
            type="button"
            disabled={!!busyKey}
            aria-busy={busyKey === "ENRICH_SUPPLIER"}
            className={`rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white ${
              busyKey ? "cursor-not-allowed opacity-60" : "hover:bg-emerald-700"
            }`}
            onClick={() =>
              run("ENRICH_SUPPLIER", () =>
                enqueue(
                "ENRICH_SUPPLIER",
                {
                  supplier_id: supplierId ? Number(supplierId) : undefined,
                  supplier_name: supplierName || undefined,
                  source_category: sourceCategory || undefined,
                  batch_size: Number(batchSize || "25"),
                  delay_seconds: 0,
                },
                60,
                ),
              )
            }
          >
            {busyKey === "ENRICH_SUPPLIER" ? (
              <span className="inline-flex items-center gap-2">
                <Spinner /> Enqueuing…
              </span>
            ) : (
              "Enqueue ENRICH_SUPPLIER"
            )}
          </button>
        </div>
      </Section>

      <Section title="Marketplace sync (ops)">
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            disabled={!!busyKey}
            aria-busy={busyKey === "SYNC_SOLD_ITEMS"}
            className={`rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-900 ${
              busyKey ? "cursor-not-allowed opacity-60" : "hover:bg-slate-50"
            }`}
            onClick={() => run("SYNC_SOLD_ITEMS", () => enqueue("SYNC_SOLD_ITEMS", {}, 80))}
          >
            {busyKey === "SYNC_SOLD_ITEMS" ? (
              <span className="inline-flex items-center gap-2">
                <span
                  aria-hidden="true"
                  className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-slate-300 border-t-slate-900"
                />
                Enqueuing…
              </span>
            ) : (
              "Enqueue SYNC_SOLD_ITEMS"
            )}
          </button>
          <button
            type="button"
            disabled={!!busyKey}
            aria-busy={busyKey === "SYNC_SELLING_ITEMS"}
            className={`rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-900 ${
              busyKey ? "cursor-not-allowed opacity-60" : "hover:bg-slate-50"
            }`}
            onClick={() => run("SYNC_SELLING_ITEMS", () => enqueue("SYNC_SELLING_ITEMS", { limit: 50 }, 70))}
          >
            {busyKey === "SYNC_SELLING_ITEMS" ? (
              <span className="inline-flex items-center gap-2">
                <span
                  aria-hidden="true"
                  className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-slate-300 border-t-slate-900"
                />
                Enqueuing…
              </span>
            ) : (
              "Enqueue SYNC_SELLING_ITEMS"
            )}
          </button>
        </div>
      </Section>

      <Section title="Bulk dry-run publish (safe review queue)">
        <div className="flex flex-wrap items-end gap-2">
          <label className="text-xs text-slate-600">
            <div className="mb-1 font-semibold uppercase tracking-wide">limit</div>
            <input
              className="w-24 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
              value={dryRunLimit}
              onChange={(e) => setDryRunLimit(e.target.value)}
            />
          </label>
          <button
            type="button"
            disabled={!!busyKey}
            aria-busy={busyKey === "BULK_DRY_RUN_PUBLISH"}
            className={`rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white ${
              busyKey ? "cursor-not-allowed opacity-60" : "hover:bg-slate-800"
            }`}
            onClick={() =>
              run("BULK_DRY_RUN_PUBLISH", async () => {
                const res = await apiPostClient<{ enqueued: number; skipped_existing_cmd: number; skipped_already_listed: number }>(
                  "/ops/bulk/dryrun_publish",
                  {
                    supplier_id: supplierId ? Number(supplierId) : undefined,
                    source_category: sourceCategory || undefined,
                    limit: Number(dryRunLimit || "50"),
                    priority: 60,
                  },
                );
                return `Dry-run queued: enqueued=${res.enqueued}, skipped_existing_cmd=${res.skipped_existing_cmd}, skipped_already_listed=${res.skipped_already_listed}`;
              })
            }
          >
            {busyKey === "BULK_DRY_RUN_PUBLISH" ? (
              <span className="inline-flex items-center gap-2">
                <Spinner /> Enqueuing…
              </span>
            ) : (
              "Enqueue DRY_RUN publish"
            )}
          </button>
        </div>
        <div className="mt-2 text-[11px] text-slate-500">
          Creates `PUBLISH_LISTING` commands with `dry_run=true` for review (skips Live/DRY_RUN and duplicates).
        </div>
      </Section>

      <Section title="Bulk approve publish (DRY_RUN → PUBLISH)">
        <div className="flex flex-wrap items-end gap-2">
          <label className="text-xs text-slate-600">
            <div className="mb-1 font-semibold uppercase tracking-wide">limit</div>
            <input
              className="w-24 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
              value={approveLimit}
              onChange={(e) => setApproveLimit(e.target.value)}
            />
          </label>
          <button
            type="button"
            disabled={!!busyKey}
            aria-busy={busyKey === "BULK_APPROVE_PUBLISH"}
            className={`rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white ${
              busyKey ? "cursor-not-allowed opacity-60" : "hover:bg-slate-800"
            }`}
            onClick={() =>
              run("BULK_APPROVE_PUBLISH", async () => {
                const res = await apiPostClient<{
                  enqueued: number;
                  skipped_existing_cmd: number;
                  skipped_drift: number;
                  skipped_missing_metadata: number;
                  skipped_bad_dryrun_id: number;
                  store_mode: string;
                }>("/ops/bulk/approve_publish", {
                  supplier_id: supplierId ? Number(supplierId) : undefined,
                  source_category: sourceCategory || undefined,
                  limit: Number(approveLimit || "50"),
                  priority: 60,
                });
                return `Approved publish queued: enqueued=${res.enqueued}, skipped_drift=${res.skipped_drift}, skipped_existing_cmd=${res.skipped_existing_cmd} (store_mode=${res.store_mode})`;
              })
            }
          >
            {busyKey === "BULK_APPROVE_PUBLISH" ? (
              <span className="inline-flex items-center gap-2">
                <Spinner /> Enqueuing…
              </span>
            ) : (
              "Enqueue PUBLISH from DRY_RUN"
            )}
          </button>
        </div>
        <div className="mt-2 text-[11px] text-slate-500">
          Only enqueues real `PUBLISH_LISTING` if supplier snapshot hash matches the DRY_RUN snapshot (drift-safe). Disabled in
          store modes HOLIDAY/PAUSED.
        </div>
      </Section>

      <Section title="Bulk reset enrichment (requeue copy generation)">
        <div className="flex flex-wrap items-end gap-2">
          <label className="text-xs text-slate-600">
            <div className="mb-1 font-semibold uppercase tracking-wide">limit</div>
            <input
              className="w-24 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
              value={resetEnrichLimit}
              onChange={(e) => setResetEnrichLimit(e.target.value)}
            />
          </label>
          <button
            type="button"
            disabled={!!busyKey}
            aria-busy={busyKey === "BULK_RESET_ENRICHMENT"}
            className={`rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-900 ${
              busyKey ? "cursor-not-allowed opacity-60" : "hover:bg-slate-50"
            }`}
            onClick={() =>
              run("BULK_RESET_ENRICHMENT", async () => {
                const res = await apiPostClient<{ enqueued: number }>("/ops/bulk/reset_enrichment", {
                  supplier_id: supplierId ? Number(supplierId) : undefined,
                  source_category: sourceCategory || undefined,
                  limit: Number(resetEnrichLimit || "200"),
                  priority: 60,
                });
                return `Reset enrichment queued: enqueued=${res.enqueued}`;
              })
            }
          >
            {busyKey === "BULK_RESET_ENRICHMENT" ? (
              <span className="inline-flex items-center gap-2">
                <span
                  aria-hidden="true"
                  className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-slate-300 border-t-slate-900"
                />
                Enqueuing…
              </span>
            ) : (
              "Enqueue RESET_ENRICHMENT"
            )}
          </button>
        </div>
      </Section>

      <Section title="Bulk competitor scan (pricing intelligence)">
        <div className="flex flex-wrap items-end gap-2">
          <label className="text-xs text-slate-600">
            <div className="mb-1 font-semibold uppercase tracking-wide">limit</div>
            <input
              className="w-24 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
              value={scanLimit}
              onChange={(e) => setScanLimit(e.target.value)}
            />
          </label>
          <button
            type="button"
            disabled={!!busyKey}
            aria-busy={busyKey === "BULK_SCAN_COMPETITORS"}
            className={`rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white ${
              busyKey ? "cursor-not-allowed opacity-60" : "hover:bg-slate-800"
            }`}
            onClick={() =>
              run("BULK_SCAN_COMPETITORS", async () => {
                const res = await apiPostClient<{ enqueued: number }>("/ops/bulk/scan_competitors", {
                  supplier_id: supplierId ? Number(supplierId) : undefined,
                  source_category: sourceCategory || undefined,
                  status: "Live",
                  limit: Number(scanLimit || "100"),
                  priority: 40,
                });
                return `Competitor scans queued: enqueued=${res.enqueued}`;
              })
            }
          >
            {busyKey === "BULK_SCAN_COMPETITORS" ? (
              <span className="inline-flex items-center gap-2">
                <Spinner /> Enqueuing…
              </span>
            ) : (
              "Enqueue SCAN_COMPETITORS"
            )}
          </button>
        </div>
      </Section>
    </div>
  );
}

