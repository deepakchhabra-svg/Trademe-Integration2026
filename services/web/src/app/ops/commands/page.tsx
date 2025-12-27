type PageResponse<T> = { items: T[]; total: number };

type Cmd = {
  id: string;
  type: string;
  status: string;
  priority: number;
  attempts: number;
  max_attempts: number;
  last_error: string | null;
  created_at: string;
};

import Link from "next/link";
import { apiGet } from "../../_components/api";
import { Badge } from "../../_components/Badge";

export default async function CommandsPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; per_page?: string }>;
}) {
  const sp = await searchParams;
  const page = Math.max(1, Number(sp.page || "1"));
  const perPage = Math.min(200, Math.max(10, Number(sp.per_page || "50")));

  const data = await apiGet<PageResponse<Cmd>>(`/commands?page=${page}&per_page=${perPage}`);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Commands</h1>
          <p className="mt-1 text-sm text-slate-600">Every action is a command. Click to inspect payload + errors.</p>
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
                <th className="px-4 py-3">Attempts</th>
                <th className="px-4 py-3">Priority</th>
                <th className="px-4 py-3">Created</th>
                <th className="px-4 py-3">Error</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((c) => (
                <tr key={c.id} className="border-t border-slate-100 hover:bg-slate-50 align-top">
                  <td className="px-4 py-3 font-mono text-xs">
                    <Link className="underline" href={`/ops/commands/${c.id}`}>
                      {c.id.slice(0, 12)}
                    </Link>
                  </td>
                  <td className="px-4 py-3">{c.type}</td>
                  <td className="px-4 py-3">{c.status}</td>
                  <td className="px-4 py-3">
                    {c.attempts}/{c.max_attempts}
                  </td>
                  <td className="px-4 py-3">{c.priority}</td>
                  <td className="px-4 py-3">{c.created_at}</td>
                  <td className="px-4 py-3 text-xs text-slate-600">{c.last_error || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

