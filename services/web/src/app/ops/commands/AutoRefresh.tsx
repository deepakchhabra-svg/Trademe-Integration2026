"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export function AutoRefresh({ enabledByDefault, intervalMs = 1500 }: { enabledByDefault: boolean; intervalMs?: number }) {
  const router = useRouter();
  const [enabled, setEnabled] = useState(enabledByDefault);

  useEffect(() => {
    if (!enabled) return;
    const t = setInterval(() => router.refresh(), intervalMs);
    return () => clearInterval(t);
  }, [enabled, intervalMs, router]);

  return (
    <label className="inline-flex items-center gap-2 text-xs text-slate-600">
      <input
        type="checkbox"
        checked={enabled}
        onChange={(e) => setEnabled(e.target.checked)}
        className="h-3.5 w-3.5"
        data-testid="chk-auto-refresh"
      />
      Auto-refresh
    </label>
  );
}

