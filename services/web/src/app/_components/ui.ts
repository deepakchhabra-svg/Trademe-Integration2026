import clsx from "clsx";

export type ButtonVariant = "primary" | "secondary" | "danger" | "success" | "outline" | "link";
export type ButtonSize = "sm" | "md";

export function buttonClass(opts?: { variant?: ButtonVariant; size?: ButtonSize; disabled?: boolean }): string {
  const v = opts?.variant ?? "secondary";
  const s = opts?.size ?? "sm";
  const disabled = !!opts?.disabled;

  const base =
    "inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors focus:outline-none focus:ring-2";
  const size = s === "md" ? "px-3.5 py-2 text-sm" : "px-3 py-1.5 text-xs";

  const variant =
    v === "primary"
      ? "bg-indigo-600 text-white hover:bg-indigo-700 focus:ring-indigo-500/30"
      : v === "success"
        ? "bg-emerald-600 text-white hover:bg-emerald-700 focus:ring-emerald-500/30"
        : v === "danger"
          ? "bg-red-600 text-white hover:bg-red-700 focus:ring-red-500/30"
          : v === "outline"
            ? "border border-slate-300 bg-white text-slate-900 hover:bg-slate-50 focus:ring-slate-400/30"
            : v === "link"
              ? "px-0 py-0 text-indigo-700 hover:text-indigo-800 hover:underline focus:ring-indigo-500/20"
              : "border border-slate-200 bg-slate-50 text-slate-900 hover:bg-slate-100 focus:ring-slate-400/25";

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

