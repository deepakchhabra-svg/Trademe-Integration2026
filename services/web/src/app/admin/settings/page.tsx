import { apiGet } from "../../_components/api";
import { Badge } from "../../_components/Badge";
import { TokenSetter } from "../../_components/TokenSetter";
import { SettingsEditor } from "./Editor";

type Setting = { key: string; value: unknown; updated_at: string | null };

const DEFAULT_KEYS = [
  "scheduler.scrape",
  "scheduler.enrich",
  "enrichment.policy",
  "store.mode",
];

export default async function SettingsPage() {
  // Root-only: read server-side, write via client component (PUT /settings/{key}).
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

      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <TokenSetter />
      </div>

      <SettingsEditor initial={settings} />
    </div>
  );
}

