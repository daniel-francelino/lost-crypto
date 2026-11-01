import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "lost-ui/ui/card";
import { Empty } from "lost-ui/data/empty";
import { QueryBoundary } from "@/components/shared/feedback/query-boundary";
import { getHalfLife } from "@/lib/market-data/market-data.api";
import { QueryKey } from "@/lib/shared/api/query-keys";
import { formatDecimalDuration, formatInteger, formatRatio } from "@/lib/shared/format";

type Props = {
  exchange: string;
  symbol: string;
  timeframe: string;
  start: string;
  end: string;
};

export function HalfLifeCard({ exchange, symbol, timeframe, start, end }: Props) {
  const params = {
    exchange,
    symbol,
    timeframe,
    start: `${start}T00:00:00Z`,
    end: `${end}T23:59:59Z`,
  };
  const query = useQuery({
    queryKey: QueryKey.MarketData.halfLife(exchange, symbol, timeframe, start, end),
    queryFn: ({ signal }) => getHalfLife(params, signal),
    enabled: start < end,
  });
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Meia-vida estimada</CardTitle>
        <CardDescription>
          Ferramenta descritiva de reversão à média; não é previsão de preço.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <QueryBoundary query={query}>
          {(estimate) =>
            estimate.half_life_bars === null ? (
              <Empty
                title="Sem reversão à média detectável"
                description="Preços de cripto raramente são estacionários; são necessários pelo menos 100 candles e uma tendência de reversão estimável."
              />
            ) : (
              <div className="space-y-3 text-sm">
                <dl className="grid gap-2 sm:grid-cols-2">
                  <div>
                    <dt className="text-muted-foreground">Meia-vida</dt>
                    <dd>
                      ≈ {formatRatio(estimate.half_life_bars)} barras (≈{" "}
                      {formatDecimalDuration(estimate.half_life_seconds)})
                    </dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Teste indicativo a 5%</dt>
                    <dd>
                      {estimate.stationary_at_5pct
                        ? "compatível com estacionariedade"
                        : "sem evidência suficiente de estacionariedade"}
                      {estimate.t_stat === null ? "" : ` · t = ${formatRatio(estimate.t_stat)}`}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Candles / lacunas</dt>
                    <dd>
                      {formatInteger(estimate.n)} / {formatInteger(estimate.gaps)}
                    </dd>
                  </div>
                </dl>
                <p className="text-muted-foreground">{estimate.warning}</p>
              </div>
            )
          }
        </QueryBoundary>
      </CardContent>
    </Card>
  );
}
