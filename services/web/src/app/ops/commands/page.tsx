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
import { buildQueryString } from "../../_components/pagination";
import { AutoRefresh } from "./AutoRefresh";
import { formatNZT } from "../../_components/time";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Filter, Search } from "lucide-react";

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
    BACKFILL_IMAGES_ONECHEQ: "Backfill images",
    VALIDATE_LAUNCHLOCK: "Validate LaunchLock",
  };
  return map[key] || t;
}

function StatusBadge({ status }: { status: string }) {
  let variant: "default" | "secondary" | "destructive" | "outline" | "emerald" | "amber" | "slate" = "outline";
  const s = status.toUpperCase();
  if (s === "SUCCEEDED") variant = "emerald";
  if (s === "FAILED_FATAL") variant = "destructive";
  if (s === "FAILED_RETRYABLE") variant = "amber";
  if (s === "EXECUTING") variant = "secondary";
  if (s === "PENDING") variant = "outline";
  if (s === "HUMAN_REQUIRED") variant = "destructive";

  return <Badge variant={variant}>{status.replace("_", " ")}</Badge>;
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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Command Log</h1>
          <p className="text-muted-foreground">Queued work ledger and diagnostics.</p>
        </div>
        <div className="flex items-center gap-2">
          <AutoRefresh enabledByDefault={false} />
          <Badge variant="outline">Total: {data.total}</Badge>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Button asChild variant="outline" size="sm"><Link href="/ops/inbox">Inbox (Recommended)</Link></Button>
        <Button asChild variant={status === "NEEDS_ATTENTION" ? "default" : "secondary"} size="sm">
          <Link href={`/ops/commands?${buildQueryString({ per_page: perPage, type, status: "NEEDS_ATTENTION" }, { page: 1 })}`}>Needs attention</Link>
        </Button>
        <Button asChild variant={status === "ACTIVE" ? "default" : "secondary"} size="sm">
          <Link href={`/ops/commands?${buildQueryString({ per_page: perPage, type, status: "ACTIVE" }, { page: 1 })}`}>Active</Link>
        </Button>
        <Button asChild variant={status === "NOT_SUCCEEDED" ? "default" : "secondary"} size="sm">
          <Link href={`/ops/commands?${buildQueryString({ per_page: perPage, type, status: "NOT_SUCCEEDED" }, { page: 1 })}`}>Not Succeeded</Link>
        </Button>
        <Button asChild variant={status === "SUCCEEDED" ? "default" : "secondary"} size="sm">
          <Link href={`/ops/commands?${buildQueryString({ per_page: perPage, type, status: "SUCCEEDED" }, { page: 1 })}`}>Succeeded</Link>
        </Button>
        <Button asChild variant={status === "" ? "default" : "secondary"} size="sm">
          <Link href={`/ops/commands?${buildQueryString({ per_page: perPage, type, status: "" }, { page: 1 })}`}>All</Link>
        </Button>
      </div>

      <Card>
        <div className="p-4 border-b bg-muted/20">
          <form className="flex flex-wrap items-end gap-2" method="get">
            <input type="hidden" name="page" value="1" />
            <div className="space-y-1">
              <label className="text-xs font-semibold uppercase text-muted-foreground">Type</label>
              <Input name="type" defaultValue={type} placeholder="e.g. Scrape" className="h-8 w-40" />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-semibold uppercase text-muted-foreground">Status</label>
              <Input name="status" defaultValue={status} placeholder="Filter status..." className="h-8 w-40" />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-semibold uppercase text-muted-foreground">Per Page</label>
              <select name="per_page" defaultValue={String(perPage)} className="h-8 rounded-md border text-xs w-20 px-2">
                <option value="25">25</option>
                <option value="50">50</option>
                <option value="100">100</option>
                <option value="200">200</option>
              </select>
            </div>
            <Button type="submit" size="sm" className="h-8"><Filter className="mr-2 h-3 w-3" /> Filter</Button>
            <Button asChild variant="ghost" size="sm" className="h-8"><Link href="/ops/commands">Reset</Link></Button>
          </form>
        </div>

        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[100px]">ID</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Attempts</TableHead>
              <TableHead>Priority</TableHead>
              <TableHead>Created</TableHead>
              <TableHead className="w-[30%]">Last Error</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.items.length ? (
              data.items.map(c => (
                <TableRow key={c.id}>
                  <TableCell className="font-mono text-xs">
                    <Link href={`/ops/commands/${c.id}`} className="hover:underline text-primary">
                      {c.id.slice(0, 8)}
                    </Link>
                  </TableCell>
                  <TableCell className="text-xs font-medium">{typeLabel(c.type)}</TableCell>
                  <TableCell><StatusBadge status={c.status} /></TableCell>
                  <TableCell className="text-xs">{c.attempts}/{c.max_attempts}</TableCell>
                  <TableCell className="text-xs">{c.priority}</TableCell>
                  <TableCell className="text-xs whitespace-nowrap">{formatNZT(c.created_at)}</TableCell>
                  <TableCell className="text-xs text-muted-foreground truncate max-w-[200px]" title={c.last_error || ""}>
                    {c.last_error || "-"}
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={7} className="text-center h-24 text-muted-foreground">
                  No commands found.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>

        <div className="flex items-center justify-between p-4 border-t">
          <Button asChild variant="outline" size="sm" disabled={page <= 1}>
            <Link href={prevHref}>Previous</Link>
          </Button>
          <span className="text-xs text-muted-foreground">Page {page}</span>
          <Button asChild variant="outline" size="sm">
            <Link href={nextHref}>Next</Link>
          </Button>
        </div>
      </Card>
    </div>
  );
}
