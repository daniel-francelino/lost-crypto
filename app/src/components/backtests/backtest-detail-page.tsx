import { Link } from "@tanstack/react-router";
import { PageHeader } from "lost-ui/app/page-header";
import { DataTable, type DataTableColumn } from "lost-ui/data/data-table";
import { Empty } from "lost-ui/data/empty";
import { Alert, AlertDescription, AlertTitle } from "lost-ui/ui/alert";
import { Button } from "lost-ui/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "lost-ui/ui/card";
import {
  ErrorBlock,
  QueryBoundary,
  SkeletonBlock,
} from "@/components/shared/feedback/query-boundary";
import { EquityChart } from "@/components/shared/metrics/equity-chart";
import { MetricsGrid } from "@/components/shared/metrics/metrics-grid";
import { JobStatusBadge, SideBadge } from "@/components/shared/status/badges";
import { useSessionUser } from "@/hooks/shared/use-session";
import { useBacktest, useBacktestEquity, useTrades } from "@/hooks/backtests/use-backtests";
import type { Trade } from "@/lib/shared/analytics";
import { prefillFromRun } from "@/lib/shared/bot-prefill";
import { Capability, can } from "@/lib/shared/capability";
import { formatDateTime, formatUtc, formatUtcDay } from "@/lib/shared/dates";
import { JobStatus } from "@/lib/shared/enums";
import { formatMoney, formatPrice, formatQuantity, quoteCurrency } from "@/lib/shared/format";
import { AppRoute } from "@/lib/shared/routes";

const HISTORICAL = "Histórico simulado — não garante resultado futuro.";

const tradeColumns = (quote: string): DataTableColumn<Trade>[] => [
  { id: "time", header: "Quando (UTC)", accessor: "time", cell: (row) => formatUtc(row.time) },
  { id: "side", header: "Lado", accessor: "side", cell: (row) => <SideBadge side={row.side} /> },
  { id: "qty", header: "Quantidade", align: "right", cell: (row) => formatQuantity(row.quantity) },
  { id: "price", header: "Preço", align: "right", cell: (row) => formatPrice(row.price) },
  {
    id: "notional",
    header: "Valor",
    align: "right",
    cell: (row) => formatMoney(row.notional, quote),
  },
  { id: "fee", header: "Taxa", align: "right", cell: (row) => formatMoney(row.fee, quote) },
];

export function BacktestDetailPage({ runId }: { runId: string }) {
  const user = useSessionUser();
  const query = useBacktest(runId);
  const run = query.data;
  const completed = run?.status === JobStatus.Completed;
  const equity = useBacktestEquity(runId, completed);
  const trades = useTrades(runId, completed);

  if (query.isError && run === undefined) {
    return <ErrorBlock error={query.error} onRetry={() => void query.refetch()} />;
  }
  if (run === undefined) return <SkeletonBlock rows={5} />;
  const quote = quoteCurrency(run.symbol);

  return (
    <div className="space-y-6">
      <PageHeader
        title={
          <span className="flex flex-wrap items-center gap-2">
            {run.strategy_type}
            <JobStatusBadge status={run.status} />
          </span>
        }
        description={`${run.symbol} · ${run.timeframe} · ${formatUtcDay(run.start)} → ${formatUtcDay(run.end)}`}
        actions={
          completed && can(user, Capability.BotsEdit) ? (
            <Button variant="outline" asChild>
              <Link to={AppRoute.BotsNew} search={prefillFromRun(run)}>
                Criar bot com estes parâmetros
              </Link>
            </Button>
          ) : undefined
        }
      />
      <p className="text-sm text-muted-foreground">{HISTORICAL}</p>
      {run.status === JobStatus.Failed ? (
        <Alert variant="destructive">
          <AlertTitle>O backtest falhou</AlertTitle>
          <AlertDescription>{run.error ?? "Sem detalhes."}</AlertDescription>
        </Alert>
      ) : null}
      {run.status === JobStatus.Queued || run.status === JobStatus.Running ? (
        <Alert>
          <AlertTitle>Em andamento</AlertTitle>
          <AlertDescription>O worker está simulando. Esta tela atualiza sozinha.</AlertDescription>
        </Alert>
      ) : null}
      {run.metrics === null ? null : (
        <section className="space-y-3" aria-label="Métricas">
          <h2 className="text-base font-semibold">Resultado completo</h2>
          <MetricsGrid metrics={run.metrics} quote={quote} />
        </section>
      )}
      {run.segments === null ? null : (
        <section className="space-y-3" aria-label="Treino e teste">
          <h2 className="text-base font-semibold">Treino × teste (fora da amostra)</h2>
          <p className="text-sm text-muted-foreground">
            O corte está em {formatUtc(run.segments.split_at)}. O teste usa os últimos{" "}
            {run.segments.test_fraction} da série e vale tanto quanto o treino.
          </p>
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="space-y-2">
              <h3 className="text-sm font-medium">Treino</h3>
              <MetricsGrid metrics={run.segments.train} quote={quote} />
            </div>
            <div className="space-y-2">
              <h3 className="text-sm font-medium">Teste</h3>
              <MetricsGrid metrics={run.segments.test} quote={quote} />
            </div>
          </div>
        </section>
      )}
      {completed ? (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Curva de capital</CardTitle>
            </CardHeader>
            <CardContent>
              <QueryBoundary query={equity}>
                {(points) => (
                  <EquityChart
                    points={points}
                    summary={`${points.length} pontos da simulação (horários em fuso local).`}
                  />
                )}
              </QueryBoundary>
            </CardContent>
          </Card>
          <section className="space-y-2">
            <h2 className="text-base font-semibold">Operações</h2>
            {trades.isError ? (
              <ErrorBlock error={trades.error} onRetry={() => void trades.refetch()} />
            ) : (
              <DataTable
                data={trades.data ?? []}
                columns={tradeColumns(quote)}
                getRowId={(row, index) => `${row.time}-${index}`}
                rowLabel={(row) => `${row.side} ${row.time}`}
                caption="Execuções da simulação"
                loading={trades.isPending}
                pageSize={25}
                empty={
                  <Empty
                    title="Sem operações"
                    description="A estratégia não operou neste período."
                  />
                }
              />
            )}
          </section>
        </>
      ) : null}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Reprodutibilidade</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
            <dt className="text-muted-foreground">Parâmetros</dt>
            <dd>{JSON.stringify(run.strategy_params)}</dd>
            <dt className="text-muted-foreground">Semente</dt>
            <dd>{run.seed}</dd>
            <dt className="text-muted-foreground">Candles usados</dt>
            <dd>{run.candles_count ?? "—"}</dd>
            <dt className="text-muted-foreground">Hash dos dados</dt>
            <dd className="break-all font-mono text-xs">{run.data_hash ?? "—"}</dd>
            <dt className="text-muted-foreground">Criado em</dt>
            <dd>{formatDateTime(run.created_at)}</dd>
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}
