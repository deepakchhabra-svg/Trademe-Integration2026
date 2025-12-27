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

async function getCommands(): Promise<PageResponse<Cmd>> {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  const res = await fetch(`${base}/commands?page=1&per_page=50`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed: ${res.status}`);
  return (await res.json()) as PageResponse<Cmd>;
}

export default async function CommandsPage() {
  const data = await getCommands();

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">Command Center</h1>
            <p className="mt-1 text-sm text-slate-600">DB-backed command queue</p>
          </div>
          <a className="text-sm text-slate-700 underline" href="/">
            Home
          </a>
        </div>

        <div className="mt-6 rounded-xl border border-slate-200 bg-white shadow-sm">
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
                  <tr key={c.id} className="border-t border-slate-100 align-top">
                    <td className="px-4 py-3 font-mono text-xs">{c.id.slice(0, 12)}</td>
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
    </div>
  );
}

