import Link from "next/link";
import { apiGet } from "../../_components/api";
import { Badge } from "../../_components/Badge";
import { buildQueryString } from "../../_components/pagination";
import { PageHeader } from "../../../components/ui/PageHeader";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import { buttonClass } from "../../_components/ui";
import { FilterChips } from "../../../components/ui/FilterChips";
import { formatNZT } from "../../_components/time";

type PageResponse<T> = { items: T[]; total: number };

type Cmd = {
  id: string;
  type: string;
  status: string;
  priority: number;
  attempts: number;
  max_attempts: number;
  last_error: string | null;
  created_at: string;
  updated_at?: string | null;
};

function typeLabel(t: string): string {
  const key = (t || "").toUpperCase();
  const map: Record<string, string> = {
    SCRAPE_SUPPLIER: "Scrape",
    ENRICH_SUPPLIER: "Enrich & standardise",
    PUBLISH_LISTING: "Publish listing",
    UPDATE_PRICE: "Update price",
    WITHDRAW_LISTING: "Withdraw listing",
    SYNC_SOLD_ITEMS: "Sync sold items",
    SYNC_SELLING_ITEMS: "Sync selling items",
    RESET_ENRICHMENT: "Reset enrichment",
    TEST_COMMAND: "Test command",
  };
  return map[key] || t;
}

function viewToStatus(view: string): string {
  // The API supports special status views.
  if (view === "active") return "ACTIVE";
  if (view === "attention") return "NEEDS_ATTENTION";
  if (view === "succeeded") return "SUCCEEDED";
  if (view === "all") return "";
  return "NEEDS_ATTENTION";
}

export default async function QueuePage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; per_page?: string; view?: string; type?: string }>;
}) {
  const sp = await searchParams;
  const page = Math.max(1, Number(sp.page || "1"));
  const perPage = Math.min(200, Math.max(10, Number(sp.per_page || "50")));
  const view = (sp.view || "attention").toLowerCase();
  const type = sp.type || "";
  const status = viewToStatus(view);

  const qp = new URLSearchParams();
  qp.set("page", String(page));
  qp.set("per_page", String(perPage));
  if (type) qp.set("type", type);
  if (status) qp.set("status", status);

  const data = await apiGet<PageResponse<Cmd>>(`/commands?${qp.toString()}`);

  const baseParams = { per_page: perPage, type };
  const tab = (v: string) => `/ops/queue?${buildQueryString(baseParams, { page: 1, view: v })}`;
  const prevHref = `/ops/queue?${buildQueryString({ ...baseParams, view }, { page: Math.max(1, page - 1) })}`;
  const nextHref = `/ops/queue?${buildQueryString({ ...baseParams, view }, { page: page + 1 })}`;

  return (
    <div className="space-y-4">
      <PageHeader
        title="Queue"
        subtitle="System work in progress. Use this to see what’s running, what’s queued, and what needs attention."
        actions={
          <div className="flex items-center gap-2">
            <Badge tone="indigo">
              Page {page} · {perPage}/page
            </Badge>
            <Link className={buttonClass({ variant: "outline" })} href="/ops/inbox">
              Inbox
            </Link>
          </div>
        }
      />

      <FilterChips
        chips={[
          { label: "View", value: view, href: "/ops/queue" },
          { label: "Type", value: type || null, href: `/ops/queue?${buildQueryString({ per_page: perPage, view }, { page: 1 })}` },
        ]}
      />

      <div className="flex flex-wrap items-center gap-2">
        <Link className={buttonClass({ variant: view === "attention" ? "primary" : "outline" })} href={tab("attention")}>
          Needs attention
        </Link>
        <Link className={buttonClass({ variant: view === "active" ? "primary" : "outline" })} href={tab("active")}>
          Running / queued
        </Link>
        <Link className={buttonClass({ variant: view === "succeeded" ? "primary" : "outline" })} href={tab("succeeded")}>
          Completed
        </Link>
        <Link className={buttonClass({ variant: view === "all" ? "primary" : "outline" })} href={tab("all")}>
          All
        </Link>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-col gap-3 border-b border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="text-sm text-slate-700">
            Showing {data.items.length} of {data.total}
          </div>
          <form className="flex flex-wrap items-center gap-2" method="get">
            <input type="hidden" name="page" value="1" />
            <input type="hidden" name="view" value={view} />
            <label className="text-xs text-slate-600">
              <span className="mr-1">Type</span>
              <input
                name="type"
                defaultValue={type}
                className="w-48 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
                placeholder="Optional filter"
              />
            </label>
            <label className="text-xs text-slate-600">
              <span className="mr-1">Per</span>
              <select
                name="per_page"
                defaultValue={String(perPage)}
                className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
              >
                <option value="25">25</option>
                <option value="50">50</option>
                <option value="100">100</option>
                <option value="200">200</option>
              </select>
            </label>
            <button type="submit" className={buttonClass({ variant: "primary" })}>
              Apply
            </button>
            <Link className={buttonClass({ variant: "link" })} href={`/ops/queue?${buildQueryString({ per_page: perPage, view }, { page: 1 })}`}>
              Reset
            </Link>
          </form>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">ID</th>
                <th className="px-4 py-3">Action</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Attempts</th>
                <th className="px-4 py-3">Created</th>
                <th className="px-4 py-3">Notes</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((c) => (
                <tr key={c.id} className="border-t border-slate-100 hover:bg-slate-50 align-top">
                  <td className="px-4 py-3 font-mono text-xs">
                    <Link className="underline" href={`/ops/commands/${c.id}`}>
                      {c.id.slice(0, 12)}
                    </Link>
                  </td>
                  <td className="px-4 py-3">{typeLabel(c.type)}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={c.status} />
                  </td>
                  <td className="px-4 py-3">
                    {c.attempts}/{c.max_attempts}
                  </td>
                  <td className="px-4 py-3">{formatNZT(c.created_at)}</td>
                  <td className="px-4 py-3 text-xs text-slate-600">{c.last_error || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between border-t border-slate-200 p-4 text-sm">
          <Link className={`text-slate-700 underline ${page <= 1 ? "pointer-events-none opacity-40" : ""}`} href={prevHref}>
            Prev
          </Link>
          <div className="text-xs text-slate-600">Page {page}</div>
          <Link className="text-slate-700 underline" href={nextHref}>
            Next
          </Link>
        </div>
      </div>
    </div>
  );
}

