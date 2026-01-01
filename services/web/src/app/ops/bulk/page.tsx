import { Badge } from "../../_components/Badge";
import { apiGet } from "../../_components/api";
import { BulkOpsForm } from "./ui";

export default async function BulkOpsPage() {
  const suppliers = await apiGet<Array<{ id: number; name: string }>>("/suppliers");
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Bulk ops (advanced)</h1>
          <p className="mt-1 text-sm text-slate-600">
            Batch enqueue console. For day-to-day operation, prefer <span className="font-semibold">Pipeline</span>.
          </p>
        </div>
        <Badge tone="indigo">Operator</Badge>
      </div>

      <BulkOpsForm suppliers={suppliers} />
    </div>
  );
}

