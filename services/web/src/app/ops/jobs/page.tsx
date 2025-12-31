import Link from "next/link";

import { apiGet } from "../../_components/api";
import { Badge } from "../../_components/Badge";
import { buildQueryString } from "../../_components/pagination";
import { buttonClass } from "../../_components/ui";
import { PageHeader } from "../../../components/ui/PageHeader";
import { FilterChips } from "../../../components/ui/FilterChips";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import { formatNZT } from "../../_components/time";

type PageResponse<T> = { items: T[]; total: number };

type JobRow = {
  id: number;
  job_type: string | null;
  status: string | null;
  start_time: string | null;
  end_time: string | null;
  items_processed: number | null;
  items_created: number | null;
  items_updated: number | null;
  items_deleted: number | null;
  items_failed: number | null;
  summary: string | null;
};

export default async function JobsPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; per_page?: string; status?: string; job_type?: string }>;
}) {
  const sp = await searchParams;
  const page = Math.max(1, Number(sp.page || "1"));
  const perPage = Math.min(200, Math.max(10, Number(sp.per_page || "50")));
  const status = sp.status || "";
  const jobType = sp.job_type || "";

  const baseParams = { per_page: perPage, status, job_type: jobType };
  const qs = buildQueryString({ page, per_page: perPage, status, job_type: jobType }, {});
  const data = await apiGet<PageResponse<JobRow>>(`/jobs?${qs}`);
  const prevHref = `/ops/jobs?${buildQueryString(baseParams, { page: Math.max(1, page - 1) })}`;
  const nextHref = `/ops/jobs?${buildQueryString(baseParams, { page: page + 1 })}`;

  return (
    <div className="space-y-4">
      <PageHeader
        title="Jobs"
        subtitle="Background runs with counts and summaries. Filter by type/status to troubleshoot quickly."
        actions={
          <Badge tone="indigo">
            Page {page} · {perPage}/page
          </Badge>
        }
      />

      <FilterChips
        chips={[
          { label: "Status", value: status || null, href: "/ops/jobs" },
          { label: "Job type", value: jobType || null, href: "/ops/jobs" },
        ]}
      />

      <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-col gap-3 border-b border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="text-sm text-slate-700">
            Showing {data.items.length} of {data.total}
          </div>
          <form className="flex flex-wrap items-center gap-2" method="get">
            <input type="hidden" name="page" value="1" />
            <label className="text-xs text-slate-600">
              <span className="mr-1">Status</span>
              <select
                name="status"
                defaultValue={status}
                className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
              >
                <option value="">All</option>
                <option value="RUNNING">RUNNING</option>
                <option value="COMPLETED">COMPLETED</option>
                <option value="FAILED">FAILED</option>
              </select>
            </label>
            <label className="text-xs text-slate-600">
              <span className="mr-1">Job type</span>
              <input
                name="job_type"
                defaultValue={jobType}
                className="w-48 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
                placeholder="e.g. ENRICH_SUPPLIER"
              />
            </label>
            <label className="text-xs text-slate-600">
              <span className="mr-1">Per</span>
              <select
                name="per_page"
                defaultValue={String(perPage)}
                className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
              >
                <option value="25">25</option>
                <option value="50">50</option>
                <option value="100">100</option>
                <option value="200">200</option>
              </select>
            </label>
            <button type="submit" className={buttonClass({ variant: "primary" })}>
              Apply
            </button>
            <Link className={buttonClass({ variant: "link" })} href="/ops/jobs">
              Reset
            </Link>
          </form>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">ID</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Start</th>
                <th className="px-4 py-3">End</th>
                <th className="px-4 py-3">Processed</th>
                <th className="px-4 py-3">Failed</th>
              </tr>
            </thead>
            <tbody>
              {data.items.length ? (
                data.items.map((j) => (
                  <tr key={j.id} className="border-t border-slate-100 hover:bg-slate-50">
                    <td className="px-4 py-3 font-mono text-xs">
                      <Link className="underline" href={`/ops/jobs#job-${j.id}`}>
                        {j.id}
                      </Link>
                    </td>
                    <td className="px-4 py-3">{j.job_type || "-"}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={j.status || "UNKNOWN"} />
                    </td>
                    <td className="px-4 py-3">{formatNZT(j.start_time)}</td>
                    <td className="px-4 py-3">{formatNZT(j.end_time)}</td>
                    <td className="px-4 py-3">{j.items_processed ?? 0}</td>
                    <td className="px-4 py-3">{j.items_failed ?? 0}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td className="px-4 py-6 text-sm text-slate-600" colSpan={7}>
                    No jobs match this filter. Next action: run the pipeline for your supplier, then return here to review summaries.
                    <div className="mt-2 flex gap-2">
                      <Link className={buttonClass({ variant: "primary" })} href="/pipeline">
                        Open Pipeline
                      </Link>
                      <Link className={buttonClass({ variant: "outline" })} href="/ops/jobs">
                        Reset filters
                      </Link>
                    </div>
                  </td>
                </tr>
              )}
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

