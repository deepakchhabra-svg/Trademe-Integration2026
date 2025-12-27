import Link from "next/link";

import { apiGet } from "../../_components/api";
import { Badge } from "../../_components/Badge";
import { InboxCommandActions } from "./Actions";

type Inbox = {
  offline?: boolean;
  error?: string;
  counts: {
    commands_human_required: number;
    commands_retrying: number;
    jobs_failed: number;
    orders_pending: number;
  };
  groups_human_required?: Array<{
    type: string;
    error_code: string;
    count: number;
    latest_updated_at: string | null;
  }>;
  groups_retrying?: Array<{
    type: string;
    status: string;
    count: number;
    latest_updated_at: string | null;
  }>;
  commands_human_required: Array<{
    id: string;
    type: string;
    status: string;
    error_code: string | null;
    error_message: string | null;
    last_error: string | null;
    updated_at: string | null;
  }>;
  commands_retrying: Array<{
    id: string;
    type: string;
    status: string;
    attempts: number;
    max_attempts: number;
    last_error: string | null;
    updated_at: string | null;
  }>;
  jobs_failed: Array<{ id: number; job_type: string | null; status: string | null; start_time: string | null; end_time: string | null; summary: string | null }>;
  orders_pending: Array<{ id: number; tm_order_ref: string; buyer_name: string | null; sold_price: number | null; created_at: string | null }>;
};

