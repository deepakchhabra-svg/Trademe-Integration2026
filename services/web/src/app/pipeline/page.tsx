import Link from "next/link";

import { apiGet } from "../_components/api";
import { PageHeader } from "../../components/ui/PageHeader";
import { SectionCard } from "../../components/ui/SectionCard";
import { buttonClass } from "../_components/ui";

type Supplier = { id: number; name: string; base_url: string | null; is_active: boolean | null };

export default async function PipelineIndexPage() {
  const suppliers = await apiGet<Supplier[]>("/suppliers");

  return (
    <div className="space-y-6">
      <PageHeader
        title="Pipeline"
        subtitle="Choose a supplier to run the end-to-end pipeline on a single screen."
        actions={
          <Link className={buttonClass({ variant: "outline" })} href="/ops/trademe">
            Trade Me health →
          </Link>
        }
      />

      <SectionCard title="Suppliers">
        {suppliers.length ? (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            {suppliers.map((s) => (
              <div key={s.id} className="rounded-xl border border-slate-200 bg-white p-4">
                <div className="text-sm font-semibold text-slate-900">{s.name}</div>
                <div className="mt-1 text-xs text-slate-500">Supplier id: {s.id}</div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Link className={buttonClass({ variant: "primary" })} href={`/pipeline/${s.id}`}>
                    Open pipeline
                  </Link>
                  {s.base_url ? (
                    <a className={buttonClass({ variant: "outline" })} href={s.base_url} target="_blank" rel="noreferrer">
                      Site →
                    </a>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="rounded-xl border-2 border-dashed border-slate-200 bg-slate-50 p-6 text-sm text-slate-700">
            No suppliers configured yet. Next action: start the API once to seed defaults, then refresh this page.
          </div>
        )}
      </SectionCard>
    </div>
  );
}

