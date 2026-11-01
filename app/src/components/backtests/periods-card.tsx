import { DataTable, type DataTableColumn } from "lost-ui/data/data-table";
import { Alert, AlertDescription, AlertTitle } from "lost-ui/ui/alert";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "lost-ui/ui/card";
import { SignedValue } from "@/components/shared/status/signed-value";
import type { Periods } from "@/lib/backtests/backtests.api";
import { PeriodGranularity } from "@/lib/shared/enums";
import {
  compareDecimal,
  formatInteger,
  formatPercent,
  formatRatio,
  formatSignedPercent,
} from "@/lib/shared/format";

type PeriodRow = Periods["periods"][number] & { latest: boolean };

const columns: DataTableColumn<PeriodRow>[] = [
  {
    id: "label",
    header: "Período",
    cell: (row) => (
      <span className={row.latest ? "font-semibold" : undefined}>
        {row.label}
        {row.latest ? " (mais recente)" : ""}
      </span>
    ),
  },
  {
    id: "return",
    header: "Retorno",
    align: "right",
    cell: (row) => (
      <SignedValue
        raw={row.metrics.total_return_pct}
        text={formatSignedPercent(row.metrics.total_return_pct)}
      />
    ),
  },
  {
    id: "bh",
    header: "Comprar e segurar",
    align: "right",
    cell: (row) => formatSignedPercent(row.metrics.buy_and_hold_return_pct),
  },
  {
    id: "sharpe",
    header: "Sharpe",
    align: "right",
    cell: (row) => formatRatio(row.metrics.sharpe_ratio),
  },
  {
    id: "drawdown",
    header: "Drawdown",
    align: "right",
    cell: (row) => formatPercent(row.metrics.max_drawdown_pct),
  },
  {
    id: "trades",
    header: "Operações",
    align: "right",
    accessor: (row) => row.metrics.round_trips,
  },
  {
    id: "candles",
    header: "Candles",
    align: "right",
    cell: (row) => formatInteger(row.candles),
  },
];

const recentLoss = (periods: Periods, total: string): boolean => {
  const latest = periods.periods.at(-1);
  return (
    periods.periods.length > 1 &&
    latest !== undefined &&
    compareDecimal(latest.metrics.total_return_pct, "0") < 0 &&
    compareDecimal(total, "0") > 0
  );
};

type PeriodsCardProps = { periods: Periods; totalReturnPct: string };

export function PeriodsCard({ periods, totalReturnPct }: PeriodsCardProps) {
  const rows = periods.periods.map((period, index) => ({
    ...period,
    latest: index === periods.periods.length - 1,
  }));
  const unit = periods.granularity === PeriodGranularity.Quarter ? "trimestre" : "ano";
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Por período</CardTitle>
        <CardDescription>
          O mesmo resultado separado por {unit}. Períodos antigos tendem a parecer melhores: julgue
          pelos mais recentes. Poucos candles por linha dão números instáveis.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {recentLoss(periods, totalReturnPct) ? (
          <Alert className="border-warning/40">
            <AlertTitle>O resultado total vem de períodos antigos</AlertTitle>
            <AlertDescription>
              O período mais recente deu prejuízo, embora o total seja positivo.
            </AlertDescription>
          </Alert>
        ) : null}
        <div className="min-w-0 overflow-x-auto">
          <DataTable
            data={rows}
            columns={columns}
            getRowId={(row) => row.label}
            rowLabel={(row) => row.label}
            caption={`Métricas por ${unit}`}
          />
        </div>
      </CardContent>
    </Card>
  );
}
