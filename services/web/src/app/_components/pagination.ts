export function buildQueryString(
  base: Record<string, string | number | null | undefined>,
  overrides: Record<string, string | number | null | undefined>,
): string {
  const qp = new URLSearchParams();
  const merged = { ...base, ...overrides };
  for (const [k, v] of Object.entries(merged)) {
    if (v === undefined || v === null) continue;
    const s = String(v);
    if (!s) continue;
    qp.set(k, s);
  }
  return qp.toString();
}

