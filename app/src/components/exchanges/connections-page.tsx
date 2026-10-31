import { useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { Plus } from "lucide-react";
import { useState } from "react";
import { PageHeader } from "lost-ui/app/page-header";
import { DataTable, type DataTableColumn } from "lost-ui/data/data-table";
import { Empty } from "lost-ui/data/empty";
import { Badge } from "lost-ui/ui/badge";
import { Button } from "lost-ui/ui/button";
import { toast } from "lost-ui/ui/sonner";
import { ConfirmDialog } from "@/components/shared/feedback/confirm-dialog";
import { ErrorBlock } from "@/components/shared/feedback/query-boundary";
import { ConnectionStatusBadge, ModeBadge } from "@/components/shared/status/badges";
import { useConnections } from "@/hooks/shared/use-catalog";
import { useSessionUser } from "@/hooks/shared/use-session";
import { disableConnection } from "@/lib/exchanges/exchanges.api";
import { QueryKey } from "@/lib/shared/api/query-keys";
import { Capability, can } from "@/lib/shared/capability";
import { formatDateTime } from "@/lib/shared/dates";
import { ConnectionStatus } from "@/lib/shared/enums";
import type { Connection } from "@/lib/shared/exchanges/connections.api";
import { CONNECTION_STATUS_HELP } from "@/lib/shared/labels";
import { AppRoute } from "@/lib/shared/routes";

export function ConnectionsPage() {
  const user = useSessionUser();
  const client = useQueryClient();
  const query = useConnections(true);
  const [target, setTarget] = useState<Connection | null>(null);
  const manage = can(user, Capability.ExchangesManage);

  const columns: DataTableColumn<Connection>[] = [
    { id: "label", header: "Nome", accessor: "label", sortable: true },
    { id: "exchange", header: "Exchange", accessor: "exchange" },
    {
      id: "environment",
      header: "Ambiente",
      accessor: "environment",
      cell: (row) => <ModeBadge mode={row.environment} />,
    },
    {
      id: "key",
      header: "Chave",
      accessor: "api_key_hint",
      cell: (row) => <code className="text-xs">{row.api_key_hint}</code>,
    },
    {
      id: "status",
      header: "Situação",
      accessor: "status",
      cell: (row) => <ConnectionStatusBadge status={row.status} />,
    },
    {
      id: "verified",
      header: "Verificada em",
      accessor: "verified_at",
      cell: (row) => formatDateTime(row.verified_at),
    },
    {
      id: "actions",
      header: "",
      cell: (row) =>
        manage && row.status !== ConnectionStatus.Disabled ? (
          <Button size="sm" variant="outline" onClick={() => setTarget(row)}>
            Desativar
          </Button>
        ) : null,
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Conexões"
        description="Chaves de API das exchanges. O segredo nunca é exibido de novo depois de salvo."
        actions={
          manage ? (
            <Button asChild className="gap-1.5">
              <Link to={AppRoute.ExchangesNew}>
                <Plus className="size-4" aria-hidden="true" />
                Nova conexão
              </Link>
            </Button>
          ) : undefined
        }
      />
      {query.isError && query.data === undefined ? (
        <ErrorBlock error={query.error} onRetry={() => void query.refetch()} />
      ) : (
        <DataTable
          data={query.data ?? []}
          columns={columns}
          getRowId={(row) => row.id}
          rowLabel={(row) => row.label}
          caption="Conexões com exchanges"
          loading={query.isPending}
          renderExpanded={(row) => (
            <p className="text-sm text-muted-foreground">{CONNECTION_STATUS_HELP[row.status]}</p>
          )}
          empty={
            <Empty
              title="Nenhuma conexão"
              description="Crie uma conexão testnet para rodar bots na exchange com dinheiro fictício."
            />
          }
        />
      )}
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Badge variant="outline">Dica</Badge>
        Chaves live só ficam ativas se o worker confirmar que são somente de trade, sem saque nem
        transferência, e restritas por IP.
      </div>
      <ConfirmDialog
        open={target !== null}
        onOpenChange={(open) => {
          if (!open) setTarget(null);
        }}
        destructive
        title={`Desativar a conexão ${target?.label ?? ""}?`}
        description="Bots que usam esta conexão deixam de poder operar com ela."
        confirmLabel="Desativar conexão"
        onConfirm={async () => {
          if (target === null) return;
          await disableConnection(target.id);
          await client.invalidateQueries({ queryKey: QueryKey.Exchanges.connections() });
          toast.success("Conexão desativada.");
        }}
      />
    </div>
  );
}
