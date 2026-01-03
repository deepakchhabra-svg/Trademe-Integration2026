import fs from "fs";
import path from "path";

import { PageHeader } from "../../../components/ui/PageHeader";
import Link from "next/link";
import { buttonClass } from "../../_components/ui";

export const dynamic = "force-dynamic";

function resolveDocsPath(parts: string[]): string | null {
  const repoRoot = path.resolve(process.cwd(), "..", ".."); // services/web -> repo root
  const docsRoot = path.resolve(repoRoot, "docs");
  const rel = parts.join("/");
  const full = path.resolve(docsRoot, rel);
  if (full === docsRoot) return null;
  if (!full.startsWith(docsRoot + path.sep)) return null; // prevent traversal
  return full;
}

export default async function DocsPage({ params }: { params: Promise<{ path: string[] }> }) {
  const p = await params;
  const parts = Array.isArray(p.path) ? p.path : [];
  const full = resolveDocsPath(parts);
  const title = parts.join("/") || "docs";

  let body = "";
  let error: string | null = null;
  if (!full) {
    error = "Invalid docs path.";
  } else {
    try {
      body = fs.readFileSync(full, "utf-8");
    } catch (e) {
      error = e instanceof Error ? e.message : "Doc not found";
    }
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title={`Docs · ${title}`}
        subtitle="Static documentation bundled with this repo."
        actions={
          <Link className={buttonClass({ variant: "outline" })} href="/access">
            Back to Access
          </Link>
        }
      />
      {error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-900">{error}</div>
      ) : (
        <pre className="rounded-xl border border-slate-200 bg-white p-4 text-[12px] leading-5 text-slate-900 whitespace-pre-wrap">
          {body}
        </pre>
      )}
    </div>
  );
}

