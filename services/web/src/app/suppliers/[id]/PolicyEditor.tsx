"use client";

import { useEffect, useState } from "react";

import { apiPutClient } from "../../_components/api_client";
import { buttonClass, cardBodyClass, cardClass, cardHeaderClass } from "../../_components/ui";

type SupplierPolicy = {
  enabled?: boolean;
  scrape?: { enabled?: boolean; category_presets?: string[] };
  enrich?: { enabled?: boolean; enrichment_policy_override?: unknown };
  publish?: { enabled?: boolean; publishing_policy_override?: unknown };
};

type SupplierPolicyResp = { supplier_id: number; supplier_name: string; policy: SupplierPolicy };

export function PolicyEditor({ supplierId }: { supplierId: number }) {
  const [data, setData] = useState<SupplierPolicyResp | null>(null);
  const [jsonText, setJsonText] = useState<string>("");
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState<boolean>(false);

  async function load() {
    setMsg(null);
    setBusy(true);
    try {
      // api_client currently only has POST/PUT; use POST to a GET-like endpoint is wrong.
      // We fetch via window.fetch to keep this component self-contained.
      const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
      const role = document.cookie.match(/(?:^|; )retailos_role=([^;]+)/)?.[1] || "root";
      const token = document.cookie.match(/(?:^|; )retailos_token=([^;]+)/)?.[1];
      const headers: Record<string, string> = { "X-RetailOS-Role": decodeURIComponent(role) };
      if (token) headers["X-RetailOS-Token"] = decodeURIComponent(token);

      const res = await fetch(`${base}/suppliers/${supplierId}/policy`, { headers });
      if (!res.ok) throw new Error(`Failed to load supplier policy: ${res.status}`);
      const j = (await res.json()) as SupplierPolicyResp;
      setData(j);
      setJsonText(JSON.stringify(j.policy || {}, null, 2));
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [supplierId]);

  async function save() {
    setMsg(null);
    setBusy(true);
    try {
      const parsed = JSON.parse(jsonText) as SupplierPolicy;
      const res = await apiPutClient<SupplierPolicyResp>(`/suppliers/${encodeURIComponent(String(supplierId))}/policy`, {
        policy: parsed,
      });
      setData(res);
      setJsonText(JSON.stringify(res.policy || {}, null, 2));
      setMsg("Saved.");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function setSimple(patch: SupplierPolicy) {
    const next = { ...(data?.policy || {}), ...patch };
    setJsonText(JSON.stringify(next, null, 2));
  }

  return (
    <div className="space-y-4">
      <div className={cardClass()}>
        <div className={cardHeaderClass()}>
          <div className="text-sm font-semibold">Supplier policy</div>
          <div className="mt-1 text-xs text-slate-600">
            Controls scheduling + worker behavior per supplier (scrape/enrich/publish), plus category presets for batch ops.
          </div>
        </div>
        <div className={cardBodyClass()}>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className={buttonClass({ variant: "secondary", disabled: busy })}
              disabled={busy}
              onClick={() => void load()}
            >
              Refresh
            </button>
            <button
              type="button"
              className={buttonClass({ variant: "primary", disabled: busy })}
              disabled={busy}
              onClick={() => void save()}
            >
              Save
            </button>
            <button
              type="button"
              className={buttonClass({ variant: "secondary", disabled: busy })}
              disabled={busy}
              onClick={() => void setSimple({ enabled: true })}
            >
              Enable supplier
            </button>
            <button
              type="button"
              className={buttonClass({ variant: "danger", disabled: busy })}
              disabled={busy}
              onClick={() => void setSimple({ enabled: false })}
            >
              Disable supplier
            </button>
          </div>

          {msg ? <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-2 text-xs text-slate-900">{msg}</div> : null}

          <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-3">
            <div className="rounded-lg border border-slate-200 bg-white p-3">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Quick toggles</div>
              <div className="mt-3 space-y-2 text-xs text-slate-700">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={!!(data?.policy?.scrape?.enabled ?? true)}
                    onChange={(e) => void setSimple({ scrape: { ...(data?.policy?.scrape || {}), enabled: e.target.checked } })}
                  />
                  Scrape enabled
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={!!(data?.policy?.enrich?.enabled ?? true)}
                    onChange={(e) => void setSimple({ enrich: { ...(data?.policy?.enrich || {}), enabled: e.target.checked } })}
                  />
                  Enrich enabled
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={!!(data?.policy?.publish?.enabled ?? true)}
                    onChange={(e) => void setSimple({ publish: { ...(data?.policy?.publish || {}), enabled: e.target.checked } })}
                  />
                  Publish enabled
                </label>
              </div>
              <div className="mt-3 text-[11px] text-slate-500">
                Note: publishing still obeys global guardrails (`store.mode`, `publishing.policy`, balance checks).
              </div>
            </div>

            <div className="lg:col-span-2">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Policy JSON</div>
              <textarea
                value={jsonText}
                onChange={(e) => setJsonText(e.target.value)}
                className="mt-2 h-[380px] w-full rounded-lg border border-slate-200 bg-white p-3 font-mono text-[12px] text-slate-900"
                spellCheck={false}
              />
              <div className="mt-2 text-[11px] text-slate-500">
                Suggested fields: `enabled`, `scrape.enabled`, `scrape.category_presets`, `enrich.enabled`, `publish.enabled`.
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className={cardClass()}>
        <div className={cardHeaderClass()}>
          <div className="text-sm font-semibold">Batch presets</div>
          <div className="mt-1 text-xs text-slate-600">
            Add supplier category presets (collection handles / category URLs / browse URLs) so you can run “scrape everything” in one click.
          </div>
        </div>
        <div className={cardBodyClass()}>
          <div className="text-xs text-slate-700">
            Current presets:{" "}
            <span className="font-mono text-[11px]">
              {JSON.stringify((data?.policy?.scrape?.category_presets || []).slice(0, 50))}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

