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

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${apiBaseUrl()}${path}`, { cache: "no-store", headers: await apiHeaders() });
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

