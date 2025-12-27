import Link from "next/link";

import { apiGet } from "../../_components/api";
import { Badge } from "../../_components/Badge";

type Alert = { severity: "low" | "medium" | "high"; code: string; title: string; detail: string };
type AlertsResponse = { alerts: Alert[]; count: number };

export default async function AlertsPage() {
  const data = await apiGet<AlertsResponse>("/ops/alerts");
  const high = data.alerts.filter((a) => a.severity === "high").length;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Alerts</h1>
          <p className="mt-1 text-sm text-slate-600">Computed alerts so nothing critical hides in logs.</p>
        </div>
        <div className="flex gap-2">
          <Badge tone={high ? "red" : "emerald"}>high {high}</Badge>
          <Badge tone="blue">total {data.count}</Badge>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="divide-y divide-slate-100">
          {data.alerts.length ? (
            data.alerts.map((a) => (
              <div key={a.code} className="p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-sm font-semibold">{a.title}</div>
                    <div className="mt-1 text-sm text-slate-700">{a.detail}</div>
                    <div className="mt-1 font-mono text-[11px] text-slate-500">{a.code}</div>
                  </div>
                  <Badge tone={a.severity === "high" ? "red" : a.severity === "medium" ? "amber" : "slate"}>
                    {a.severity}
                  </Badge>
                </div>
                {a.code === "COMMANDS_HUMAN_REQUIRED" ? (
                  <div className="mt-2 text-xs text-slate-600">
                    Go to <Link className="underline" href="/ops/inbox">Inbox</Link> to action commands.
                  </div>
                ) : null}
              </div>
            ))
          ) : (
            <div className="p-4 text-sm text-slate-600">No alerts.</div>
          )}
        </div>
      </div>
    </div>
  );
}

