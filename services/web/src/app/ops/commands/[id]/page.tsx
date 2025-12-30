import Link from "next/link";

import { apiGet } from "../../../_components/api";
import { Badge } from "../../../_components/Badge";
import { ErrorState } from "../../../../components/ui/ErrorState";
import { CommandActions } from "./Actions";
import { LiveCommandPanel } from "./LivePanel";
import { CommandLogsPanel } from "./LogsPanel";
import { formatNZT } from "../../../_components/time";

type CommandDetail = {
  id: string;
  type: string;
  status: string;
  priority: number;
  attempts: number;
  max_attempts: number;
  last_error: string | null;
  error_code?: string | null;
  error_message?: string | null;
  payload: Record<string, unknown>;
  created_at: string | null;
  updated_at: string | null;
};

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-sm text-slate-900">{value}</div>
    </div>
  );
}

export default async function CommandDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let cmd: CommandDetail | null = null;
  try {
    cmd = await apiGet<CommandDetail>(`/commands/${encodeURIComponent(id)}`);
  } catch (e) {
    const err = e instanceof Error ? e : new Error("Command not found");
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Link className="text-sm text-slate-600 underline" href="/ops/commands">
            Commands
          </Link>
          <span className="text-sm text-slate-400">/</span>
          <span className="text-sm font-medium text-slate-900">{id}</span>
        </div>
        <ErrorState error={err} />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Link className="text-sm text-slate-600 underline" href="/ops/commands">
              Commands
            </Link>
            <span className="text-sm text-slate-400">/</span>
            <span className="text-sm font-medium text-slate-900">{cmd.id.slice(0, 12)}</span>
          </div>
          <h1 className="mt-2 text-lg font-semibold tracking-tight">{cmd.type}</h1>
          <p className="mt-1 text-sm text-slate-600">Inspect payload + error context for this command.</p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <Badge tone={cmd.status === "SUCCEEDED" ? "emerald" : cmd.status.includes("FAILED") ? "red" : "amber"}>
            {cmd.status}
          </Badge>
          {cmd.error_code ? <Badge tone="red">{cmd.error_code}</Badge> : null}
        </div>
      </div>

      <LiveCommandPanel commandId={cmd.id} initial={cmd} />
      <CommandLogsPanel commandId={cmd.id} initialStatus={cmd.status} />

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        <Field label="Priority" value={cmd.priority} />
        <Field label="Attempts" value={`${cmd.attempts}/${cmd.max_attempts}`} />
        <Field label="Created" value={formatNZT(cmd.created_at)} />
        <Field label="Updated" value={formatNZT(cmd.updated_at)} />
      </div>

      {cmd.error_message || cmd.last_error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-900">
          <div className="font-semibold">Error</div>
          <div className="mt-2 font-mono text-xs whitespace-pre-wrap">
            {(cmd.error_message || "") + (cmd.last_error ? `\n\n${cmd.last_error}` : "")}
          </div>
        </div>
      ) : null}

      <CommandActions commandId={cmd.id} status={cmd.status} />

      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="text-sm font-semibold">Payload (JSON)</div>
        <pre className="mt-3 max-h-[520px] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-900">
          {JSON.stringify(cmd.payload || {}, null, 2)}
        </pre>
      </div>
    </div>
  );
}

