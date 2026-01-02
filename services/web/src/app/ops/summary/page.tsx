import { apiGet } from "../../_components/api";
import { Badge } from "../../_components/Badge";
import { formatNZT } from "../../_components/time";

export default async function SummaryPage() {
    const [summary, kpis] = await Promise.all([
        apiGet<any>("/ops/summary"),
        apiGet<any>("/ops/kpis"),
    ]);

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-xl font-bold tracking-tight">Store Health Dashboard</h1>
                    <p className="text-sm text-slate-600">Daily performance and system vitals.</p>
                </div>
                <div className="text-xs text-slate-500">Updated: {formatNZT(summary.utc)}</div>
            </div>

            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                <KPI title="Sales Today" value={kpis.sales_today} tone="emerald" />
                <KPI title="Listed Today" value={kpis.listed_today} tone="indigo" />
                <KPI title="Queue Backlog" value={summary.commands.pending} tone="blue" />
                <KPI
                    title="Failures Today"
                    value={kpis.failures_today}
                    tone={kpis.failures_today > 0 ? "red" : "slate"}
                />
            </div>

            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                    <h3 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">Inventory Pipeline</h3>
                    <div className="space-y-4">
                        <Row label="Raw Items" value={summary.vaults.raw_total} sub={`(${summary.vaults.raw_present} present)`} />
                        <Row label="Enriched" value={summary.vaults.enriched_total} sub={`(${summary.vaults.enriched_ready} ready)`} />
                        <Row label="Listings (Live)" value={summary.vaults.listings_live} tone="emerald" />
                        <Row label="Listings (Draft)" value={summary.vaults.listings_dry} tone="amber" />
                    </div>
                </div>

                <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                    <h3 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">System Health</h3>
                    <div className="space-y-4">
                        <Row label="Pending Orders" value={summary.orders.pending} tone={summary.orders.pending > 0 ? "amber" : "slate"} />
                        <Row label="Human Required" value={summary.commands.human_required} tone={summary.commands.human_required > 0 ? "red" : "slate"} />
                        <Row label="Executing" value={summary.commands.executing} />
                        <Row label="Failed (Total)" value={summary.commands.failed} />
                    </div>
                </div>
            </div>
        </div>
    );
}

function KPI({ title, value, tone = "slate" }: { title: string; value: number; tone?: "emerald" | "indigo" | "blue" | "red" | "amber" | "slate" }) {
    const colors = {
        emerald: "bg-emerald-50 text-emerald-700 border-emerald-100",
        indigo: "bg-indigo-50 text-indigo-700 border-indigo-100",
        blue: "bg-blue-50 text-blue-700 border-blue-100",
        red: "bg-red-50 text-red-700 border-red-100",
        amber: "bg-amber-50 text-amber-700 border-amber-100",
        slate: "bg-slate-50 text-slate-700 border-slate-100",
    };

    return (
        <div className={`rounded-xl border p-4 ${colors[tone]}`}>
            <div className="text-xs font-medium uppercase tracking-wide opacity-80">{title}</div>
            <div className="mt-1 text-2xl font-bold">{value}</div>
        </div>
    );
}

function Row({ label, value, sub, tone }: { label: string; value: number; sub?: string; tone?: string }) {
    return (
        <div className="flex items-center justify-between">
            <div className="text-sm font-medium text-slate-700">{label}</div>
            <div className="flex items-center gap-2">
                {sub && <span className="text-xs text-slate-400">{sub}</span>}
                <span className={`text-sm font-bold ${tone === "red" ? "text-red-600" : tone === "emerald" ? "text-emerald-600" : tone === "amber" ? "text-amber-600" : "text-slate-900"}`}>
                    {value}
                </span>
            </div>
        </div>
    );
}
