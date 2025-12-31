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
};

import Link from "next/link";
import { apiGet } from "../../_components/api";
import { Badge } from "../../_components/Badge";
import { buildQueryString } from "../../_components/pagination";
import { AutoRefresh } from "./AutoRefresh";
import { PageHeader } from "../../../components/ui/PageHeader";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import { buttonClass } from "../../_components/ui";
import { formatNZT } from "../../_components/time";

function typeLabel(t: string): string {
  const key = (t || "").toUpperCase();
  const map: Record<string, string> = {
    SCRAPE_SUPPLIER: "Scrape supplier",
    ENRICH_SUPPLIER: "Enrich & standardise",
    PUBLISH_LISTING: "Create/publish listing",
    WITHDRAW_LISTING: "Withdraw listing",
    UPDATE_PRICE: "Update price",
    SYNC_SOLD_ITEMS: "Sync sold items",
    SYNC_SELLING_ITEMS: "Sync selling items",
    RESET_ENRICHMENT: "Reset enrichment",
    ONECHEQ_FULL_BACKFILL: "OneCheq full backfill",
    BACKFILL_IMAGES_ONECHEQ: "Backfill images (OneCheq)",
    VALIDATE_LAUNCHLOCK: "Validate LaunchLock",
  };
  return map[key] || t;
}

export default async function CommandsPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; per_page?: string; type?: string; status?: string }>;
}) {
  const sp = await searchParams;
  const page = Math.max(1, Number(sp.page || "1"));
  const perPage = Math.min(200, Math.max(10, Number(sp.per_page || "50")));
  const type = sp.type || "";
  const status = sp.status ?? "NOT_SUCCEEDED";

  const qp = new URLSearchParams();
  qp.set("page", String(page));
  qp.set("per_page", String(perPage));
  if (type) qp.set("type", type);
  if (status) qp.set("status", status);
  const data = await apiGet<PageResponse<Cmd>>(`/commands?${qp.toString()}`);

  const baseParams = { per_page: perPage, type, status };
  const prevHref = `/ops/commands?${buildQueryString(baseParams, { page: Math.max(1, page - 1) })}`;
  const nextHref = `/ops/commands?${buildQueryString(baseParams, { page: page + 1 })}`;

  return (
    <div className="space-y-4">
      <PageHeader
        title="Command log"
        subtitle="Queued work ledger. Use this to diagnose failures and see what is running/blocked."
        actions={
          <Badge tone="indigo">
            Page {page} · {perPage}/page
          </Badge>
        }
      />

      <div className="flex flex-wrap items-center gap-2">
        <AutoRefresh enabledByDefault={false} />
        <Link className={buttonClass({ variant: "outline" })} href="/ops/inbox">
          Go to Inbox (recommended)
        </Link>
        <Link
          className={buttonClass({ variant: status === "NEEDS_ATTENTION" ? "primary" : "outline" })}
          href={`/ops/commands?${buildQueryString({ per_page: perPage, type, status: "NEEDS_ATTENTION" }, { page: 1 })}`}
        >
          Needs attention
        </Link>
        <Link
          className={buttonClass({ variant: status === "ACTIVE" ? "primary" : "outline" })}
          href={`/ops/commands?${buildQueryString({ per_page: perPage, type, status: "ACTIVE" }, { page: 1 })}`}
        >
          Active (queued/running)
        </Link>
        <Link
          className={buttonClass({ variant: status === "NOT_SUCCEEDED" ? "primary" : "outline" })}
          href={`/ops/commands?${buildQueryString({ per_page: perPage, type, status: "NOT_SUCCEEDED" }, { page: 1 })}`}
        >
          Not succeeded
        </Link>
        <Link
          className={buttonClass({ variant: status === "SUCCEEDED" ? "primary" : "outline" })}
          href={`/ops/commands?${buildQueryString({ per_page: perPage, type, status: "SUCCEEDED" }, { page: 1 })}`}
        >
          Succeeded
        </Link>
        <Link
          className={buttonClass({ variant: status === "" ? "primary" : "outline" })}
          href={`/ops/commands?${buildQueryString({ per_page: perPage, type, status: "" }, { page: 1 })}`}
        >
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
            <label className="text-xs text-slate-600">
              <span className="mr-1">Type</span>
              <input
                name="type"
                defaultValue={type}
                className="w-44 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
                placeholder="e.g. PUBLISH_LISTING"
              />
            </label>
            <label className="text-xs text-slate-600">
              <span className="mr-1">Status</span>
              <input
                name="status"
                defaultValue={status}
                className="w-40 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-900"
                placeholder="Queued / Running / Needs attention"
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
            <button
              type="submit"
              className={buttonClass({ variant: "primary" })}
            >
              Apply
            </button>
            <Link className={buttonClass({ variant: "link" })} href="/ops/commands">
              Reset
            </Link>
          </form>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">ID</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Attempts</th>
                <th className="px-4 py-3">Priority</th>
                <th className="px-4 py-3">Created</th>
                <th className="px-4 py-3">Error</th>
              </tr>
            </thead>
            <tbody>
              {data.items.length ? (
                data.items.map((c) => (
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
                    <td className="px-4 py-3">{c.priority}</td>
                    <td className="px-4 py-3">{formatNZT(c.created_at)}</td>
                    <td className="px-4 py-3 text-xs text-slate-600">{c.last_error || "-"}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td className="px-4 py-6 text-sm text-slate-600" colSpan={7}>
                    No commands match this filter.
                    <div className="mt-1 text-sm text-slate-600">Next action: use Pipeline to run supplier steps; then use this page for full command history.</div>
                    <div className="mt-2 flex gap-2">
                      <Link className={buttonClass({ variant: "primary" })} href="/pipeline">
                        Open Pipeline
                      </Link>
                      <Link className={buttonClass({ variant: "outline" })} href="/ops/commands">
                        Reset filters
                      </Link>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="flex items-center justify-between border-t border-slate-200 p-4 text-sm">
          <Link
            className={`text-slate-700 underline ${page <= 1 ? "pointer-events-none opacity-40" : ""}`}
            href={prevHref}
          >
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

