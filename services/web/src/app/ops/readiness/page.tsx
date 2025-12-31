import { apiGet } from "../../_components/api";
import Link from "next/link";
import { PageHeader } from "../../../components/ui/PageHeader";
import { SectionCard } from "../../../components/ui/SectionCard";
import { DataTable } from "../../../components/tables/DataTable";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import { buttonClass } from "../../_components/ui";

type Readiness = {
  totals: { internal_products: number; ready: number; blocked: number };
  top_blockers: [string, number][];
  by_supplier: [string, number][];
  by_source_category: [string, number][];
  limit_applied: number;
};

export default async function PublishReadinessPage() {
  const r = await apiGet<Readiness>("/ops/readiness");

  const pct = r.totals.internal_products ? (r.totals.ready / r.totals.internal_products) * 100 : 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Publish Readiness"
        subtitle={
          <div className="flex items-center gap-2">
            <span className="text-slate-600">
              Ready: <span className="font-semibold text-slate-900">{r.totals.ready}</span> / {r.totals.internal_products}{" "}
              ({pct.toFixed(1)}%)
            </span>
            <span className="text-slate-300">|</span>
            <span className="text-slate-600">
              Blocked: <span className="font-semibold text-slate-900">{r.totals.blocked}</span>
            </span>
            <span className="text-slate-300">|</span>
            <span className="text-slate-600">Scan limit: {r.limit_applied}</span>
          </div>
        }
        actions={<StatusBadge status={r.totals.blocked ? "HUMAN_REQUIRED" : "SUCCESS"} label={r.totals.blocked ? "Needs work" : "All clear"} />}
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <SectionCard title="Ready">
          <div className="text-3xl font-semibold tracking-tight text-slate-900" data-testid="readiness-ready">
            {r.totals.ready}
          </div>
          <div className="mt-1 text-sm text-slate-600">Passing local publish gates</div>
        </SectionCard>
        <SectionCard title="Blocked">
          <div className="text-3xl font-semibold tracking-tight text-slate-900" data-testid="readiness-blocked">
            {r.totals.blocked}
          </div>
          <div className="mt-1 text-sm text-slate-600">Missing required fields/images/category</div>
        </SectionCard>
        <SectionCard title="Total">
          <div className="text-3xl font-semibold tracking-tight text-slate-900" data-testid="readiness-total">
            {r.totals.internal_products}
          </div>
          <div className="mt-1 text-sm text-slate-600">Internal products scanned</div>
        </SectionCard>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <SectionCard title="Top Blockers" subtitle="Why items cannot publish yet">
          <DataTable
            columns={[
              { key: "reason", label: "Reason" },
              { key: "count", label: "Count", sortable: true, className: "text-right" },
            ]}
            data={r.top_blockers.map(([reason, count]) => ({ reason, count }))}
            totalCount={r.top_blockers.length}
            currentPage={1}
            pageSize={r.top_blockers.length || 1}
            emptyState={
              <div className="text-center">
                <div className="text-sm font-semibold text-slate-900">No blockers found.</div>
                <div className="mt-1 text-sm text-slate-600">Next action: validate drafts on Trade Me Health, then publish from Pipeline/Runbook.</div>
                <div className="mt-3 flex justify-center gap-2">
                  <Link className={buttonClass({ variant: "outline" })} href="/ops/trademe">
                    Trade Me health →
                  </Link>
                  <Link className={buttonClass({ variant: "primary" })} href="/pipeline">
                    Pipeline →
                  </Link>
                </div>
              </div>
            }
            stickyHeader={false}
          />
        </SectionCard>

        <SectionCard title="By Supplier" subtitle="Inventory size by supplier">
          <DataTable
            columns={[
              { key: "supplier", label: "Supplier" },
              { key: "count", label: "Count", sortable: true, className: "text-right" },
            ]}
            data={r.by_supplier.map(([supplier, count]) => ({ supplier, count }))}
            totalCount={r.by_supplier.length}
            currentPage={1}
            pageSize={r.by_supplier.length || 1}
            emptyMessage="No suppliers"
            stickyHeader={false}
          />
        </SectionCard>
      </div>

      <SectionCard title="Top Source Categories" subtitle="Where volume is coming from">
        <DataTable
          columns={[
            { key: "source_category", label: "Source category" },
            { key: "count", label: "Count", sortable: true, className: "text-right" },
          ]}
          data={r.by_source_category.map(([source_category, count]) => ({ source_category, count }))}
          totalCount={r.by_source_category.length}
          currentPage={1}
          pageSize={Math.min(100, r.by_source_category.length || 1)}
          emptyMessage="No categories"
          stickyHeader={true}
        />
      </SectionCard>
    </div>
  );
}

