import { apiGet } from "./_components/api";
import { WorkbenchClient } from "./WorkbenchClient";

type OpsSummary = {
  utc?: string;
  commands: { total: number; pending: number; executing: number; human_required: number; failed: number };
  vaults: {
    raw_total: number;
    raw_present: number;
    enriched_total: number;
    enriched_ready: number;
    listings_total: number;
    listings_dry_run: number;
    listings_live: number;
  };
  orders: { total: number; pending_fulfillment: number };
};

export default async function Home() {
  let summary: OpsSummary | null = null;
  let err: unknown = null;
  try {
    summary = await apiGet<OpsSummary>("/ops/summary");
  } catch (e) {
    err = e;
  }

  if (summary) return <WorkbenchClient initial={summary} />;

  const msg = err instanceof Error ? err.message : String(err || "");
  const looksForbidden = msg.includes("403") || msg.toLowerCase().includes("forbidden");
  if (!looksForbidden) throw err;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Ops Workbench</h1>
        <p className="mt-1 text-sm text-slate-600">
          Access required: this page needs <span className="font-mono">POWER</span> role.
        </p>
      </div>

      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
        <div className="font-semibold">You’re not authenticated for operator endpoints yet.</div>
        <div className="mt-1">
          Go to{" "}
          <a className="underline" href="/access">
            Access &amp; tokens
          </a>{" "}
          and paste your <span className="font-mono">RETAIL_OS_POWER_TOKEN</span> (from your <span className="font-mono">.env</span>).
        </div>
        <div className="mt-2 text-[11px] opacity-80">API response: {msg}</div>
      </div>
    </div>
  );
}
