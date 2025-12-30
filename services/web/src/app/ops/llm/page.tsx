import { apiGet } from "../../_components/api";
import { PageHeader } from "../../../components/ui/PageHeader";
import { Badge } from "../../_components/Badge";

type LlmHealth = {
  provider: string | null;
  active: boolean;
  configured: boolean;
  model?: string;
  models_sample?: string[];
  error?: string;
};

export default async function LlmHealthPage() {
  let data: LlmHealth | null = null;
  let error: string | null = null;
  try {
    data = await apiGet<LlmHealth>("/llm/health");
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to load LLM health";
  }

  const ok = Boolean(data?.configured) && !data?.error && !error;

  return (
    <div className="space-y-4">
      <PageHeader
        title="LLM Health"
        subtitle="Reality-mode diagnostics for enrichment. If this is not configured, AI enrichment must block (no silent fallbacks)."
        actions={<Badge tone={ok ? "emerald" : "red"}>{ok ? "healthy" : "not ready"}</Badge>}
      />

      {error ? <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</div> : null}
      {data?.error ? <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">{data.error}</div> : null}

      {data ? (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <div className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Provider</div>
            <div className="mt-1 text-sm text-slate-900">{data.provider || "-"}</div>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Model</div>
            <div className="mt-1 text-sm text-slate-900">{data.model || "-"}</div>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-3 md:col-span-2">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">How to fix</div>
            <div className="mt-1 text-sm text-slate-900">
              Set <span className="font-mono text-xs">GEMINI_API_KEY</span> (or <span className="font-mono text-xs">OPENAI_API_KEY</span>). For Gemini, optionally set{" "}
              <span className="font-mono text-xs">GEMINI_MODEL</span> to a model shown below.
            </div>
          </div>
          {Array.isArray(data.models_sample) && data.models_sample.length ? (
            <div className="rounded-lg border border-slate-200 bg-white p-3 md:col-span-2">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Available Gemini models (sample)</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {data.models_sample.map((m) => (
                  <span key={m} className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-xs font-mono text-slate-900">
                    {m}
                  </span>
                ))}
              </div>
              <div className="mt-2 text-[11px] text-slate-500">
                Run <span className="font-mono">python scripts/llm_health.py</span> for a local CLI view.
              </div>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

