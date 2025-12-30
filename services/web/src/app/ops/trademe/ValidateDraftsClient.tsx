"use client";

import { useState } from "react";
import { apiPostClient } from "../../_components/api_client";
import { buttonClass } from "../../_components/ui";
import { formatNZT } from "../../_components/time";

type ResultRow = {
  internal_product_id: number;
  sku: string;
  supplier_product_id: number | null;
  ok: boolean;
  error?: string;
  response?: Record<string, unknown>;
};

type Resp = {
  utc: string;
  configured: boolean;
  auth_ok: boolean;
  error?: string;
  results: ResultRow[];
};

export function ValidateDraftsClient() {
  const [supplierId, setSupplierId] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [resp, setResp] = useState<Resp | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function run() {
    if (busy) return;
    setBusy(true);
    setErr(null);
    try {
      const sid = supplierId.trim() ? Number(supplierId.trim()) : null;
      const out = await apiPostClient<Resp>("/trademe/validate_drafts", {
        supplier_id: sid && Number.isFinite(sid) ? sid : null,
        limit: 10,
      });
      setResp(out);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Validate failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-sm font-semibold">Validate drafts (real Trade Me)</div>
          <div className="mt-1 text-xs text-slate-600">
            Runs Trade Me payload validation for a sample of 10 items. If keys are missing, it will show “Not configured”.
          </div>
        </div>

        <div className="flex flex-wrap items-end gap-2">
          <label className="text-xs text-slate-600">
            <div className="mb-1 font-semibold uppercase tracking-wide">Supplier ID (optional)</div>
            <input
              className="w-28 rounded-md border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-900"
              value={supplierId}
              onChange={(e) => setSupplierId(e.target.value)}
              placeholder="e.g. 1"
            />
          </label>
          <button type="button" className={buttonClass({ variant: "primary", disabled: busy })} onClick={run}>
            {busy ? "Validating…" : "Validate 10"}
          </button>
        </div>
      </div>

      {err ? <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{err}</div> : null}

      {resp ? (
        <div className="mt-4 space-y-3">
          <div className="text-xs text-slate-500">
            Checked: <span className="font-mono text-slate-700">{formatNZT(resp.utc)}</span> ·{" "}
            <span className="font-semibold">{resp.configured ? "Configured" : "Not configured"}</span>
          </div>

          {resp.error ? <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">{resp.error}</div> : null}

          <div className="overflow-x-auto rounded-lg border border-slate-200">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-3 py-2">Internal</th>
                  <th className="px-3 py-2">SKU</th>
                  <th className="px-3 py-2">OK</th>
                  <th className="px-3 py-2">Notes</th>
                </tr>
              </thead>
              <tbody>
                {resp.results.map((r) => (
                  <tr key={r.internal_product_id} className="border-t border-slate-100">
                    <td className="px-3 py-2 font-mono text-xs">{r.internal_product_id}</td>
                    <td className="px-3 py-2 font-mono text-xs">{r.sku}</td>
                    <td className="px-3 py-2">{r.ok ? "PASS" : "FAIL"}</td>
                    <td className="px-3 py-2 text-xs text-slate-700">{r.error || (r.ok ? "Validated" : "Blocked")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </div>
  );
}

