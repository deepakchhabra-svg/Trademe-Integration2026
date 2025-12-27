"use client";

export function setCookie(name: string, value: string, days = 365) {
  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = `${encodeURIComponent(name)}=${encodeURIComponent(
    value,
  )}; expires=${expires}; path=/; samesite=lax`;
}

export function getCookie(name: string): string | null {
  const cookies = document.cookie.split(";").map((c) => c.trim());
  for (const c of cookies) {
    const idx = c.indexOf("=");
    if (idx < 0) continue;
    const k = decodeURIComponent(c.slice(0, idx));
    if (k !== name) continue;
    return decodeURIComponent(c.slice(idx + 1));
  }
  return null;
}

