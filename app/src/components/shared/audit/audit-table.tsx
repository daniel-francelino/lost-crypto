import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { DataTable, type DataTableColumn } from "lost-ui/data/data-table";
import { EmptyState as Empty } from "@/components/shared/feedback/empty-state";
import { ErrorBlock } from "@/components/shared/feedback/query-boundary";
import { QueryKey } from "@/lib/shared/api/query-keys";
import { type AuditEvent, listAudit } from "@/lib/shared/audit/audit.api";
import { formatDateTime } from "@/lib/shared/dates";

const PAGE_SIZE = 25;

const columns: DataTableColumn<AuditEvent>[] = [
  {
    id: "time",
    header: "Quando",
    accessor: "occurred_at",
    cell: (row) => <span className="whitespace-nowrap">{formatDateTime(row.occurred_at)}</span>,
  },
  { id: "event", header: "Evento", accessor: "event_type", sortable: true },
  { id: "actor", header: "Autor", accessor: "actor", sortable: true },
  { id: "entity", header: "Entidade", accessor: "entity_type" },
];

const payloadText = (event: AuditEvent): string =>
  Object.keys(event.payload).length === 0
    ? "Sem detalhes."
    : JSON.stringify(event.payload, null, 2);

type AuditTableProps = { botId: string | null; eventType?: string | null };

export function AuditTable({ botId, eventType = null }: AuditTableProps) {
  const [page, setPage] = useState(1);
  const offset = (page - 1) * PAGE_SIZE;
  const query = useQuery({
    queryKey: QueryKey.Audit.list(botId, eventType, PAGE_SIZE, offset),
    queryFn: ({ signal }) => listAudit({ botId, eventType, limit: PAGE_SIZE, offset }, signal),
    placeholderData: keepPreviousData,
  });

  if (query.isError && query.data === undefined) {
    return <ErrorBlock error={query.error} onRetry={() => void query.refetch()} />;
  }

  return (
    <DataTable
      data={query.data?.data ?? []}
      columns={columns}
      getRowId={(row, index) => `${row.occurred_at ?? ""}-${row.entity_id}-${index}`}
      rowLabel={(row) => row.event_type}
      caption="Trilha de auditoria, mais recentes primeiro"
      loading={query.isPending}
      refreshing={query.isFetching && !query.isPending}
      page={page}
      pageSize={PAGE_SIZE}
      total={query.data?.total ?? 0}
      onPageChange={setPage}
      renderExpanded={(row) => (
        <pre className="overflow-x-auto rounded-md bg-muted p-3 text-xs">{payloadText(row)}</pre>
      )}
      empty={<Empty title="Nenhum evento" description="Nada foi registrado ainda." />}
    />
  );
}
