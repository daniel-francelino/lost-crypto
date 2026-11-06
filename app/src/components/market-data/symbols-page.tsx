import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { PageHeader } from "lost-ui/app/page-header";
import { DataTable, type DataTableColumn } from "lost-ui/data/data-table";
import { Alert, AlertDescription, AlertTitle } from "lost-ui/ui/alert";
import { Badge } from "lost-ui/ui/badge";
import { Button } from "lost-ui/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "lost-ui/ui/card";
import { toast } from "lost-ui/ui/sonner";
import { SymbolPicker } from "@/components/market-data/symbol-picker";
import { ConfirmDialog } from "@/components/shared/feedback/confirm-dialog";
import { EmptyState as Empty } from "@/components/shared/feedback/empty-state";
import { ErrorBlock } from "@/components/shared/feedback/query-boundary";
import { UpdatedAt } from "@/components/shared/feedback/updated-at";
import { SymbolLabel } from "@/components/shared/market-data/coin-icon";
import { TrendBadge } from "@/components/shared/status/trend-badge";
import { useSessionUser } from "@/hooks/shared/use-session";
import { useRegisteredSymbols, useTrends } from "@/hooks/shared/use-symbol-registry";
import { setRegisteredSymbolActive } from "@/lib/market-data/registry.api";
import { errorMessage } from "@/lib/shared/api/messages";
import { QueryKey } from "@/lib/shared/api/query-keys";
import { Capability, can } from "@/lib/shared/capability";
import { TrendFrame } from "@/lib/shared/enums";
import { exchangeLabel, trendFrameLabel } from "@/lib/shared/labels";
import type { RegisteredSymbol, SymbolTrends } from "@/lib/shared/market-data/registry.api";

const FRAME_ORDER = [TrendFrame.Week, TrendFrame.Day, TrendFrame.FourHours, TrendFrame.Hour];

function TrendCells({ item }: { item: SymbolTrends | undefined }) {
  if (item === undefined || item.readings.length === 0) {
    return <span className="text-muted-foreground">Aguardando o worker</span>;
  }
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1">
      {FRAME_ORDER.map((frame) => {
        const reading = item.readings.find((entry) => entry.frame === frame);
        return (
          <span key={frame} className="flex items-center gap-1.5 text-xs">
            <span className="text-muted-foreground">{trendFrameLabel(frame)}</span>
            {reading === undefined ? (
              <span className="text-muted-foreground">—</span>
            ) : (
              <TrendBadge trend={reading.trend} confirmed={reading.confirmed} />
            )}
          </span>
        );
      })}
    </div>
  );
}

export function SymbolsPage() {
  const user = useSessionUser();
  const client = useQueryClient();
  const symbols = useRegisteredSymbols();
  const trends = useTrends();
  const [target, setTarget] = useState<RegisteredSymbol | null>(null);
  const manage = can(user, Capability.SymbolsManage);
  const trendsById = new Map((trends.data ?? []).map((item) => [item.symbol.id, item]));
  const activate = useMutation({
    mutationFn: (id: string) => setRegisteredSymbolActive(id, true),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: QueryKey.Trends.all() });
      toast.success("Moeda reativada.");
    },
    onError: (failure) => toast(errorMessage(failure)),
  });

  const columns: DataTableColumn<RegisteredSymbol>[] = [
    {
      id: "symbol",
      header: "Moeda",
      accessor: "symbol",
      sortable: true,
      cell: (row) => <SymbolLabel symbol={row.symbol} size={28} />,
    },
    {
      id: "exchange",
      header: "Exchange",
      accessor: "exchange",
      cell: (row) => exchangeLabel(row.exchange),
    },
    {
      id: "trends",
      header: "Tendência",
      cell: (row) => <TrendCells item={trendsById.get(row.id)} />,
    },
    {
      id: "active",
      header: "Situação",
      accessor: "active",
      cell: (row) =>
        row.active ? (
          <Badge variant="outline">Ativa</Badge>
        ) : (
          <Badge variant="secondary">Inativa</Badge>
        ),
    },
    {
      id: "actions",
      header: "",
      cell: (row) =>
        manage ? (
          <div className="flex justify-end">
            {row.active ? (
              <Button size="sm" variant="outline" onClick={() => setTarget(row)}>
                Desativar
              </Button>
            ) : (
              <Button
                size="sm"
                variant="outline"
                disabled={activate.isPending}
                onClick={() => activate.mutate(row.id)}
              >
                Reativar
              </Button>
            )}
          </div>
        ) : null,
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Moedas"
        description="Só as moedas cadastradas aqui podem ser usadas por bots, backtests e importações de candles. A tendência é calculada a cada fechamento de candle."
        actions={<UpdatedAt updatedAtMs={trends.dataUpdatedAt} failed={trends.isError} />}
      />
      {symbols.isError && symbols.data === undefined ? (
        <ErrorBlock error={symbols.error} onRetry={() => void symbols.refetch()} />
      ) : (
        <DataTable
          data={symbols.data ?? []}
          columns={columns}
          getRowId={(row) => row.id}
          rowLabel={(row) => row.symbol}
          caption="Moedas cadastradas"
          loading={symbols.isPending}
          empty={
            <Empty
              title="Nenhuma moeda cadastrada"
              description="Escolha pares da Binance abaixo para liberar bots, backtests e importações."
            />
          }
        />
      )}
      {manage ? (
        <Card>
          <CardHeader>
            <CardTitle>Adicionar da Binance</CardTitle>
            <CardDescription>
              A lista vem direto da exchange. Selecione os pares e confirme.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <SymbolPicker registered={symbols.data ?? []} />
          </CardContent>
        </Card>
      ) : (
        <Alert>
          <AlertTitle>Somente leitura</AlertTitle>
          <AlertDescription>
            Somente administradores cadastram ou desativam moedas.
          </AlertDescription>
        </Alert>
      )}
      <ConfirmDialog
        open={target !== null}
        onOpenChange={(open) => {
          if (!open) setTarget(null);
        }}
        destructive
        title={`Desativar ${target?.symbol ?? ""}?`}
        description="Bots, backtests e importações deixam de poder usar esta moeda, e a tendência para de ser atualizada. Se um bot em execução usa a moeda, pare o bot antes."
        confirmLabel="Desativar moeda"
        onConfirm={async () => {
          if (target === null) return;
          await setRegisteredSymbolActive(target.id, false);
          await client.invalidateQueries({ queryKey: QueryKey.Trends.all() });
          toast.success("Moeda desativada.");
        }}
      />
    </div>
  );
}
