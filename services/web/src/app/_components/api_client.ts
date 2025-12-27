"use client";

import { getCookie } from "./cookies";

export function apiBaseUrlClient(): string {
  // On Windows, `localhost` can resolve to IPv6 ::1 while the API binds to 127.0.0.1.
  return process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
}

export async function apiPostClient<T>(path: string, body: unknown): Promise<T> {
  const role = getCookie("retailos_role") || "root";
  const token = getCookie("retailos_token") || undefined;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-RetailOS-Role": role,
  };
  if (token) headers["X-RetailOS-Token"] = token;

  const res = await fetch(`${apiBaseUrlClient()}${path}`, { method: "POST", headers, body: JSON.stringify(body) });
  if (!res.ok) {
    let detail: string | undefined;
    try {
      const data = (await res.json()) as unknown;
      if (data && typeof data === "object" && "detail" in data && typeof (data as any).detail === "string") {
        detail = (data as any).detail;
      }
    } catch {
      // ignore json parse errors
    }
    throw new Error(`API POST ${path} failed: ${res.status}${detail ? ` (${detail})` : ""}`);
  }
  return (await res.json()) as T;
}

export async function apiPutClient<T>(path: string, body: unknown): Promise<T> {
  const role = getCookie("retailos_role") || "root";
  const token = getCookie("retailos_token") || undefined;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-RetailOS-Role": role,
  };
  if (token) headers["X-RetailOS-Token"] = token;

  const res = await fetch(`${apiBaseUrlClient()}${path}`, { method: "PUT", headers, body: JSON.stringify(body) });
  if (!res.ok) throw new Error(`API PUT ${path} failed: ${res.status}`);
  return (await res.json()) as T;
}

