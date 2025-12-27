import Link from "next/link";

import { apiGet } from "../../_components/api";
import { Badge } from "../../_components/Badge";
import { PolicyEditor } from "./PolicyEditor";

type Supplier = { id: number; name: string; base_url: string | null; is_active: boolean };

export default async function SupplierDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const supplierId = Number(id);
  const suppliers = await apiGet<Supplier[]>("/suppliers");
  const s = suppliers.find((x) => x.id === supplierId);

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Link className="text-sm text-slate-600 underline" href="/suppliers">
              Suppliers
            </Link>
            <span className="text-sm text-slate-400">/</span>
            <span className="text-sm font-medium text-slate-900">{supplierId}</span>
          </div>
          <h1 className="mt-2 text-lg font-semibold tracking-tight">{s?.name || "Supplier"}</h1>
          <p className="mt-1 text-sm text-slate-600">Per-supplier controls and presets.</p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <Badge tone={s?.is_active ? "emerald" : "red"}>{s?.is_active ? "active" : "inactive"}</Badge>
          <div className="font-mono text-[11px] text-slate-600">{s?.base_url || "-"}</div>
        </div>
      </div>

      <PolicyEditor supplierId={supplierId} />
    </div>
  );
}

