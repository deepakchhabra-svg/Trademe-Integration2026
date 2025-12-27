import { NotImplemented } from "../../_components/NotImplemented";

export default function RiskPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Risk & fraud</h1>
        <p className="mt-1 text-sm text-slate-600">
          Blacklists, scam/spam checks, duplicate orders, returning customer signals.
        </p>
      </div>

      <NotImplemented
        title="Risk engine + controls"
        notes={[
          { label: "blacklist", detail: "Buyer email/name/address blacklists; allowlists; audit trail." },
          { label: "duplicate orders", detail: "Detect duplicates by buyer+listing+time window; auto-hold." },
          { label: "scam checks", detail: "Heuristics for suspicious messages, mismatched addresses, high-risk categories." },
          { label: "returning customers", detail: "Customer profile: prior orders, refund rate, delivery issues, messaging tone." },
        ]}
      />
    </div>
  );
}

