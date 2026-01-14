import Link from "next/link";
import { apiGet } from "../../_components/api";
import { formatNZT } from "../../_components/time";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Activity, AlertTriangle, DollarSign, Package, Layers, ShoppingCart, CheckCircle, Clock } from "lucide-react";

export default async function SummaryPage() {
    type SummaryData = {
        utc: string;
        vaults: { raw_total: number; raw_present: number; enriched_total: number; enriched_ready: number; listings_live: number; listings_dry: number };
        commands: { pending: number; executing: number; human_required: number; failed: number };
        orders: { pending: number };
    };
    type KpisData = { sales_today: number; listed_today: number; failures_today: number };
    
    let summary: SummaryData | null = null;
    let kpis: KpisData | null = null;
    let error: string | null = null;

    try {
        [summary, kpis] = await Promise.all([
            apiGet<SummaryData>("/ops/summary"),
            apiGet<KpisData>("/ops/kpis"),
        ]);
    } catch (e) {
        error = e instanceof Error ? e.message : String(e);
        console.error("Dashboard data fetch failed:", error);
    }

    if (error || !summary || !kpis) {
        return (
            <div className="space-y-6">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
                    <p className="text-muted-foreground">Store health and system vitals.</p>
                </div>
                <Card>
                    <CardHeader>
                        <CardTitle className="text-red-600">Failed to Load Dashboard</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <p className="text-sm text-muted-foreground mb-4">
                            Unable to fetch dashboard data from the API. This usually means:
                        </p>
                        <ul className="list-disc list-inside text-sm text-muted-foreground space-y-1 mb-4">
                            <li>The API backend is offline or unreachable</li>
                            <li>Network connectivity issues</li>
                            <li>API authentication problems</li>
                        </ul>
                        {error && (
                            <div className="mt-4 p-3 bg-muted rounded-md">
                                <p className="text-xs font-mono text-red-600">{error}</p>
                            </div>
                        )}
                        <div className="mt-4 flex gap-2">
                            <Link href="/pipeline" className="text-sm text-blue-600 hover:underline">
                                Try Pipeline →
                            </Link>
                            <Link href="/suppliers" className="text-sm text-blue-600 hover:underline">
                                Try Suppliers →
                            </Link>
                        </div>
                    </CardContent>
                </Card>
            </div>
        );
    }

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
                    href="/orders"
                />
                <KPI
                    title="Listed Today"
                    value={kpis.listed_today}
                    icon={Package}
                    trend="New live listings"
                    href="/vaults/live"
                />
                <KPI
                    title="Queue Backlog"
                    value={summary.commands.pending}
                    icon={Layers}
                    trend="Commands pending"
                    href="/ops/inbox"
                />
                <KPI
                    title="Failures Today"
                    value={kpis.failures_today}
                    icon={AlertTriangle}
                    status={kpis.failures_today > 0 ? "destructive" : "default"}
                    trend="Failed commands"
                    href="/ops/commands?status=NEEDS_ATTENTION"
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
                            href="/vaults/raw"
                        />
                        <PipelineRow
                            label="Enriched"
                            value={summary.vaults.enriched_total}
                            sub={`(${summary.vaults.enriched_ready} ready)`}
                            icon={CheckCircle}
                            href="/vaults/enriched"
                        />
                        <PipelineRow
                            label="Live Listings"
                            value={summary.vaults.listings_live}
                            tone="success"
                            icon={Activity}
                            highlight
                            href="/vaults/live"
                        />
                        <PipelineRow
                            label="Draft Listings"
                            value={summary.vaults.listings_dry}
                            tone="warning"
                            icon={Clock}
                            href="/vaults/live?status=DRY_RUN"
                        />
                    </CardContent>
                </Card>

                <Card className="col-span-3">
                    <CardHeader>
                        <CardTitle>System Health</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="relative group flex items-center justify-between rounded-lg border p-4 hover:bg-muted/50 transition-colors">
                            <Link href="/orders" className="absolute inset-0 z-10" aria-label="Pending Orders"><span className="sr-only">View Pending Orders</span></Link>
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

                        <div className="relative group flex items-center justify-between rounded-lg border p-4 hover:bg-muted/50 transition-colors">
                            <Link href="/ops/inbox" className="absolute inset-0 z-10" aria-label="Inbox"><span className="sr-only">View Inbox</span></Link>
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
                            <div className="relative group rounded-lg bg-muted p-3 text-center hover:bg-muted/80 transition-colors">
                                <Link href="/ops/commands?status=EXECUTING" className="absolute inset-0 z-10" aria-label="Executing"><span className="sr-only">View Executing</span></Link>
                                <div className="text-xs text-muted-foreground uppercase">Executing</div>
                                <div className="text-lg font-bold">{summary.commands.executing}</div>
                            </div>
                            <div className="relative group rounded-lg bg-muted p-3 text-center hover:bg-muted/80 transition-colors">
                                <Link href="/ops/commands?status=NEEDS_ATTENTION" className="absolute inset-0 z-10" aria-label="Failed"><span className="sr-only">View Failed</span></Link>
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

function KPI({ title, value, icon: Icon, trend, status, href }: { title: string; value: string | number; icon: React.ComponentType<{ className?: string }>; trend?: string; status?: string; href?: string }) {
    return (
        <Card className="relative group hover:bg-muted/50 transition-colors">
            {href && (
                <Link href={href} className="absolute inset-0 z-10" aria-label={title}>
                    <span className="sr-only">View {title}</span>
                </Link>
            )}
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                    {title}
                </CardTitle>
                <Icon className={`h-4 w-4 text-muted-foreground ${status === 'destructive' ? 'text-red-500' : ''}`} />
            </CardHeader>
            <CardContent>
                <div className="text-2xl font-bold">{value}</div>
                <p className="text-xs text-muted-foreground">
                    {trend}
                </p>
            </CardContent>
        </Card>
    )
}

function PipelineRow({ label, value, sub, icon: Icon, tone, highlight, href }: { label: string; value: string | number; sub?: string; icon: React.ComponentType<{ className?: string }>; tone?: string; highlight?: boolean; href?: string }) {
    let colorClass = "text-muted-foreground";
    if (tone === "success") colorClass = "text-emerald-600";
    if (tone === "warning") colorClass = "text-amber-600";
    if (tone === "destructive") colorClass = "text-red-600";

    return (
        <div className={`relative group flex items-center justify-between ${highlight ? 'bg-muted/40 p-2 rounded-md -mx-2' : ''} hover:bg-muted/50 p-2 rounded-md -mx-2 transition-colors`}>
            {href && (
                <Link href={href} className="absolute inset-0 z-10" aria-label={label}>
                    <span className="sr-only">View {label}</span>
                </Link>
            )}
            <div className="flex items-center gap-2">
                {Icon && <Icon className={`h-4 w-4 ${colorClass}`} />}
                <span className="text-sm font-medium">{label}</span>
            </div>
            <div className="flex items-center gap-2">
                {sub && <span className="text-xs text-muted-foreground">{sub}</span>}
                <span className="font-bold">{value}</span>
            </div>
        </div>
    )
}

