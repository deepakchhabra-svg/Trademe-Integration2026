import { NotImplemented } from "../../_components/NotImplemented";

export default function ShipmentsPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Shipments</h1>
        <p className="mt-1 text-sm text-slate-600">Labels, tracking, carrier selection, delivery confirmation.</p>
      </div>

      <NotImplemented
        title="Shipping/label workflow"
        notes={[
          { label: "carrier", detail: "Carrier selection, service level, address validation." },
          { label: "labels", detail: "Generate/print labels, store PDFs, link to order." },
          { label: "tracking", detail: "Capture tracking ref, push status to Trade Me, delivery confirmation." },
          { label: "delays", detail: "In-flight delays, automated customer comms, exception queue." },
        ]}
      />
    </div>
  );
}

