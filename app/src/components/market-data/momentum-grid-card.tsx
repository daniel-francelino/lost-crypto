import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "lost-ui/ui/card";
import { QueryBoundary } from "@/components/shared/feedback/query-boundary";
import { getMomentumGrid } from "@/lib/market-data/market-data.api";
import {
  DEFAULT_LAGS,
  cellAt,
  cellText,
  gridError,
  holdingsOf,
  lookbacksOf,
  parseLags,
} from "@/lib/market-data/momentum-grid";
import { QueryKey } from "@/lib/shared/api/query-keys";
import { formatInteger, formatRatio } from "@/lib/shared/format";

type Props = {
  exchange: string;
  symbol: string;
  timeframe: string;
  start: string;
  end: string;
};

export function MomentumGridCard({ exchange, symbol, timeframe, start, end }: Props) {
  const [lookbackText, setLookbackText] = useState(DEFAULT_LAGS);
  const [holdingText, setHoldingText] = useState(DEFAULT_LAGS);
  const lookbacks = parseLags(lookbackText);
  const holdings = parseLags(holdingText);
  const error = gridError(lookbacks, holdings);
  const query = useQuery({
    queryKey: QueryKey.MarketData.momentumGrid(
      exchange,
      symbol,
      timeframe,
      start,
      end,
      lookbacks.values.join(","),
      holdings.values.join(","),
    ),
    queryFn: ({ signal }) =>
      getMomentumGrid(
        {
          exchange,
          symbol,
          timeframe,
          start: `${start}T00:00:00Z`,
          end: `${end}T23:59:59Z`,
          lookbacks: lookbacks.values.join(","),
          holdings: holdings.values.join(","),
        },
        signal,
      ),
    enabled: start < end && error === null,
  });
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Correlação defasada (momentum)</CardTitle>
        <CardDescription>
          Retorno dos últimos N candles contra o retorno dos M candles seguintes, com amostras que
          não se sobrepõem. É um mapa de onde pode haver momentum, não um ranking para escolher a
          melhor célula. Correlação não paga custos e não é lucro negociável.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div className="flex flex-wrap gap-4">
          <label className="flex items-center gap-2">
            <span className="text-muted-foreground">Janelas de observação</span>
            <input
              className="h-8 w-32 rounded-md border bg-background px-2"
              aria-label="Janelas de observação, em candles"
              value={lookbackText}
              onChange={(event) => setLookbackText(event.target.value)}
            />
          </label>
          <label className="flex items-center gap-2">
            <span className="text-muted-foreground">Janelas de manutenção</span>
            <input
              className="h-8 w-32 rounded-md border bg-background px-2"
              aria-label="Janelas de manutenção, em candles"
              value={holdingText}
              onChange={(event) => setHoldingText(event.target.value)}
            />
          </label>
        </div>
        {error === null ? null : <p className="text-destructive">{error}</p>}
        {error === null ? (
          <QueryBoundary query={query}>
            {(grid) => (
              <div className="space-y-2">
                <div className="overflow-x-auto">
                  <table className="w-full text-left">
                    <caption className="sr-only">
                      Correlação entre o retorno passado e o seguinte
                    </caption>
                    <thead>
                      <tr className="text-muted-foreground">
                        <th className="py-1 pr-3">Observação ↓ / Manutenção →</th>
                        {holdingsOf(grid).map((holding) => (
                          <th key={holding} className="py-1 pr-3">
                            {holding}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {lookbacksOf(grid).map((lookback) => (
                        <tr key={lookback}>
                          <th className="py-1 pr-3 font-medium">{lookback}</th>
                          {holdingsOf(grid).map((holding) => {
                            const found = cellAt(grid, lookback, holding);
                            return (
                              <td key={holding} className="py-1 pr-3 align-top">
                                {found === undefined ? "—" : cellText(found)}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="text-muted-foreground">
                  Nível corrigido (0,05 ÷ {formatInteger(grid.cells.length)} células) = z crítico{" "}
                  {formatRatio(grid.critical_z)}. {formatInteger(grid.candles)} candles,{" "}
                  {formatInteger(grid.gaps)} lacunas. {grid.warning}
                </p>
              </div>
            )}
          </QueryBoundary>
        ) : null}
      </CardContent>
    </Card>
  );
}
