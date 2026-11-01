import { useQuery } from "@tanstack/react-query";
import { DataTable, type DataTableColumn } from "lost-ui/data/data-table";
import { Empty } from "lost-ui/data/empty";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "lost-ui/ui/card";
import { ErrorBlock } from "@/components/shared/feedback/query-boundary";
import { SignedValue } from "@/components/shared/status/signed-value";
import { type Outlier, listOutliers } from "@/lib/market-data/market-data.api";
import { QueryKey } from "@/lib/shared/api/query-keys";
import { dayEndUtcIso, dayStartUtcIso, formatUtc } from "@/lib/shared/dates";
import { formatPrice, formatRatio, formatSignedPercent } from "@/lib/shared/format";

const columns: DataTableColumn<Outlier>[] = [
  { id: "time", header: "Candle (UTC)", cell: (row) => formatUtc(row.open_time) },
  {
    id: "return",
    header: "Retorno",
    align: "right",
    cell: (row) => <SignedValue raw={row.return_pct} text={formatSignedPercent(row.return_pct)} />,
  },
  { id: "sigmas", header: "Desvios (σ)", align: "right", cell: (row) => formatRatio(row.sigmas) },
  { id: "close", header: "Fechamento", align: "right", cell: (row) => formatPrice(row.close) },
  {
    id: "reference",
    header: "BTC/USDT no mesmo candle",
    align: "right",
    cell: (row) =>
      row.reference_return_pct === null ? "—" : formatSignedPercent(row.reference_return_pct),
  },
];

type OutliersCardProps = {
  exchange: string;
  symbol: string;
  timeframe: string;
  start: string;
  end: string;
};

export function OutliersCard({ exchange, symbol, timeframe, start, end }: OutliersCardProps) {
  const query = useQuery({
    queryKey: QueryKey.MarketData.outliers(exchange, symbol, timeframe, start, end),
    queryFn: ({ signal }) =>
      listOutliers(
        { exchange, symbol, timeframe, start: dayStartUtcIso(start), end: dayEndUtcIso(end) },
        signal,
      ),
  });
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Movimentos fora do comum</CardTitle>
        <CardDescription>
          Retornos de um candle acima de 4 desvios-padrão no recorte. Podem ser erro de dado ou um
          crash real: se o BTC também se moveu no mesmo candle, provavelmente foi o mercado todo.
          Nada é apagado; confira antes de confiar num backtest que lucra nesses pontos.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {query.isError ? (
          <ErrorBlock error={query.error} onRetry={() => void query.refetch()} />
        ) : (
          <DataTable
            data={query.data ?? []}
            columns={columns}
            getRowId={(row) => row.open_time}
            rowLabel={(row) => formatUtc(row.open_time)}
            caption="Candles com movimento acima de 4σ"
            loading={query.isPending}
            empty={
              <Empty
                title="Nada fora do comum"
                description="Nenhum movimento acima de 4σ neste recorte (ou dados insuficientes)."
              />
            }
          />
        )}
      </CardContent>
    </Card>
  );
}
