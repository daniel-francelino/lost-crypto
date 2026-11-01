import { CheckCheck } from "lucide-react";
import { useState } from "react";
import { PageHeader } from "lost-ui/app/page-header";
import { DataTable, type DataTableColumn } from "lost-ui/data/data-table";
import { EmptyState as Empty } from "@/components/shared/feedback/empty-state";
import { FormSelect } from "lost-ui/forms/form-select";
import { Badge } from "lost-ui/ui/badge";
import { Button } from "lost-ui/ui/button";
import { toast } from "lost-ui/ui/sonner";
import { ErrorBlock } from "@/components/shared/feedback/query-boundary";
import { UpdatedAt } from "@/components/shared/feedback/updated-at";
import { AlertSeverityBadge } from "@/components/shared/status/badges";
import { useAlerts, useMarkAlertRead, useMarkAllAlertsRead } from "@/hooks/shared/use-alerts";
import { useSessionUser } from "@/hooks/shared/use-session";
import type { Alert } from "@/lib/shared/alerts/alerts.api";
import { errorMessage } from "@/lib/shared/api/messages";
import { Capability, WHY_ADMIN_ONLY, can } from "@/lib/shared/capability";
import { formatDateTime } from "@/lib/shared/dates";
import { AlertSeverity } from "@/lib/shared/enums";
import { alertKindLabel, alertSeverityLabel } from "@/lib/shared/labels";

const PAGE_SIZE = 25;
const ALL = "all";
const UNREAD = "unread";

const SEVERITY_ITEMS = [
  { label: "Todas as severidades", value: ALL },
  ...Object.values(AlertSeverity).map((value) => ({ label: alertSeverityLabel(value), value })),
];
const READ_ITEMS = [
  { label: "Todos os alertas", value: ALL },
  { label: "Somente não lidos", value: UNREAD },
];

const severityFilter = (value: string): AlertSeverity | null =>
  Object.values(AlertSeverity).find((severity) => severity === value) ?? null;

export function AlertsPage() {
  const user = useSessionUser();
  const canAcknowledge = can(user, Capability.AlertsAcknowledge);
  const [page, setPage] = useState(1);
  const [severity, setSeverity] = useState(ALL);
  const [read, setRead] = useState(ALL);
  const filtered = severity !== ALL || read !== ALL;
  const query = useAlerts({
    unreadOnly: read === UNREAD,
    severity: severityFilter(severity),
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  });
  const markRead = useMarkAlertRead();
  const markAll = useMarkAllAlertsRead();

  const acknowledge = async (alert: Alert) => {
    try {
      await markRead.mutateAsync(alert.id);
    } catch (error) {
      toast.error(errorMessage(error));
    }
  };
  const acknowledgeAll = async () => {
    try {
      const marked = await markAll.mutateAsync();
      toast.success(
        marked === 0 ? "Nenhum alerta novo." : `${marked} alertas marcados como lidos.`,
      );
    } catch (error) {
      toast.error(errorMessage(error));
    }
  };

  const columns: DataTableColumn<Alert>[] = [
    {
      id: "severity",
      header: "Severidade",
      accessor: "severity",
      cell: (row) => <AlertSeverityBadge severity={row.severity} />,
    },
    { id: "kind", header: "Tipo", accessor: (row) => alertKindLabel(row.kind) },
    {
      id: "message",
      header: "Mensagem",
      accessor: "message",
      cell: (row) => (
        <span className={row.read_at === null ? "font-medium" : ""}>{row.message}</span>
      ),
    },
    {
      id: "opened",
      header: "Aberto em",
      accessor: "opened_at",
      cell: (row) => <span className="whitespace-nowrap">{formatDateTime(row.opened_at)}</span>,
    },
    {
      id: "state",
      header: "Situação",
      accessor: (row) => (row.resolved_at === null ? "open" : "resolved"),
      cell: (row) =>
        row.resolved_at === null ? (
          <Badge variant="outline">Em aberto</Badge>
        ) : (
          <span className="whitespace-nowrap text-muted-foreground">
            Resolvido {formatDateTime(row.resolved_at)}
          </span>
        ),
    },
    {
      id: "read",
      header: "Leitura",
      align: "right",
      cell: (row) =>
        row.read_at !== null ? (
          <span className="text-muted-foreground">Lido</span>
        ) : (
          <Button
            size="sm"
            variant="outline"
            disabled={!canAcknowledge || markRead.isPending}
            title={canAcknowledge ? undefined : WHY_ADMIN_ONLY}
            onClick={() => void acknowledge(row)}
          >
            Marcar como lido
          </Button>
        ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Alertas"
        description="Falhas que pedem atenção: worker parado, bot com erro, candles atrasados e kill switch."
        actions={
          <div className="flex flex-wrap items-center gap-3">
            <UpdatedAt updatedAtMs={query.dataUpdatedAt} failed={query.isError} />
            {canAcknowledge ? (
              <Button
                variant="outline"
                className="gap-1.5"
                disabled={markAll.isPending}
                onClick={() => void acknowledgeAll()}
              >
                <CheckCheck className="size-4" aria-hidden="true" />
                Marcar todos como lidos
              </Button>
            ) : null}
          </div>
        }
      />
      <div className="flex flex-wrap gap-3">
        <FormSelect
          label="Severidade"
          items={SEVERITY_ITEMS}
          value={severity}
          onValueChange={(value) => {
            setSeverity(value);
            setPage(1);
          }}
        />
        <FormSelect
          label="Leitura"
          items={READ_ITEMS}
          value={read}
          onValueChange={(value) => {
            setRead(value);
            setPage(1);
          }}
        />
      </div>
      {query.isError && query.data === undefined ? (
        <ErrorBlock error={query.error} onRetry={() => void query.refetch()} />
      ) : (
        <DataTable
          data={query.data?.data ?? []}
          columns={columns}
          getRowId={(row) => String(row.id)}
          rowLabel={(row) => alertKindLabel(row.kind)}
          caption="Alertas, mais recentes primeiro"
          loading={query.isPending}
          refreshing={query.isFetching && !query.isPending}
          page={page}
          pageSize={PAGE_SIZE}
          total={query.data?.total ?? 0}
          onPageChange={setPage}
          empty={
            filtered ? (
              <Empty title="Nenhum resultado" description="Nenhum alerta com esses filtros." />
            ) : (
              <Empty title="Nenhum alerta" description="Nada deu errado até agora." />
            )
          }
        />
      )}
    </div>
  );
}
