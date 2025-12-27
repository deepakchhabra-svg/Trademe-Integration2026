import { apiGet } from "../../_components/api";
import { Badge } from "../../_components/Badge";

type PageResponse<T> = { items: T[]; total: number };

type AuditRow = {
  id: number;
  timestamp: string | null;
  user: string | null;
  action: string | null;
  entity_type: string | null;
  entity_id: string | null;
  old_value: string | null;
  new_value: string | null;
};

export default async function AuditsPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; per_page?: string; entity_type?: string; entity_id?: string; action?: string }>;
}) {
  const sp = await searchParams;
  const page = Math.max(1, Number(sp.page || "1"));
  const perPage = Math.min(200, Math.max(10, Number(sp.per_page || "100")));

  const qp = new URLSearchParams();
  qp.set("page", String(page));
  qp.set("per_page", String(perPage));
  if (sp.entity_type) qp.set("entity_type", sp.entity_type);
  if (sp.entity_id) qp.set("entity_id", sp.entity_id);
  if (sp.action) qp.set("action", sp.action);

  const data = await apiGet<PageResponse<AuditRow>>(`/audits?${qp.toString()}`);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Audits</h1>
          <p className="mt-1 text-sm text-slate-600">Immutable trail of why the system did what it did.</p>
        </div>
        <Badge tone="blue">
          Page {page} · {perPage}/page
        </Badge>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-200 p-4">
          <div className="text-sm text-slate-700">
            Showing {data.items.length} of {data.total}
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Time</th>
                <th className="px-4 py-3">Action</th>
                <th className="px-4 py-3">Entity</th>
                <th className="px-4 py-3">User</th>
                <th className="px-4 py-3">New Value</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((a) => (
                <tr key={a.id} className="border-t border-slate-100 hover:bg-slate-50 align-top">
                  <td className="px-4 py-3 font-mono text-xs">{a.timestamp || "-"}</td>
                  <td className="px-4 py-3">{a.action || "-"}</td>
                  <td className="px-4 py-3">
                    <div className="text-xs text-slate-600">{a.entity_type || "-"}</div>
                    <div className="font-mono text-xs">{a.entity_id || "-"}</div>
                  </td>
                  <td className="px-4 py-3">{a.user || "-"}</td>
                  <td className="px-4 py-3">
                    <pre className="max-h-32 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-2 text-[11px] text-slate-900">
                      {(a.new_value || "-").slice(0, 2000)}
                    </pre>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

