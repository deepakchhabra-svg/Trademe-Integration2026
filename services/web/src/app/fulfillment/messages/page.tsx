import { NotImplemented } from "../../_components/NotImplemented";

export default function MessagesPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Customer comms</h1>
        <p className="mt-1 text-sm text-slate-600">Templates, delay notices, order updates, feedback requests.</p>
      </div>

      <NotImplemented
        title="Messaging automation"
        notes={[
          { label: "templates", detail: "Standard templates for: paid, packed, shipped, delayed, delivered, closure." },
          { label: "trade me", detail: "Send messages via Trade Me endpoints; log all comms in AuditLog." },
          { label: "feedback", detail: "Post-delivery feedback request; seller feedback loop." },
          { label: "spam/scam", detail: "Auto-detect abusive messages; operator escalation." },
        ]}
      />
    </div>
  );
}