export default async function InboxPage() {
  const inbox = await apiGet<Inbox>("/ops/inbox");
  const humanGroups = inbox.groups_human_required || [];
  const retryGroups = inbox.groups_retrying || [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Operator Inbox</h1>
          <p className="mt-1 text-sm text-slate-600">Everything that needs attention, in one place.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge tone={inbox.counts.commands_human_required ? "red" : "emerald"}>human {inbox.counts.commands_human_required}</Badge>
          <Badge tone={inbox.counts.jobs_failed ? "red" : "emerald"}>jobs {inbox.counts.jobs_failed}</Badge>
          <Badge tone={inbox.counts.orders_pending ? "amber" : "emerald"}>orders {inbox.counts.orders_pending}</Badge>
        </div>
      </div>

      {inbox.offline ? (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <div className="font-semibold">API offline / DB unavailable</div>
          <div className="mt-1 text-xs font-mono whitespace-pre-wrap">{inbox.error || "-"}</div>
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-200 p-4">
            <div className="text-sm font-semibold">HUMAN_REQUIRED commands</div>
            <div className="mt-1 text-xs text-slate-600">Fix blockers (balance, creds, policy, validation).</div>
          </div>
          <div className="divide-y divide-slate-100">
            {humanGroups.length ? (
              <div className="p-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Top groups (scale view)</div>
                <div className="mt-2 space-y-2">
                  {humanGroups.slice(0, 10).map((g) => (
                    <div key={`${g.type}:${g.error_code}`} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="text-sm font-medium text-slate-900">{g.type}</div>
                          <div className="mt-1 flex flex-wrap items-center gap-2">
                            <Badge tone={g.error_code === "NONE" ? "amber" : "red"}>{g.error_code}</Badge>
                            <Badge tone="blue">{g.count}</Badge>
                            <span className="text-[11px] text-slate-600">{g.latest_updated_at || "-"}</span>
                          </div>
                        </div>
                        <Link
                          className="text-xs underline text-slate-700"
                          href={`/ops/commands?status=NEEDS_ATTENTION&type=${encodeURIComponent(g.type)}`}
                        >
                          View in Commands
                        </Link>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="mt-2 text-[11px] text-slate-500">
                  These are grouped so you can clear issues class-by-class instead of scrolling endless rows.
                </div>
              </div>
            ) : null}
            {inbox.commands_human_required.length ? (
              inbox.commands_human_required.map((c) => (
                <div key={c.id} className="p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <Link className="font-mono text-xs underline" href={`/ops/commands/${c.id}`}>
                        {c.id.slice(0, 12)}
                      </Link>
                      <div className="mt-1 text-sm">{c.type}</div>
                      <div className="mt-1 text-xs text-slate-600">{c.updated_at || "-"}</div>
                    </div>
                    <div className="flex items-start gap-3">
                      {c.error_code ? <Badge tone="red">{c.error_code}</Badge> : <Badge tone="amber">{c.status}</Badge>}
                      <InboxCommandActions commandId={c.id} />
                    </div>
                  </div>
                  {c.error_message || c.last_error ? (
                    <pre className="mt-2 max-h-28 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-2 text-[11px] text-slate-900">
                      {(c.error_message || "") + (c.last_error ? `\n${c.last_error}` : "")}
                    </pre>
                  ) : null}
                </div>
              ))
            ) : (
              <div className="p-4 text-sm text-slate-600">No human-required commands.</div>
            )}
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-200 p-4">
            <div className="text-sm font-semibold">Pending orders</div>
            <div className="mt-1 text-xs text-slate-600">Fulfillment queue (spectator mode).</div>
          </div>
          <div className="divide-y divide-slate-100">
            {inbox.orders_pending.length ? (
              inbox.orders_pending.map((o) => (
                <div key={o.id} className="p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="font-mono text-xs">{o.tm_order_ref}</div>
                      <div className="mt-1 text-sm">{o.buyer_name || "-"}</div>
                      <div className="mt-1 text-xs text-slate-600">{o.created_at || "-"}</div>
                    </div>
                    <Badge tone="amber">{o.sold_price == null ? "-" : `$${o.sold_price.toFixed(2)}`}</Badge>
                  </div>
                </div>
              ))
            ) : (
              <div className="p-4 text-sm text-slate-600">No pending orders.</div>
            )}
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 p-4">
          <div className="text-sm font-semibold">Retrying / executing commands</div>
          <div className="mt-1 text-xs text-slate-600">Good for spotting platform outages or stuck workers.</div>
        </div>
        <div className="divide-y divide-slate-100">
          {retryGroups.length ? (
            <div className="p-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Top groups (scale view)</div>
              <div className="mt-2 space-y-2">
                {retryGroups.slice(0, 10).map((g) => (
                  <div key={`${g.type}:${g.status}`} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="text-sm font-medium text-slate-900">{g.type}</div>
                        <div className="mt-1 flex flex-wrap items-center gap-2">
                          <Badge tone="amber">{g.status}</Badge>
                          <Badge tone="blue">{g.count}</Badge>
                          <span className="text-[11px] text-slate-600">{g.latest_updated_at || "-"}</span>
                        </div>
                      </div>
                      <Link
                        className="text-xs underline text-slate-700"
                        href={`/ops/commands?status=ACTIVE&type=${encodeURIComponent(g.type)}`}
                      >
                        View in Commands
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
          {inbox.commands_retrying.length ? (
            inbox.commands_retrying.map((c) => (
              <div key={c.id} className="p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <Link className="font-mono text-xs underline" href={`/ops/commands/${c.id}`}>
                      {c.id.slice(0, 12)}
                    </Link>
                    <div className="mt-1 text-sm">{c.type}</div>
                    <div className="mt-1 text-xs text-slate-600">
                      {c.status} · {c.attempts}/{c.max_attempts} · {c.updated_at || "-"}
                    </div>
                  </div>
                  <Badge tone="amber">{c.status}</Badge>
                </div>
                {c.last_error ? (
                  <pre className="mt-2 max-h-28 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-2 text-[11px] text-slate-900">
                    {c.last_error}
                  </pre>
                ) : null}
              </div>
            ))
          ) : (
            <div className="p-4 text-sm text-slate-600">No retrying/executing commands.</div>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 p-4">
          <div className="text-sm font-semibold">Failed jobs</div>
          <div className="mt-1 text-xs text-slate-600">Automation runs that need investigation.</div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">ID</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Start</th>
                <th className="px-4 py-3">End</th>
                <th className="px-4 py-3">Summary</th>
              </tr>
            </thead>
            <tbody>
              {inbox.jobs_failed.map((j) => (
                <tr key={j.id} className="border-t border-slate-100">
                  <td className="px-4 py-3 font-mono text-xs">{j.id}</td>
                  <td className="px-4 py-3">{j.job_type || "-"}</td>
                  <td className="px-4 py-3">{j.start_time || "-"}</td>
                  <td className="px-4 py-3">{j.end_time || "-"}</td>
                  <td className="px-4 py-3">
                    <pre className="max-h-24 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-2 text-[11px] text-slate-900">
                      {(j.summary || "-").slice(0, 1500)}
                    </pre>
                  </td>
                </tr>
              ))}
              {!inbox.jobs_failed.length ? (
                <tr className="border-t border-slate-100">
                  <td className="px-4 py-3 text-sm text-slate-600" colSpan={5}>
                    No failed jobs.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

