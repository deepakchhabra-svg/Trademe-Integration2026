import Link from "next/link";
import { apiGet } from "../../_components/api";
import { ResolveButton } from "./Actions";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Link2, ExternalLink } from "lucide-react";

type Listing = {
    id: number;
    tm_id: string;
    price: number | null;
    last_synced?: string;
};

type DuplicateGroup = {
    internal_product_id: number;
    listings: Listing[];
};

type DuplicatesResponse = {
    count: number;
    duplicates: DuplicateGroup[];
};

export default async function DuplicatesPage() {
    const data = await apiGet<DuplicatesResponse>("/ops/duplicates");

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Duplicate Listings</h1>
                <p className="text-muted-foreground">Internal products mapped to multiple Live listings on Trade Me.</p>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Link2 className="h-5 w-5" />
                        {data.count} Groups Found
                    </CardTitle>
                </CardHeader>
                <CardContent className="divide-y">
                    {!data.duplicates.length ? (
                        <div className="py-8 text-center text-muted-foreground">No duplicates found. All clean!</div>
                    ) : (
                        data.duplicates.map(group => (
                            <div key={group.internal_product_id} className="py-4 first:pt-0 last:pb-0 flex flex-col sm:flex-row items-start justify-between gap-4">
                                <div className="w-full">
                                    <div className="flex items-center gap-2 mb-2">
                                        <Badge variant="outline">IP #{group.internal_product_id}</Badge>
                                        <Link
                                            href={`/vaults/enriched/${group.internal_product_id}`}
                                            className="text-sm font-medium text-primary hover:underline flex items-center gap-1"
                                        >
                                            View Product <ExternalLink className="h-3 w-3" />
                                        </Link>
                                    </div>
                                    <div className="bg-muted/50 rounded-md p-3 space-y-2">
                                        {group.listings.map(l => (
                                            <div key={l.id} className="flex items-center justify-between text-sm">
                                                <div className="flex items-center gap-2">
                                                    <span className="font-mono text-xs text-muted-foreground">#{l.id}</span>
                                                    <span className="font-semibold">{l.tm_id}</span>
                                                </div>
                                                <div className="flex items-center gap-4">
                                                    <span>${l.price?.toFixed(2)}</span>
                                                    <span className="text-xs text-muted-foreground hidden sm:inline">Synced {l.last_synced}</span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                                <div className="shrink-0">
                                    <ResolveButton group={group} />
                                </div>
                            </div>
                        ))
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
