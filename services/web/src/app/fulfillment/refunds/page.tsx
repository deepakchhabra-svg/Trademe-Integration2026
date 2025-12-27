import { NotImplemented } from "../../_components/NotImplemented";

export default function RefundsPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Refunds</h1>
        <p className="mt-1 text-sm text-slate-600">Refund execution, partial refunds, evidence, audit trail.</p>
      </div>

      <NotImplemented
        title="Refund controls"
        notes={[
          { label: "types", detail: "Full refund, partial refund, shipping-only, goodwill credit." },
          { label: "approval", detail: "RBAC + dual-approval for large refunds (root/power)." },
          { label: "ledger", detail: "Reconcile refunds against Trade Me ledger + bank statements." },
          { label: "abuse", detail: "Detect abusive refund patterns; blacklist/risk flag escalation." },
        ]}
      />
    </div>
  );
}

