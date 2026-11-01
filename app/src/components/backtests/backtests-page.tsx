import { Link, useNavigate } from "@tanstack/react-router";
import { SymbolLabel } from "@/components/shared/market-data/coin-icon";
import { GitCompare, Plus } from "lucide-react";
import { useState } from "react";
import { PageHeader } from "lost-ui/app/page-header";
import { DataTable, type DataTableColumn } from "lost-ui/data/data-table";
import { Empty } from "lost-ui/data/empty";
import { Button } from "lost-ui/ui/button";
import { ErrorBlock } from "@/components/shared/feedback/query-boundary";
import { JobStatusBadge } from "@/components/shared/status/badges";
import { SignedValue } from "@/components/shared/status/signed-value";
import { useBacktests } from "@/hooks/backtests/use-backtests";
import { useSessionUser } from "@/hooks/shared/use-session";
import type { Backtest } from "@/lib/backtests/backtests.api";
import { Capability, can } from "@/lib/shared/capability";
import { formatDateTime, formatUtcDay } from "@/lib/shared/dates";
import { formatPercent, formatSignedPercent } from "@/lib/shared/format";
import { AppRoute } from "@/lib/shared/routes";

const PAGE_SIZE = 25;
const MIN_COMPARE = 2;
const MAX_COMPARE = 4;

const paramsText = (run: Backtest): string =>
  Object.entries(run.strategy_params)
    .map(([name, value]) => `${name}=${String(value)}`)
    .join(", ");

const columns: DataTableColumn<Backtest>[] = [
  {
    id: "status",
    header: "Situação",
    accessor: "status",
    cell: (row) => <JobStatusBadge status={row.status} />,
  },
  {
    id: "strategy",
    header: "Estratégia",
    accessor: "strategy_type",
    cell: (row) => (
      <Link
        to="/backtests/$runId"
        params={{ runId: row.id }}
        className="font-medium underline-offset-4 hover:underline"
      >
        {row.strategy_type}
      </Link>
    ),
  },
  { id: "params", header: "Parâmetros", cell: paramsText },
  {
    id: "symbol",
    header: "Par",
    accessor: "symbol",
    cell: (row) => <SymbolLabel symbol={row.symbol} />,
  },
  { id: "timeframe", header: "Intervalo", accessor: "timeframe" },
  {
    id: "period",
    header: "Período (UTC)",
    cell: (row) => `${formatUtcDay(row.start)} → ${formatUtcDay(row.end)}`,
  },
  {
    id: "return",
    header: "Retorno",
    align: "right",
    cell: (row) => (
      <SignedValue
        raw={row.metrics?.total_return_pct}
        text={formatSignedPercent(row.metrics?.total_return_pct)}
      />
    ),
  },
  {
    id: "drawdown",
    header: "Drawdown",
    align: "right",
    cell: (row) => formatPercent(row.metrics?.max_drawdown_pct),
  },
  {
    id: "created",
    header: "Criado em",
    accessor: "created_at",
    cell: (row) => formatDateTime(row.created_at),
  },
];

export function BacktestsPage() {
  const user = useSessionUser();
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<string[]>([]);
  const query = useBacktests(PAGE_SIZE, (page - 1) * PAGE_SIZE);
  const canCompare = selected.length >= MIN_COMPARE && selected.length <= MAX_COMPARE;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Backtests"
        description="Simulações históricas. Resultados passados não garantem resultado futuro."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              disabled={!canCompare}
              title={`Selecione de ${MIN_COMPARE} a ${MAX_COMPARE} backtests.`}
              className="gap-1.5"
              onClick={() =>
                void navigate({ to: AppRoute.BacktestsCompare, search: { ids: selected } })
              }
            >
              <GitCompare className="size-4" aria-hidden="true" />
              Comparar ({selected.length})
            </Button>
            {can(user, Capability.BacktestsRun) ? (
              <Button asChild className="gap-1.5">
                <Link to={AppRoute.BacktestsNew}>
                  <Plus className="size-4" aria-hidden="true" />
                  Novo backtest
                </Link>
              </Button>
            ) : null}
          </div>
        }
      />
      {query.isError && query.data === undefined ? (
        <ErrorBlock error={query.error} onRetry={() => void query.refetch()} />
      ) : (
        <DataTable
          data={query.data?.data ?? []}
          columns={columns}
          getRowId={(row) => row.id}
          rowLabel={(row) => `${row.strategy_type} ${row.symbol}`}
          caption="Backtests, mais recentes primeiro"
          loading={query.isPending}
          selectable
          selected={selected}
          onSelectedChange={setSelected}
          page={page}
          pageSize={PAGE_SIZE}
          total={query.data?.total ?? 0}
          onPageChange={setPage}
          empty={
            <Empty
              title="Nenhum backtest"
              description="Rode um backtest para ver como uma estratégia teria se comportado."
            />
          }
        />
      )}
    </div>
  );
}
