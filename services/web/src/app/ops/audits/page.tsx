import { apiGet } from "../../_components/api";
import { Badge } from "../../_components/Badge";
import Link from "next/link";
import { buildQueryString } from "../../_components/pagination";
import { buttonClass } from "../../_components/ui";

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
  searchParams: Promise<{
    page?: string;
    per_page?: string;
    entity_type?: string;
    entity_id?: string;
    action?: string;
    include_ai_cost?: string;
  }>;
}) {
  const sp = await searchParams;
  const page = Math.max(1, Number(sp.page || "1"));
  const perPage = Math.min(200, Math.max(10, Number(sp.per_page || "100")));
  const entityType = sp.entity_type || "";
  const entityId = sp.entity_id || "";
  const action = sp.action || "";
  const includeAiCost = sp.include_ai_cost === "1";

  const qs = buildQueryString(
    { page, per_page: perPage, entity_type: entityType, entity_id: entityId, action, include_ai_cost: includeAiCost ? "1" : "" },
    {},
  );
  const data = await apiGet<PageResponse<AuditRow>>(`/audits?${qs}`);

  const baseParams = { per_page: perPage, entity_type: entityType, entity_id: entityId, action, include_ai_cost: includeAiCost ? "1" : "" };
  const prevHref = `/ops/audits?${buildQueryString(baseParams, { page: Math.max(1, page - 1) })}`;
  const nextHref = `/ops/audits?${buildQueryString(baseParams, { page: page + 1 })}`;

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
        <div className="flex flex-col gap-3 border-b border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="text-sm text-slate-700">
            Showing {data.items.length} of {data.total}
          </div>
          <form className="flex flex-wrap items-center gap-2" method="get">
            <input type="hidden" name="page" value="1" />
            <label className="text-xs text-slate-600">
              <span className="mr-1">Entity</span>
              <input
                name="entity_type"
                defaultValue={entityType}
                className="w-28 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
                placeholder="Order/Listing"
              />
            </label>
            <label className="text-xs text-slate-600">
              <span className="mr-1">ID</span>
              <input
                name="entity_id"
                defaultValue={entityId}
                className="w-28 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
                placeholder="entity id"
              />
            </label>
            <label className="text-xs text-slate-600">
              <span className="mr-1">Action</span>
              <input
                name="action"
                defaultValue={action}
                className="w-44 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
                placeholder="VALIDATION_FAIL"
              />
            </label>
            <label className="flex items-center gap-2 text-xs text-slate-600">
              <input type="checkbox" name="include_ai_cost" value="1" defaultChecked={includeAiCost} />
              <span>Include AI_COST</span>
            </label>
            <label className="text-xs text-slate-600">
              <span className="mr-1">Per</span>
              <select
                name="per_page"
                defaultValue={String(perPage)}
                className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
              >
                <option value="50">50</option>
                <option value="100">100</option>
                <option value="200">200</option>
              </select>
            </label>
            <button type="submit" className={buttonClass({ variant: "primary" })}>
              Apply
            </button>
            <Link className={buttonClass({ variant: "link" })} href="/ops/audits">
              Reset
            </Link>
          </form>
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
        <div className="flex items-center justify-between border-t border-slate-200 p-4 text-sm">
          <Link className={`text-slate-700 underline ${page <= 1 ? "pointer-events-none opacity-40" : ""}`} href={prevHref}>
            Prev
          </Link>
          <div className="text-xs text-slate-600">Page {page}</div>
          <Link className="text-slate-700 underline" href={nextHref}>
            Next
          </Link>
        </div>
      </div>
    </div>
  );
}

