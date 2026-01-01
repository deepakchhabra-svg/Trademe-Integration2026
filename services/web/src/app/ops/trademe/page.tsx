import { apiGet } from "../../_components/api";
import { Badge } from "../../_components/Badge";
import { formatNZT } from "../../_components/time";
import { ValidateDraftsClient } from "./ValidateDraftsClient";

type Summary = {
  member_id: number | null;
  nickname: string | null;
  email: string | null;
  account_balance: number | null;
  pay_now_balance: number | null;
  unique_positive: number | null;
  unique_negative: number | null;
  feedback_count: number | null;
  total_items_sold: number | null;
  offline?: boolean;
  error?: string;
  balance_raw?: Record<string, unknown>;
  balance_error?: string | null;
  diagnostics?: Record<string, unknown>;
  utc?: string;
  configured?: boolean;
  auth_ok?: boolean;
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
  const configured = Boolean(summary?.configured);
  const authOk = Boolean(summary?.auth_ok) && !isOffline;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Trade Me Health</h1>
          <p className="mt-1 text-sm text-slate-600">Account balance + reputation signals (for safe publishing).</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge tone={configured ? "indigo" : "slate"}>{configured ? "configured" : "not configured"}</Badge>
          <Badge tone={authOk ? "emerald" : "red"}>{authOk ? "auth ok" : "auth failed"}</Badge>
        </div>
      </div>

      <div className="text-xs text-slate-500">
        Last checked: <span className="font-mono text-slate-700">{formatNZT(summary?.utc)}</span>
      </div>

      {error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</div>
      ) : null}
      {summary?.offline && summary?.error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{summary.error}</div>
      ) : null}

      {summary && (Number(summary.account_balance) || 0) < 0 ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 flex gap-3 items-start">
          <div className="text-red-500 mt-0.5">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" /></svg>
          </div>
          <div>
            <h3 className="text-sm font-bold text-red-900 uppercase tracking-tight">Your Trade Me account needs some love...</h3>
            <p className="mt-1 text-xs text-red-800">Your account is in debt, so you cannot create any new listings until you credit your account.</p>
            <div className="mt-2">
              <a href="https://www.trademe.co.nz/MyTradeMe/CreditAccount.aspx" target="_blank" rel="noopener noreferrer" className="text-xs font-semibold text-red-900 underline underline-offset-2 hover:no-underline font-mono">Credit my account →</a>
            </div>
          </div>
        </div>
      ) : null}

      {summary ? (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-lg border border-slate-200 bg-white p-3 flex flex-col justify-between">
            <div>
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Trade Me balance</div>
              <div className={`mt-1 text-lg font-mono font-bold ${(Number(summary.account_balance) || 0) < 0 ? "text-red-600" : "text-slate-900"}`}>
                {summary.account_balance == null ? (
                  <span className="text-slate-400 font-normal text-sm">Unavailable</span>
                ) : (
                  `${Number(summary.account_balance) < 0 ? '-' : ''}$${Math.abs(Number(summary.account_balance)).toFixed(2)}`
                )}
              </div>
            </div>
            <div className="mt-2 flex flex-wrap gap-2 border-t border-slate-50 pt-2">
              <a href="https://www.trademe.co.nz/MyTradeMe/AccountStatement.aspx" target="_blank" rel="noopener noreferrer" className="text-[10px] text-indigo-600 hover:text-indigo-800 font-semibold hover:underline bg-slate-50 px-1.5 py-0.5 rounded border border-slate-100 italic">Statement</a>
              <a href="https://www.trademe.co.nz/MyTradeMe/Sell/SalesSummary.aspx" target="_blank" rel="noopener noreferrer" className="text-[10px] text-indigo-600 hover:text-indigo-800 font-semibold hover:underline bg-slate-50 px-1.5 py-0.5 rounded border border-slate-100">Sales Summary</a>
              <a href="https://www.trademe.co.nz/MyTradeMe/Sell/WeeklySummary.aspx" target="_blank" rel="noopener noreferrer" className="text-[10px] text-indigo-600 hover:text-indigo-800 font-semibold hover:underline bg-slate-50 px-1.5 py-0.5 rounded border border-slate-100">Weekly Summary</a>
              <a href="https://www.trademe.co.nz/MyTradeMe/CreditAccount.aspx" target="_blank" rel="noopener noreferrer" className="text-[10px] font-bold text-red-600 hover:text-red-800 hover:underline bg-red-50 px-1.5 py-0.5 rounded border border-red-100">Top Up →</a>
            </div>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-3 flex flex-col justify-between">
            <div>
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Safe, instant payments (Ping)</div>
              <div className={`mt-1 text-lg font-mono font-bold ${(Number(summary.pay_now_balance) || 0) < 0 ? "text-red-600" : "text-slate-900"}`}>
                {summary.pay_now_balance == null ? (
                  <span className="text-slate-400 font-normal text-sm">Unavailable</span>
                ) : (
                  `${Number(summary.pay_now_balance) < 0 ? '-' : ''}$${Math.abs(Number(summary.pay_now_balance)).toFixed(2)}`
                )}
              </div>
            </div>
            <div className="mt-2 border-t border-slate-50 pt-2 flex gap-2">
              <a href="https://www.trademe.co.nz/Ping/Manage.aspx" target="_blank" rel="noopener noreferrer" className="text-[10px] text-indigo-600 hover:text-indigo-800 font-semibold hover:underline">Manage Ping</a>
              <span className="text-slate-300">·</span>
              <a href="https://www.trademe.co.nz/Afterpay/Manage.aspx" target="_blank" rel="noopener noreferrer" className="text-[10px] text-indigo-600 hover:text-indigo-800 font-semibold hover:underline">Afterpay</a>
            </div>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Reputation (Feedback)</div>
            <div className="mt-1 text-lg font-bold text-slate-900">{summary.feedback_count ?? <span className="text-slate-400 font-normal text-sm">Unavailable</span>}</div>
            <div className="text-[10px] text-slate-500 mt-1">
              {summary.unique_positive || 0} pos / {summary.unique_negative || 0} neg
            </div>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Items sold</div>
            <div className="mt-1 text-lg font-bold text-slate-900">{summary.total_items_sold ?? <span className="text-slate-400 font-normal text-sm">Unavailable</span>}</div>
            <div className="text-[10px] text-slate-500 mt-1">
              Total lifecycle sales
            </div>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-3 md:col-span-2">
            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Identity</div>
            <div className="mt-1 text-sm font-semibold text-slate-900">
              {summary.nickname || "-"}
            </div>
            <div className="text-[10px] text-slate-500">
              {summary.email || "-"} · member {summary.member_id ?? "-"}
            </div>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Ecosystem</div>
            <div className="mt-1 grid grid-cols-2 gap-x-2 gap-y-1">
              <a href="https://www.motorweb.co.nz" target="_blank" rel="noopener noreferrer" className="text-[9px] font-bold text-slate-600 hover:text-indigo-600">MotorWeb ↗</a>
              <a href="https://www.holidayhouses.co.nz" target="_blank" rel="noopener noreferrer" className="text-[9px] font-bold text-slate-600 hover:text-indigo-600">Holiday Houses ↗</a>
              <a href="https://www.findsomeone.co.nz" target="_blank" rel="noopener noreferrer" className="text-[9px] font-bold text-slate-600 hover:text-indigo-600">FindSomeone ↗</a>
              <a href="https://www.trademe.co.nz/insurance" target="_blank" rel="noopener noreferrer" className="text-[9px] font-bold text-slate-600 hover:text-indigo-600">Insurance ↗</a>
            </div>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Status</div>
            <div className="mt-1 flex items-center gap-2">
              <Badge tone={authOk ? "emerald" : "red"}>{authOk ? "Ok" : "Fail"}</Badge>
              <div className="text-[9px] text-slate-400">
                {formatNZT(summary?.utc).split(',')[1]}
              </div>
            </div>
          </div>
          {summary.balance_error ? (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900 md:col-span-2 xl:col-span-4">
              Balance note: {summary.balance_error}
            </div>
          ) : null}
          {summary.balance_raw && Object.keys(summary.balance_raw || {}).length ? (
            <div className="rounded-lg border border-slate-200 bg-white p-3 md:col-span-2 xl:col-span-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Balance</div>
              <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-2 text-[11px] text-slate-900">
                {JSON.stringify(summary.balance_raw, null, 2)}
              </pre>
            </div>
          ) : null}

          {summary.diagnostics ? (
            <div className="rounded-lg border border-slate-200 bg-white p-3 md:col-span-2 xl:col-span-4">
              <details>
                <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Diagnostics (safe)
                </summary>
                <div className="mt-2 text-xs text-slate-600">
                  Shows endpoint availability + missing fields. No keys/tokens are ever returned here.
                </div>
                <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-2 text-[11px] text-slate-900">
                  {JSON.stringify(summary.diagnostics, null, 2)}
                </pre>
              </details>
            </div>
          ) : null}
        </div>
      ) : null}

      <ValidateDraftsClient />
    </div>
  );
}

