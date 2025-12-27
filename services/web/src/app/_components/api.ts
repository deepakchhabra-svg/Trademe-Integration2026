import { cookies } from "next/headers";

export function apiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
}

export function apiHeaders(): Record<string, string> {
  const store = cookies();
  const role = store.get("retailos_role")?.value || "root";
  const token = store.get("retailos_token")?.value;
  const headers: Record<string, string> = {
    "X-RetailOS-Role": role,
  };
  if (token) headers["X-RetailOS-Token"] = token;
  return headers;
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${apiBaseUrl()}${path}`, { cache: "no-store", headers: apiHeaders() });
  if (!res.ok) throw new Error(`API ${path} failed: ${res.status}`);
  return (await res.json()) as T;
}

