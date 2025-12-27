import Link from "next/link";

import { apiGet } from "../../_components/api";
import { Badge } from "../../_components/Badge";

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

export default async function JobsPage({ searchParams }: { searchParams: Promise<{ page?: string; per_page?: string }> }) {
  const sp = await searchParams;
  const page = Math.max(1, Number(sp.page || "1"));
  const perPage = Math.min(200, Math.max(10, Number(sp.per_page || "50")));

  const data = await apiGet<PageResponse<JobRow>>(`/jobs?page=${page}&per_page=${perPage}`);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Jobs</h1>
          <p className="mt-1 text-sm text-slate-600">Scheduler/worker runs with counts and summaries.</p>
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
              {data.items.map((j) => (
                <tr key={j.id} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-4 py-3 font-mono text-xs">
                    <Link className="underline" href={`/ops/jobs#job-${j.id}`}>
                      {j.id}
                    </Link>
                  </td>
                  <td className="px-4 py-3">{j.job_type || "-"}</td>
                  <td className="px-4 py-3">{j.status || "-"}</td>
                  <td className="px-4 py-3">{j.start_time || "-"}</td>
                  <td className="px-4 py-3">{j.end_time || "-"}</td>
                  <td className="px-4 py-3">{j.items_processed ?? 0}</td>
                  <td className="px-4 py-3">{j.items_failed ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

