import clsx from "clsx";

export type ButtonVariant = "primary" | "secondary" | "danger" | "success";
export type ButtonSize = "sm" | "md";

export function buttonClass(opts?: { variant?: ButtonVariant; size?: ButtonSize; disabled?: boolean }): string {
  const v = opts?.variant ?? "secondary";
  const s = opts?.size ?? "sm";
  const disabled = !!opts?.disabled;

  const base =
    "inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400/40";
  const size = s === "md" ? "px-3 py-2 text-sm" : "px-3 py-1.5 text-xs";

  const variant =
    v === "primary"
      ? "bg-slate-900 text-white hover:bg-slate-800"
      : v === "success"
        ? "bg-emerald-600 text-white hover:bg-emerald-700"
        : v === "danger"
          ? "border border-red-200 bg-red-50 text-red-900 hover:bg-red-100"
          : "border border-slate-200 bg-white text-slate-900 hover:bg-slate-50";

  const state = disabled ? "cursor-not-allowed opacity-60" : "";

  return clsx(base, size, variant, state);
}

export function cardClass(): string {
  return "rounded-xl border border-slate-200 bg-white shadow-sm";
}

export function cardHeaderClass(): string {
  return "border-b border-slate-200 p-4";
}

export function cardBodyClass(): string {
  return "p-4";
}

export function tableClass(): string {
  return "w-full text-left text-sm";
}

export function tableHeadClass(): string {
  return "bg-slate-50 text-xs uppercase tracking-wide text-slate-500";
}

export function tableRowClass(): string {
  return "border-t border-slate-100 hover:bg-slate-50";
}

