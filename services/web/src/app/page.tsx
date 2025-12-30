import { apiGet } from "./_components/api";
import { WorkbenchClient } from "./WorkbenchClient";

type OpsSummary = {
  utc?: string;
  commands: { total: number; pending: number; executing: number; human_required: number; failed: number };
  vaults: {
    raw_total: number;
    raw_present: number;
    enriched_total: number;
    enriched_ready: number;
    listings_total: number;
    listings_dry_run: number;
    listings_live: number;
  };
  orders: { total: number; pending_fulfillment: number };
};

export default async function Home() {
  const summary = await apiGet<OpsSummary>("/ops/summary");

  return <WorkbenchClient initial={summary} />;
}
