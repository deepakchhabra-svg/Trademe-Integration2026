"use client";

import { useState } from "react";
import { getCookie, setCookie } from "./cookies";

type Role = "listing" | "fulfillment" | "power" | "root";

export function RoleSwitcher() {
  const [role, setRole] = useState<Role>(() => {
    const v = getCookie("retailos_role");
    if (v === "listing" || v === "fulfillment" || v === "power" || v === "root") return v;
    return "listing";
  });

  return (
    <label className="flex items-center gap-2 text-xs text-slate-600">
      <span className="hidden sm:inline">Role</span>
      <select
        className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900 shadow-sm"
        value={role}
        onChange={(e) => {
          const next = e.target.value as Role;
          setRole(next);
          setCookie("retailos_role", next);
          window.location.reload();
        }}
      >
        <option value="listing">listing</option>
        <option value="fulfillment">fulfillment</option>
        <option value="power">power</option>
        <option value="root">root</option>
      </select>
    </label>
  );
}

