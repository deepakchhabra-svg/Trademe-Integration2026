import Link from "next/link";

export type FilterChip = {
  label: string;
  value?: string | number | null;
  href?: string; // link to clear or change filter
  title?: string;
};

export function FilterChips({ chips }: { chips: FilterChip[] }) {
  const visible = chips.filter((c) => c.value !== undefined && c.value !== null && String(c.value).trim() !== "");
  if (!visible.length) return null;

  return (
    <div className="flex flex-wrap items-center gap-2" data-testid="filter-chips">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Filters</div>
      {visible.map((c) => {
        const text = `${c.label}: ${String(c.value)}`;
        return c.href ? (
          <Link
            key={text}
            href={c.href}
            title={c.title || "Clear filter"}
            className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-2 py-0.5 text-xs font-medium text-slate-800 hover:bg-slate-50"
          >
            {text} <span aria-hidden="true" className="text-slate-400">×</span>
          </Link>
        ) : (
          <span
            key={text}
            title={c.title}
            className="inline-flex items-center rounded-full border border-slate-200 bg-white px-2 py-0.5 text-xs font-medium text-slate-800"
          >
            {text}
          </span>
        );
      })}
    </div>
  );
}

