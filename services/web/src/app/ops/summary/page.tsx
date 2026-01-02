import { apiGet } from "../../_components/api";
import { formatNZT } from "../../_components/time";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Activity, AlertTriangle, DollarSign, Package, Layers, ShoppingCart, CheckCircle, Clock } from "lucide-react";

export default async function SummaryPage() {
    const [summary, kpis] = await Promise.all([
        apiGet<any>("/ops/summary"),
        apiGet<any>("/ops/kpis"),
    ]);

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
                    <p className="text-muted-foreground">Store health and system vitals.</p>
                </div>
                <Badge variant="outline" className="text-muted-foreground">
                    Last updated: {formatNZT(summary.utc)}
                </Badge>
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <KPI
                    title="Sales Today"
                    value={kpis.sales_today}
                    icon={DollarSign}
                    trend="Daily sales count"
                />
                <KPI
                    title="Listed Today"
                    value={kpis.listed_today}
                    icon={Package}
                    trend="New live listings"
                />
                <KPI
                    title="Queue Backlog"
                    value={summary.commands.pending}
                    icon={Layers}
                    trend="Commands pending"
                />
                <KPI
                    title="Failures Today"
                    value={kpis.failures_today}
                    icon={AlertTriangle}
                    status={kpis.failures_today > 0 ? "destructive" : "default"}
                    trend="Failed commands"
                />
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
                <Card className="col-span-4">
                    <CardHeader>
                        <CardTitle>Inventory Pipeline</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <PipelineRow
                            label="Raw Items"
                            value={summary.vaults.raw_total}
                            sub={`(${summary.vaults.raw_present} present)`}
                            icon={Package}
                        />
                        <PipelineRow
                            label="Enriched"
                            value={summary.vaults.enriched_total}
                            sub={`(${summary.vaults.enriched_ready} ready)`}
                            icon={CheckCircle}
                        />
                        <PipelineRow
                            label="Live Listings"
                            value={summary.vaults.listings_live}
                            tone="success"
                            icon={Activity}
                            highlight
                        />
                        <PipelineRow
                            label="Draft Listings"
                            value={summary.vaults.listings_dry}
                            tone="warning"
                            icon={Clock}
                        />
                    </CardContent>
                </Card>

                <Card className="col-span-3">
                    <CardHeader>
                        <CardTitle>System Health</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex items-center justify-between rounded-lg border p-4">
                            <div className="flex items-center gap-4">
                                <div className="rounded-full bg-amber-100 p-2">
                                    <ShoppingCart className="h-5 w-5 text-amber-600" />
                                </div>
                                <div>
                                    <div className="text-sm font-medium">Pending Orders</div>
                                    <div className="text-xs text-muted-foreground">Needs fulfillment</div>
                                </div>
                            </div>
                            <div className="text-2xl font-bold">{summary.orders.pending}</div>
                        </div>

                        <div className="flex items-center justify-between rounded-lg border p-4">
                            <div className="flex items-center gap-4">
                                <div className="rounded-full bg-red-100 p-2">
                                    <AlertTriangle className="h-5 w-5 text-red-600" />
                                </div>
                                <div>
                                    <div className="text-sm font-medium">Human Attention</div>
                                    <div className="text-xs text-muted-foreground">Blocked commands</div>
                                </div>
                            </div>
                            <div className="text-2xl font-bold">{summary.commands.human_required}</div>
                        </div>

                        <div className="grid grid-cols-2 gap-4 pt-2">
                            <div className="rounded-lg bg-muted p-3 text-center">
                                <div className="text-xs text-muted-foreground uppercase">Executing</div>
                                <div className="text-lg font-bold">{summary.commands.executing}</div>
                            </div>
                            <div className="rounded-lg bg-muted p-3 text-center">
                                <div className="text-xs text-muted-foreground uppercase">Failed (Total)</div>
                                <div className="text-lg font-bold">{summary.commands.failed}</div>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}

function KPI({ title, value, icon: Icon, trend, status }: any) {
    return (
        <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                    {title}
                </CardTitle>
                <Icon className={`h-4 w-4 text-muted-foreground ${status === 'destructive' ? 'text-red-500' : ''}`} />
            </CardHeader>
            <CardContent>
                <div className={`text-2xl font-bold ${status === 'destructive' ? 'text-red-500' : ''}`}>{value}</div>
                <p className="text-xs text-muted-foreground">
                    {trend}
                </p>
            </CardContent>
        </Card>
    )
}

function PipelineRow({ label, value, sub, icon: Icon, tone, highlight }: any) {
    let colorClass = "text-muted-foreground";
    if (tone === "success") colorClass = "text-emerald-600";
    if (tone === "warning") colorClass = "text-amber-600";
    if (tone === "destructive") colorClass = "text-red-600";

    return (
        <div className={`flex items-center justify-between ${highlight ? 'bg-muted/40 p-2 rounded-md -mx-2' : ''}`}>
            <div className="flex items-center gap-2">
                {Icon && <Icon className={`h-4 w-4 ${colorClass}`} />}
                <span className="text-sm font-medium">{label}</span>
            </div>
            <div className="flex items-center gap-2">
                {sub && <span className="text-xs text-muted-foreground">{sub}</span>}
                <span className={`font-bold ${tone === 'success' ? 'text-emerald-600' : ''}`}>{value}</span>
            </div>
        </div>
    )
}
