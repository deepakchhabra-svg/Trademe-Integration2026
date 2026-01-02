import Link from "next/link";
import { apiGet } from "../../_components/api";
import { ResolveButton } from "./Actions";

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
        <div className="space-y-4">
            <div className="flex items-center justify-between gap-4">
                <div>
                    <h1 className="text-lg font-semibold tracking-tight">Duplicate Listings</h1>
                    <p className="mt-1 text-sm text-slate-600">
                        Internal products mapped to multiple Live listings on Trade Me.
                    </p>
                </div>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
                <div className="border-b border-slate-200 p-4">
                    <div className="text-sm font-semibold">
                        {data.count} Duplicate Groups Found
                    </div>
                </div>
                <div className="divide-y divide-slate-100">
                    {!data.duplicates.length ? (
                        <div className="p-8 text-center text-sm text-slate-500">
                            No duplicates found. All clean!
                        </div>
                    ) : (
                        data.duplicates.map((group) => (
                            <div key={group.internal_product_id} className="p-4">
                                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                                    <div>
                                        <div className="text-sm font-medium">
                                            Internal Product ID:{" "}
                                            <Link
                                                href={`/vaults/enriched/${group.internal_product_id}`}
                                                className="font-mono text-indigo-600 hover:underline"
                                            >
                                                {group.internal_product_id}
                                            </Link>
                                        </div>
                                        <div className="mt-2 space-y-1">
                                            {group.listings.map((l) => (
                                                <div
                                                    key={l.id}
                                                    className="flex items-center gap-2 text-xs text-slate-700"
                                                >
                                                    <span className="font-mono text-slate-500">#{l.id}</span>
                                                    <span className="font-semibold">{l.tm_id}</span>
                                                    <span>${l.price?.toFixed(2)}</span>
                                                    <span className="text-slate-400">
                                                        Synced: {l.last_synced || "?"}
                                                    </span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                    <ResolveButton group={group} />
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}
