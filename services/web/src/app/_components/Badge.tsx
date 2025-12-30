import clsx from "clsx";

export function Badge({
  children,
  tone = "slate",
}: {
  children: React.ReactNode;
  tone?: "slate" | "emerald" | "red" | "amber" | "blue" | "indigo";
}) {
  const toneClasses: Record<string, string> = {
    slate: "bg-slate-100 text-slate-800 border-slate-200",
    emerald: "bg-emerald-50 text-emerald-800 border-emerald-200",
    red: "bg-red-50 text-red-800 border-red-200",
    amber: "bg-amber-50 text-amber-900 border-amber-200",
    blue: "bg-blue-50 text-blue-900 border-blue-200",
    indigo: "bg-indigo-50 text-indigo-900 border-indigo-200",
  };

  return (
    <span
      data-testid={`badge-${tone}`}
      className={clsx(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium",
        toneClasses[tone] ?? toneClasses.slate,
      )}
    >
      {children}
    </span>
  );
}

