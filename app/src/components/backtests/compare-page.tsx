import { PageHeader } from "lost-ui/app/page-header";
import { LineChart } from "lost-ui/charts/line-chart";
import { DataTable, type DataTableColumn } from "lost-ui/data/data-table";
import { EmptyState as Empty } from "@/components/shared/feedback/empty-state";
import { Alert, AlertDescription, AlertTitle } from "lost-ui/ui/alert";
import { Card, CardContent, CardHeader } from "lost-ui/ui/card";
import { IconCardTitle as CardTitle } from "@/components/shared/metrics/icon-card-title";
import { QueryBoundary } from "@/components/shared/feedback/query-boundary";
import { SignedValue } from "@/components/shared/status/signed-value";
import { useCompareEquity, useComparison } from "@/hooks/backtests/use-backtests";
import type { Backtest } from "@/lib/backtests/backtests.api";
import { compareChartRows } from "@/lib/shared/equity-chart-rows";
import {
  compareDecimal,
  formatDuration,
  formatPercent,
  formatRatio,
  formatSignedPercent,
} from "@/lib/shared/format";

const MAX = 4;

const label = (run: Backtest, index: number): string =>
  `${index + 1}. ${run.strategy_type} ${Object.entries(run.strategy_params)
    .map(([name, value]) => `${name}=${String(value)}`)
    .join(" ")}`;

export function ComparePage({ ids }: { ids: string[] }) {
  const selected = ids.slice(0, MAX);
  const comparison = useComparison(selected);
  const curves = useCompareEquity(selected);

  if (selected.length < 2) {
    return (
      <Empty
        title="Escolha de 2 a 4 backtests"
        description="Marque os backtests na lista e use “Comparar”."
      />
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Comparar backtests"
        description="Curvas de capital e métricas lado a lado. Resultados históricos e simulados."
      />
      <QueryBoundary query={comparison}>
        {(runs) => {
          const series = runs.map((run, index) => ({ key: run.id, label: label(run, index) }));
          const loaded = curves.every((curve) => curve.data !== undefined);
          const rows = loaded
            ? compareChartRows(
                runs.map((run, index) => ({ id: run.id, points: curves[index]?.data ?? [] })),
              )
            : [];
          const columns: DataTableColumn<Backtest>[] = [
            { id: "name", header: "Backtest", cell: (row) => label(row, runs.indexOf(row)) },
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
              id: "test",
              header: "Retorno (teste)",
              align: "right",
              cell: (row) => formatSignedPercent(row.segments?.test.total_return_pct),
            },
            {
              id: "bh",
              header: "Comprar e segurar",
              align: "right",
              cell: (row) => formatSignedPercent(row.metrics?.buy_and_hold_return_pct),
            },
            {
              id: "sharpe",
              header: "Sharpe",
              align: "right",
              sortable: true,
              accessor: (row) => row.metrics?.sharpe_ratio ?? null,
              compare: (a, b) =>
                compareDecimal(a.metrics?.sharpe_ratio ?? null, b.metrics?.sharpe_ratio ?? null),
              cell: (row) => formatRatio(row.metrics?.sharpe_ratio),
            },
            {
              id: "dd",
              header: "Drawdown",
              align: "right",
              cell: (row) => formatPercent(row.metrics?.max_drawdown_pct),
            },
            {
              id: "dd-time",
              header: "Tempo abaixo do pico",
              align: "right",
              cell: (row) => formatDuration(row.metrics?.max_drawdown_duration_seconds),
            },
            {
              id: "wr",
              header: "Taxa de acerto",
              align: "right",
              cell: (row) => formatPercent(row.metrics?.win_rate_pct),
            },
            {
              id: "trips",
              header: "Operações",
              align: "right",
              accessor: (row) => row.metrics?.round_trips ?? 0,
            },
          ];
          const symbols = new Set(runs.map((run) => run.symbol));
          return (
            <div className="space-y-6">
              {symbols.size > 1 ? (
                <Alert className="border-warning/40">
                  <AlertTitle>Pares diferentes</AlertTitle>
                  <AlertDescription>
                    Os pares foram escolhidos hoje; pares deslistados não entram na comparação, o
                    que tende a favorecer o resultado (viés de sobrevivência).
                  </AlertDescription>
                </Alert>
              ) : null}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Curvas de capital</CardTitle>
                </CardHeader>
                <CardContent>
                  {rows.length < 2 ? (
                    <Empty title="Carregando as curvas…" loading />
                  ) : (
                    <LineChart
                      data={rows}
                      xKey="label"
                      series={series}
                      showLegend
                      className="h-72 w-full"
                    />
                  )}
                </CardContent>
              </Card>
              <DataTable
                data={runs}
                columns={columns}
                getRowId={(row) => row.id}
                rowLabel={(row) => row.strategy_type}
                caption="Métricas dos backtests comparados"
              />
            </div>
          );
        }}
      </QueryBoundary>
    </div>
  );
}
