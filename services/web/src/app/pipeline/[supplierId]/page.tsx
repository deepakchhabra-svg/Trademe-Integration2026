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

  const initial = await apiGet<PipelineResp>(`/ops/suppliers/${supplierId}/pipeline`);

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

