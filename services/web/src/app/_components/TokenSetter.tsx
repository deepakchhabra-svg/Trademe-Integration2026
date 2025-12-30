"use client";

import { useState } from "react";
import { setCookie, getCookie } from "./cookies";
import { buttonClass } from "./ui";

export function TokenSetter() {
  const [token, setToken] = useState<string>(() => getCookie("retailos_token") || "");
  const [saved, setSaved] = useState(false);

  return (
    <div className="space-y-2">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Root token</div>
      <div className="flex items-center gap-2">
        <input
          className="w-full rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900 shadow-sm"
          type="password"
          placeholder="X-RetailOS-Token"
          value={token}
          onChange={(e) => {
            setToken(e.target.value);
            setSaved(false);
          }}
        />
        <button
          className={buttonClass({ variant: "primary" })}
          onClick={() => {
            setCookie("retailos_token", token);
            setSaved(true);
          }}
          type="button"
        >
          Save
        </button>
      </div>
      {saved ? <div className="text-[11px] text-emerald-700">Saved to cookie.</div> : null}
      <div className="text-[11px] text-slate-500">Used for root-only settings if `RETAIL_OS_ROOT_TOKEN` is set.</div>
    </div>
  );
}

