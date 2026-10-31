import { createFileRoute } from "@tanstack/react-router";
import { PageHeader } from "lost-ui/app/page-header";
import { AuditTable } from "@/components/shared/audit/audit-table";

export const Route = createFileRoute("/_app/audit/")({
  component: AuditRoute,
});

function AuditRoute() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Auditoria"
        description="Trilha somente de leitura de comandos, ordens e eventos de risco."
      />
      <AuditTable botId={null} />
    </div>
  );
}
