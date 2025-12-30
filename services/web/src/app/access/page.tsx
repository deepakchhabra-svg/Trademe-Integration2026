import Link from "next/link";

import { TokenSetter } from "../_components/TokenSetter";
import { PageHeader } from "../../components/ui/PageHeader";
import { SectionCard } from "../../components/ui/SectionCard";

export default function AccessPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Access & tokens"
        subtitle="Set your operator token locally (stored in a cookie). This unlocks protected API endpoints like the Ops Workbench and /media."
        actions={
          <Link className="text-sm underline text-slate-700 hover:text-slate-900" href="/docs/LOCAL_OPERATOR_RUNBOOK_WINDOWS.md">
            Runbook →
          </Link>
        }
      />

      <SectionCard title="Operator token">
        <TokenSetter />
        <div className="mt-3 text-[11px] text-slate-500">
          - For Ops pages, set <span className="font-mono">RETAIL_OS_POWER_TOKEN</span> in <span className="font-mono">.env</span>.
          <br />- For Settings, set <span className="font-mono">RETAIL_OS_ROOT_TOKEN</span>.
        </div>
      </SectionCard>
    </div>
  );
}

