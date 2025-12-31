import clsx from "clsx";

export type ButtonVariant = "primary" | "secondary" | "danger" | "success" | "outline" | "link";
export type ButtonSize = "sm" | "md";

export function buttonClass(opts?: { variant?: ButtonVariant; size?: ButtonSize; disabled?: boolean }): string {
  const v = opts?.variant ?? "secondary";
  const s = opts?.size ?? "sm";
  const disabled = !!opts?.disabled;

  const base =
    "inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2";
  const size = s === "md" ? "px-3.5 py-2 text-sm" : "px-3 py-1.5 text-xs";

  const variant =
    v === "primary"
      ? "bg-indigo-600 text-white shadow-sm shadow-indigo-900/10 hover:bg-indigo-700 focus-visible:ring-indigo-500/30 focus-visible:ring-offset-slate-50"
      : v === "success"
        ? "bg-emerald-600 text-white shadow-sm shadow-emerald-900/10 hover:bg-emerald-700 focus-visible:ring-emerald-500/30 focus-visible:ring-offset-slate-50"
        : v === "danger"
          ? "bg-red-600 text-white shadow-sm shadow-red-900/10 hover:bg-red-700 focus-visible:ring-red-500/30 focus-visible:ring-offset-slate-50"
          : v === "outline"
            ? "border border-slate-200 bg-white/80 text-slate-900 backdrop-blur hover:bg-white focus-visible:ring-slate-400/30 focus-visible:ring-offset-slate-50"
            : v === "link"
              ? "px-0 py-0 text-indigo-700 hover:text-indigo-800 hover:underline focus-visible:ring-indigo-500/20 focus-visible:ring-offset-slate-50"
              : "border border-slate-200 bg-slate-900 text-white shadow-sm shadow-slate-900/10 hover:bg-slate-800 focus-visible:ring-slate-400/25 focus-visible:ring-offset-slate-50";

  const state = disabled ? "cursor-not-allowed opacity-60" : "";

  return clsx(base, size, variant, state);
}

export function cardClass(): string {
  return "rounded-xl border border-slate-200 bg-white/85 shadow-sm backdrop-blur";
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

