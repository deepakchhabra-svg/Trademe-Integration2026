"use client";

import { getCookie } from "./cookies";

export function apiBaseUrlClient(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
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
  if (!res.ok) throw new Error(`API POST ${path} failed: ${res.status}`);
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

