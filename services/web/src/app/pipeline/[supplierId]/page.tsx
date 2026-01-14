import Link from "next/link";

import { apiGet } from "../../_components/api";
import { PageHeader } from "../../../components/ui/PageHeader";
import { buttonClass } from "../../_components/ui";
import { PipelineClient } from "./PipelineClient";

type PipelineResp = Parameters<typeof PipelineClient>[0]["initial"];

export default async function SupplierPipelinePage({ params }: { params: Promise<{ supplierId: string }> }) {
  const p = await params;
  const supplierId = Number(p.supplierId);
  if (!supplierId || Number.isNaN(supplierId)) {
    return (
      <div className="space-y-4">
        <PageHeader title="Pipeline" subtitle="Invalid supplier id." actions={<Link className={buttonClass({ variant: "link" })} href="/pipeline">Back</Link>} />
      </div>
    );
  }

  let initial: PipelineResp | null = null;
  let error: string | null = null;

  try {
    initial = await apiGet<PipelineResp>(`/ops/suppliers/${supplierId}/pipeline`);
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
    console.error(`Pipeline data fetch failed for supplier ${supplierId}:`, error);
  }

  if (error || !initial) {
    return (
      <div className="space-y-4">
        <PageHeader
          title="Pipeline Error"
          subtitle={`Failed to load pipeline for supplier ${supplierId}`}
          actions={<Link className={buttonClass({ variant: "outline" })} href="/pipeline">Back to Suppliers</Link>}
        />
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <p className="text-sm text-red-900 mb-2">Unable to fetch pipeline data from the API.</p>
          {error && (
            <p className="text-xs font-mono text-red-700">{error}</p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Pipeline · ${initial.supplier.name}`}
        subtitle="Single operator screen: Scrape → Images → Enrich → Draft → Validate → Publish."
        actions={
          <div className="flex items-center gap-2">
            {initial.supplier.base_url ? (
              <a className={buttonClass({ variant: "outline" })} href={initial.supplier.base_url} target="_blank" rel="noreferrer">
                Supplier site →
              </a>
            ) : null}
            <Link className={buttonClass({ variant: "outline" })} href="/pipeline">
              All suppliers
            </Link>
          </div>
        }
      />

      <PipelineClient supplierId={supplierId} initial={initial} />
    </div>
  );
}

