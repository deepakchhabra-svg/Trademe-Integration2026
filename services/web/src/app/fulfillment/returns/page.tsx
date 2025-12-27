import { NotImplemented } from "../../_components/NotImplemented";

export default function ReturnsPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Returns</h1>
        <p className="mt-1 text-sm text-slate-600">Return cases (RMA), inbound tracking, inspection, resolution.</p>
      </div>

      <NotImplemented
        title="Returns workflow"
        notes={[
          { label: "case intake", detail: "Create return case, reason codes, customer evidence." },
          { label: "inbound", detail: "Return label + tracking, expected arrival, delay handling." },
          { label: "inspection", detail: "Condition check, restock vs discard vs supplier return." },
          { label: "resolution", detail: "Replace/refund/repair, audit trail, close case." },
        ]}
      />
    </div>
  );
}

