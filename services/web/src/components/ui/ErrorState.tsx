export interface ErrorStateProps {
    error: Error | string;
    retry?: () => void;
}

export function ErrorState({ error, retry }: ErrorStateProps) {
    const message = typeof error === "string" ? error : error.message;

    return (
        <div className="rounded-xl border border-red-200 bg-red-50 p-6" data-testid="error-state">
            <div className="flex items-start gap-3">
                <div className="flex-shrink-0">
                    <svg className="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                        />
                    </svg>
                </div>
                <div className="flex-1">
                    <h3 className="text-sm font-semibold text-red-900" data-testid="error-title">An error occurred</h3>
                    <p className="mt-1 text-sm text-red-800" data-testid="error-message">{message}</p>
                    {retry && (
                        <button
                            type="button"
                            onClick={retry}
                            data-testid="btn-error-retry"
                            className="mt-3 rounded-md bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-700"
                        >
                            Try again
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
