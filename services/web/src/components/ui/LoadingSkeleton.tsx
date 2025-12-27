export function TableSkeleton({ rows = 5, columns = 6 }: { rows?: number; columns?: number }) {
    return (
        <div className="w-full animate-pulse">
            <div className="mb-3 h-8 w-full rounded bg-slate-100" />
            {Array.from({ length: rows }).map((_, i) => (
                <div key={i} className="mb-2 flex gap-4">
                    {Array.from({ length: columns }).map((_, j) => (
                        <div key={j} className="h-6 flex-1 rounded bg-slate-100" />
                    ))}
                </div>
            ))}
        </div>
    );
}

export function CardSkeleton({ count = 3 }: { count?: number }) {
    return (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: count }).map((_, i) => (
                <div key={i} className="h-32 animate-pulse rounded-xl bg-slate-100" />
            ))}
        </div>
    );
}

export function TextSkeleton({ lines = 3 }: { lines?: number }) {
    return (
        <div className="space-y-2 animate-pulse">
            {Array.from({ length: lines }).map((_, i) => (
                <div
                    key={i}
                    className="h-4 rounded bg-slate-100"
                    style={{ width: i === lines - 1 ? "60%" : "100%" }}
                />
            ))}
        </div>
    );
}
