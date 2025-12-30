import { apiGet } from "../../_components/api";
import { Badge } from "../../_components/Badge";

type Summary = {
  member_id: number | null;
  nickname: string | null;
  email: string | null;
  account_balance: number;
  pay_now_balance: number;
  unique_positive: number;
  unique_negative: number;
  feedback_count: number;
  total_items_sold: number;
  offline?: boolean;
  error?: string;
  balance_raw?: Record<string, unknown>;
};

export default async function TradeMeHealthPage() {
  let summary: Summary | null = null;
  let error: string | null = null;

  try {
    summary = await apiGet<Summary>("/trademe/account_summary");
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to load Trade Me summary";
  }

  const isOffline = Boolean(summary?.offline) || Boolean(error);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Trade Me Health</h1>
          <p className="mt-1 text-sm text-slate-600">Account balance + reputation signals (for safe publishing).</p>
        </div>
        <Badge tone={!isOffline ? "emerald" : "red"}>{!isOffline ? "connected" : "offline"}</Badge>
      </div>

      {error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</div>
      ) : null}
      {summary?.offline && summary?.error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{summary.error}</div>
      ) : null}

      {summary ? (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Account balance</div>
            <div className="mt-1 text-sm text-slate-900">${Number(summary.account_balance || 0).toFixed(2)}</div>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">PayNow balance</div>
            <div className="mt-1 text-sm text-slate-900">${Number(summary.pay_now_balance || 0).toFixed(2)}</div>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Feedback</div>
            <div className="mt-1 text-sm text-slate-900">{summary.feedback_count}</div>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Items sold</div>
            <div className="mt-1 text-sm text-slate-900">{summary.total_items_sold}</div>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Unique positive</div>
            <div className="mt-1 text-sm text-slate-900">{summary.unique_positive}</div>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Unique negative</div>
            <div className="mt-1 text-sm text-slate-900">{summary.unique_negative}</div>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-3 md:col-span-2">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Identity</div>
            <div className="mt-1 text-sm text-slate-900">
              {summary.nickname || "-"} · {summary.email || "-"} · member {summary.member_id ?? "-"}
            </div>
          </div>
          {summary.balance_raw ? (
            <div className="rounded-lg border border-slate-200 bg-white p-3 md:col-span-2 xl:col-span-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Balance</div>
              <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-2 text-[11px] text-slate-900">
                {JSON.stringify(summary.balance_raw, null, 2)}
              </pre>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

