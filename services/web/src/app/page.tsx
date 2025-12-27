type Health = { status: string; utc: string };

async function fetchHealth(): Promise<Health> {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  const res = await fetch(`${base}/health`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API health failed: ${res.status}`);
  return (await res.json()) as Health;
}

export default async function Home() {
  let health: Health | null = null;
  let error: string | null = null;

  try {
    health = await fetchHealth();
  } catch (e) {
    error = e instanceof Error ? e.message : "Unknown error";
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h1 className="text-xl font-semibold">RetailOS Admin</h1>
              <p className="mt-1 text-sm text-slate-600">
                Next.js UI talking to FastAPI. This will replace Streamlit.
              </p>
            </div>
            <div className="text-right">
              <div className="text-xs uppercase tracking-wide text-slate-500">API</div>
              {health ? (
                <div className="mt-1 inline-flex items-center rounded-full bg-emerald-50 px-3 py-1 text-sm font-medium text-emerald-700">
                  {health.status}
                </div>
              ) : (
                <div className="mt-1 inline-flex items-center rounded-full bg-red-50 px-3 py-1 text-sm font-medium text-red-700">
                  down
                </div>
              )}
            </div>
          </div>

          {error ? (
            <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
              {error}
            </div>
          ) : (
            <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
              <a className="rounded-lg border border-slate-200 bg-slate-50 p-4 hover:bg-slate-100" href="/vaults/raw">
                <div className="text-sm font-semibold">Vault 1 (Raw)</div>
                <div className="mt-1 text-xs text-slate-600">Supplier products + reconciliation</div>
              </a>
              <a
                className="rounded-lg border border-slate-200 bg-slate-50 p-4 hover:bg-slate-100"
                href="/vaults/enriched"
              >
                <div className="text-sm font-semibold">Vault 2 (Enriched)</div>
                <div className="mt-1 text-xs text-slate-600">Internal products + publish gate</div>
              </a>
              <a className="rounded-lg border border-slate-200 bg-slate-50 p-4 hover:bg-slate-100" href="/ops/commands">
                <div className="text-sm font-semibold">Command Center</div>
                <div className="mt-1 text-xs text-slate-600">Queue, retries, failures</div>
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
