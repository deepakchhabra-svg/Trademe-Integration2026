import { apiGet } from "../../_components/api";
import { Badge } from "../../_components/Badge";

type Setting = { key: string; value: unknown; updated_at: string | null };

const DEFAULT_KEYS = [
  "scheduler.scrape",
  "scheduler.enrich",
  "enrichment.policy",
  "store.mode",
];

export default async function SettingsPage() {
  // Minimal read-only view for now; write UI comes next (root-only endpoint already exists).
  const settings: Setting[] = [];
  for (const key of DEFAULT_KEYS) {
    try {
      settings.push(await apiGet<Setting>(`/settings/${encodeURIComponent(key)}`));
    } catch {
      settings.push({ key, value: null, updated_at: null });
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Settings (root)</h1>
          <p className="mt-1 text-sm text-slate-600">
            Store modes, scheduler throttles, and policy knobs. (Write controls coming next.)
          </p>
        </div>
        <Badge tone="amber">root only</Badge>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        {settings.map((s) => (
          <div key={s.key} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div className="font-mono text-sm">{s.key}</div>
              <div className="text-xs text-slate-500">{s.updated_at || "missing"}</div>
            </div>
            <pre className="mt-3 max-h-[520px] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-900">
              {JSON.stringify(s.value, null, 2)}
            </pre>
          </div>
        ))}
      </div>
    </div>
  );
}

