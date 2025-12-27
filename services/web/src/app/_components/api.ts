import { cookies } from "next/headers";

export function apiBaseUrl(): string {
  // On Windows, `localhost` can resolve to IPv6 ::1 while the API binds to 127.0.0.1,
  // which causes `fetch failed` in server components. Prefer 127.0.0.1 by default.
  return process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
}

export async function apiHeaders(): Promise<Record<string, string>> {
  const store = await cookies();
  const role = store.get("retailos_role")?.value || "root";
  const token = store.get("retailos_token")?.value;
  const headers: Record<string, string> = {
    "X-RetailOS-Role": role,
  };
  if (token) headers["X-RetailOS-Token"] = token;
  return headers;
}

async function fetchWithRetry(url: string, init: RequestInit, attempts = 3): Promise<Response> {
  // Server components can hit ECONNRESET when the API reloads (uvicorn --reload),
  // especially on Windows. Retry a few times with small backoff.
  let lastErr: unknown = null;
  for (let i = 1; i <= attempts; i++) {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 15_000);
    try {
      const res = await fetch(url, { ...init, signal: ctrl.signal });
      clearTimeout(t);
      return res;
    } catch (e) {
      clearTimeout(t);
      lastErr = e;
      // small backoff: 250ms, 500ms, 1000ms
      const wait = Math.min(1000, 250 * 2 ** (i - 1));
      await new Promise((r) => setTimeout(r, wait));
    }
  }
  throw lastErr instanceof Error ? lastErr : new Error("fetch failed");
}

export async function apiGet<T>(path: string): Promise<T> {
  const url = `${apiBaseUrl()}${path}`;
  const res = await fetchWithRetry(url, { cache: "no-store", headers: await apiHeaders() }, 3);
  if (!res.ok) {
    let detail = "";
    try {
      detail = (await res.text()).slice(0, 500);
    } catch {
      detail = "";
    }
    throw new Error(`API ${path} failed: ${res.status}${detail ? ` — ${detail}` : ""}`);
  }
  return (await res.json()) as T;
}

