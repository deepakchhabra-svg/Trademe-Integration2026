import { buildQueryString } from "../../_components/pagination";
import { redirect } from "next/navigation";

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
  const perPage = Math.min(200, Math.max(10, Number(sp.per_page || "50")));
  const view = (sp.view || "attention").toLowerCase();
  const type = sp.type || "";
  const status = viewToStatus(view);

  // This page was an early duplicate of Command log filters.
  // Keep the route for compatibility, but redirect to the canonical command ledger.
  redirect(`/ops/commands?${buildQueryString({ per_page: perPage, type, status }, { page: 1 })}`);
}

