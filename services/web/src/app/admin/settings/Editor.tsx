"use client";

import { useMemo, useState } from "react";
import { apiPutClient } from "../../_components/api_client";
import { buttonClass } from "../../_components/ui";

type Setting = { key: string; value: unknown; updated_at: string | null };

export function SettingsEditor({ initial }: { initial: Setting[] }) {
  const [rows, setRows] = useState<Setting[]>(initial);
  const [drafts, setDrafts] = useState<Record<string, string>>(() => {
    const d: Record<string, string> = {};
    for (const r of initial) d[r.key] = JSON.stringify(r.value, null, 2);
    return d;
  });
  const [status, setStatus] = useState<string | null>(null);

  const keys = useMemo(() => rows.map((r) => r.key), [rows]);

  async function putValue(key: string, value: unknown) {
    const updated = await apiPutClient<{ key: string; value: unknown; updated_at: string }>(`/settings/${encodeURIComponent(key)}`, { value });
    setRows((prev) => prev.map((r) => (r.key === key ? { key, value: updated.value, updated_at: updated.updated_at } : r)));
    setDrafts((prev) => ({ ...prev, [key]: JSON.stringify(updated.value, null, 2) }));
    return updated;
  }

  async function save(key: string) {
    setStatus(null);
    let parsed: unknown;
    try {
      parsed = JSON.parse(drafts[key] || "null");
    } catch {
      setStatus(`Invalid JSON for ${key}`);
      return;
    }
    try {
      const updated = await apiPutClient<{ key: string; value: unknown; updated_at: string }>(
        `/settings/${encodeURIComponent(key)}`,
        { value: parsed },
      );
      setRows((prev) => prev.map((r) => (r.key === key ? { key, value: updated.value, updated_at: updated.updated_at } : r)));
      setStatus(`Saved ${key}`);
    } catch (e) {
      setStatus(e instanceof Error ? e.message : `Failed saving ${key}`);
    }
  }

  const tmUseTemplateKey = "trademe.shipping.use_template";
  const tmTemplateIdKey = "trademe.shipping.template_id";
  const tmFooterKey = "trademe.listing.footer";

  const tmUseTemplate = Boolean(rows.find((r) => r.key === tmUseTemplateKey)?.value);
  const tmTemplateIdRaw = rows.find((r) => r.key === tmTemplateIdKey)?.value;
  const tmTemplateId = typeof tmTemplateIdRaw === "number" ? tmTemplateIdRaw : typeof tmTemplateIdRaw === "string" ? Number(tmTemplateIdRaw) : null;
  const tmFooter = typeof rows.find((r) => r.key === tmFooterKey)?.value === "string" ? (rows.find((r) => r.key === tmFooterKey)?.value as string) : "";

  return (
    <div className="space-y-3">
      {status ? <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-900">{status}</div> : null}

      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="text-sm font-semibold text-slate-900">Trade Me listing controls</div>
        <div className="mt-1 text-xs text-slate-600">
          These override `.env` at runtime (DB-backed). Safe defaults are OFF unless you explicitly enable them.
        </div>

        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <div className="text-xs font-semibold text-slate-900">Shipping template</div>
            <label className="mt-2 flex items-center gap-2 text-xs text-slate-700">
              <input
                type="checkbox"
                checked={tmUseTemplate}
                onChange={async (e) => {
                  try {
                    await putValue(tmUseTemplateKey, Boolean(e.target.checked));
                    setStatus(`Saved ${tmUseTemplateKey}`);
                  } catch (err) {
                    setStatus(err instanceof Error ? err.message : "Failed saving Trade Me shipping setting");
                  }
                }}
              />
              Use Trade Me shipping template (requires a valid template ID for this account)
            </label>

            <div className="mt-3">
              <div className="text-[11px] font-semibold text-slate-700">Template ID</div>
              <input
                type="number"
                inputMode="numeric"
                className="mt-1 w-full rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900 disabled:bg-slate-100"
                placeholder="e.g. 123456"
                disabled={!tmUseTemplate}
                value={Number.isFinite(tmTemplateId as number) && tmTemplateId != null ? String(tmTemplateId) : ""}
                onChange={(e) => {
                  const v = e.target.value.trim();
                  setDrafts((prev) => ({ ...prev, [tmTemplateIdKey]: v ? JSON.stringify(Number(v), null, 2) : "null" }));
                }}
              />
              <div className="mt-2 flex items-center justify-end">
                <button
                  type="button"
                  className={buttonClass({ variant: "primary" })}
                  disabled={!tmUseTemplate}
                  onClick={async () => {
                    try {
                      const raw = (drafts[tmTemplateIdKey] || "null").trim();
                      const parsed = JSON.parse(raw);
                      const id = typeof parsed === "number" ? parsed : typeof parsed === "string" ? Number(parsed) : null;
                      if (!id || !Number.isFinite(id) || id <= 0) {
                        setStatus("Template ID must be a positive integer");
                        return;
                      }
                      await putValue(tmTemplateIdKey, Math.trunc(id));
                      setStatus(`Saved ${tmTemplateIdKey}`);
                    } catch (err) {
                      setStatus(err instanceof Error ? err.message : `Failed saving ${tmTemplateIdKey}`);
                    }
                  }}
                >
                  Save template ID
                </button>
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <div className="text-xs font-semibold text-slate-900">Buyer-visible footer (optional)</div>
            <div className="mt-1 text-[11px] text-slate-600">
              Appended to every listing description. Leave blank for no footer.
            </div>
            <textarea
              className="mt-2 h-28 w-full rounded-md border border-slate-200 bg-white p-2 text-xs text-slate-900"
              value={tmFooter}
              onChange={(e) => {
                const v = e.target.value;
                setRows((prev) => prev.map((r) => (r.key === tmFooterKey ? { ...r, value: v } : r)));
              }}
              placeholder="e.g. Returns policy, store hours, contact instructions..."
            />
            <div className="mt-2 flex items-center justify-end">
              <button
                type="button"
                className={buttonClass({ variant: "primary" })}
                onClick={async () => {
                  try {
                    const v = (typeof rows.find((r) => r.key === tmFooterKey)?.value === "string" ? (rows.find((r) => r.key === tmFooterKey)?.value as string) : "").trim();
                    await putValue(tmFooterKey, v);
                    setStatus(`Saved ${tmFooterKey}`);
                  } catch (err) {
                    setStatus(err instanceof Error ? err.message : `Failed saving ${tmFooterKey}`);
                  }
                }}
              >
                Save footer
              </button>
            </div>
          </div>
        </div>

        <div className="mt-3 text-[11px] text-slate-500">
          Keys: <span className="font-mono">{tmUseTemplateKey}</span>, <span className="font-mono">{tmTemplateIdKey}</span>,{" "}
          <span className="font-mono">{tmFooterKey}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        {keys.map((key) => {
          const row = rows.find((r) => r.key === key)!;
          return (
            <div key={key} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="flex items-center justify-between gap-3">
                <div className="font-mono text-sm">{key}</div>
                <div className="text-xs text-slate-500">{row.updated_at || "missing"}</div>
              </div>
              <textarea
                className="mt-3 h-56 w-full rounded-lg border border-slate-200 bg-slate-50 p-3 font-mono text-xs text-slate-900"
                value={drafts[key] ?? ""}
                onChange={(e) => setDrafts((prev) => ({ ...prev, [key]: e.target.value }))}
              />
              <div className="mt-3 flex items-center justify-end">
                <button
                  type="button"
                  className={buttonClass({ variant: "primary" })}
                  onClick={() => save(key)}
                >
                  Save
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

