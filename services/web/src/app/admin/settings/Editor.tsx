"use client";

import { useMemo, useState } from "react";
import { apiPutClient } from "../../_components/api_client";

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

  return (
    <div className="space-y-3">
      {status ? <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-900">{status}</div> : null}

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
                  className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white"
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

