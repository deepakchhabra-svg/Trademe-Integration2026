"use client";

import { getCookie } from "./cookies";

export function apiBaseUrlClient(): string {
  // In production (same-origin via nginx), use empty string.
  // In development, use the API URL or default to localhost.
  if (typeof window !== "undefined" && process.env.NODE_ENV === "production") {
    return process.env.NEXT_PUBLIC_API_BASE_URL || "";
  }
  return process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
}

function authHeaders(): Record<string, string> {
  const role = getCookie("retailos_role") || "listing";
  const token = getCookie("retailos_token") || undefined;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-RetailOS-Role": role,
  };
  if (token) headers["X-RetailOS-Token"] = token;
  return headers;
}

async function extractDetail(res: Response): Promise<string | undefined> {
  try {
    const data = (await res.json()) as unknown;
    if (data && typeof data === "object" && "detail" in data) {
      const d = (data as { detail?: unknown }).detail;
      if (typeof d === "string") return d;
    }
  } catch {
    // ignore json parse errors
  }
  return undefined;
}

export async function apiGetClient<T>(path: string): Promise<T> {
  if (process.env.NODE_ENV === "development") {
    console.log(`[API Client] GET ${path}`);
  }
  const res = await fetch(`${apiBaseUrlClient()}${path}`, { method: "GET", headers: authHeaders() });
  if (!res.ok) {
    const detail = await extractDetail(res);
    throw new Error(`API GET ${path} failed: ${res.status}${detail ? ` (${detail})` : ""}`);
  }
  return (await res.json()) as T;
}

export async function apiPostClient<T>(path: string, body: unknown): Promise<T> {
  if (process.env.NODE_ENV === "development") {
    console.log(`[API Client] POST ${path}`, body);
  }
  const res = await fetch(`${apiBaseUrlClient()}${path}`, { method: "POST", headers: authHeaders(), body: JSON.stringify(body) });
  if (!res.ok) {
    const detail = await extractDetail(res);
    throw new Error(`API POST ${path} failed: ${res.status}${detail ? ` (${detail})` : ""}`);
  }
  return (await res.json()) as T;
}

export async function apiPutClient<T>(path: string, body: unknown): Promise<T> {
  if (process.env.NODE_ENV === "development") {
    console.log(`[API Client] PUT ${path}`, body);
  }
  const res = await fetch(`${apiBaseUrlClient()}${path}`, { method: "PUT", headers: authHeaders(), body: JSON.stringify(body) });
  if (!res.ok) {
    const detail = await extractDetail(res);
    throw new Error(`API PUT ${path} failed: ${res.status}${detail ? ` (${detail})` : ""}`);
  }
  return (await res.json()) as T;
}

