"use client";

import { useEffect } from "react";
import { ErrorState } from "../components/ui/ErrorState";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  const msg = error?.message || "Unknown error";
  const friendly =
    msg.toLowerCase().includes("backend offline")
      ? new Error("Backend offline. Start the API on http://127.0.0.1:8000 (see runbook).")
      : error;

  return (
    <html>
      <body className="bg-slate-50 text-slate-900">
        <div className="mx-auto max-w-3xl p-6">
          <ErrorState error={friendly} retry={reset} />
        </div>
      </body>
    </html>
  );
}

