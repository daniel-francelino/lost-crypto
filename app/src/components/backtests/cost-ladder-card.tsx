import { DataTable, type DataTableColumn } from "lost-ui/data/data-table";
import { Alert, AlertDescription, AlertTitle } from "lost-ui/ui/alert";
import { Badge } from "lost-ui/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "lost-ui/ui/card";
import { SignedValue } from "@/components/shared/status/signed-value";
import type { CostLadder, CostLevel } from "@/lib/backtests/backtests.api";
import { BreakEvenStatus } from "@/lib/shared/enums";
import { compareDecimal, formatRatio, formatSignedPercent } from "@/lib/shared/format";

const FRAGILE_BELOW = "1.5";
const CURRENT = "1";

const columns: DataTableColumn<CostLevel>[] = [
  {
    id: "multiplier",
    header: "Custo",
    cell: (row) => (
      <span className="inline-flex items-center gap-2">
        {formatRatio(row.multiplier)}×
        {compareDecimal(row.multiplier, CURRENT) === 0 ? (
          <Badge variant="secondary" className="text-xs">
            simulado
          </Badge>
        ) : null}
      </span>
    ),
  },
  {
    id: "bps",
    header: "Por lado (bps)",
    align: "right",
    cell: (row) => formatRatio(row.cost_per_side_bps),
  },
  {
    id: "return",
    header: "Retorno",
    align: "right",
    cell: (row) => (
      <SignedValue raw={row.total_return_pct} text={formatSignedPercent(row.total_return_pct)} />
    ),
  },
  { id: "sharpe", header: "Sharpe", align: "right", cell: (row) => formatRatio(row.sharpe_ratio) },
  { id: "trades", header: "Operações", align: "right", accessor: (row) => row.round_trips },
];

const headline = (ladder: CostLadder): string => {
  if (ladder.break_even_status === BreakEvenStatus.NeverProfitable) {
    return "Não dá lucro nem com custo zero.";
  }
  if (ladder.break_even_status === BreakEvenStatus.AboveMax) {
    return "Continua lucrativa mesmo com o triplo dos custos simulados.";
  }
  return `Deixa de dar lucro com custos ~${formatRatio(ladder.break_even_multiplier)}× os simulados (≈ ${formatRatio(ladder.break_even_cost_per_side_bps)} bps por lado).`;
};

const isFragile = (ladder: CostLadder): boolean =>
  ladder.break_even_status === BreakEvenStatus.NeverProfitable ||
  (ladder.break_even_status === BreakEvenStatus.Found &&
    compareDecimal(ladder.break_even_multiplier, FRAGILE_BELOW) < 0);

export function CostLadderCard({ ladder }: { ladder: CostLadder }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Sensibilidade a custos</CardTitle>
        <CardDescription>
          A mesma simulação com taxa e slippage multiplicados. Vantagens pequenas costumam sumir com
          custos um pouco maiores.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {isFragile(ladder) ? (
          <Alert className="border-warning/40">
            <AlertTitle>Frágil a custos</AlertTitle>
            <AlertDescription>{headline(ladder)}</AlertDescription>
          </Alert>
        ) : (
          <p className="text-lg font-semibold">{headline(ladder)}</p>
        )}
        <div className="min-w-0 overflow-x-auto">
          <DataTable
            data={ladder.levels}
            columns={columns}
            getRowId={(row) => row.multiplier}
            rowLabel={(row) => `${row.multiplier}x`}
            caption="Resultado por nível de custo"
          />
        </div>
        <p className="text-xs text-muted-foreground">
          Muda só taxa e slippage; impacto de mercado e ordens limitadas não executadas não são
          simulados.
        </p>
      </CardContent>
    </Card>
  );
}
