import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader } from "lost-ui/ui/card";
import { IconCardTitle as CardTitle } from "@/components/shared/metrics/icon-card-title";
import { Empty } from "lost-ui/data/empty";
import { QueryBoundary } from "@/components/shared/feedback/query-boundary";
import { getHalfLife } from "@/lib/shared/market-data/half-life.api";
import {
  hurstText,
  sampleEveryValue,
  varianceRatioText,
} from "@/lib/market-data/series-diagnostics";
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
  const [step, setStep] = useState("1");
  const sampleEvery = sampleEveryValue(step);
  const params = {
    exchange,
    symbol,
    timeframe,
    start: `${start}T00:00:00Z`,
    end: `${end}T23:59:59Z`,
    sample_every: sampleEvery,
  };
  const query = useQuery({
    queryKey: QueryKey.MarketData.halfLife(exchange, symbol, timeframe, start, end, sampleEvery),
    queryFn: ({ signal }) => getHalfLife(params, signal),
    enabled: start < end,
  });
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">
          Reversão à média: meia-vida, Hurst e razão de variâncias
        </CardTitle>
        <CardDescription>
          Ferramentas descritivas; não são previsão de preço. Um resultado favorável não garante
          lucro.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <label className="flex flex-wrap items-center gap-2 text-sm">
          <span className="text-muted-foreground">Amostrar a cada</span>
          <input
            className="h-8 w-20 rounded-md border bg-background px-2"
            inputMode="numeric"
            value={step}
            onChange={(event) => setStep(event.target.value)}
            aria-label="Amostrar a cada N candles"
          />
          <span className="text-muted-foreground">
            candles (candles curtos sobrepostos não são observações independentes)
          </span>
        </label>
        <QueryBoundary query={query}>
          {(estimate) => (
            <div className="space-y-3 text-sm">
              <dl className="grid gap-2 sm:grid-cols-2">
                <div>
                  <dt className="text-muted-foreground">Meia-vida</dt>
                  <dd>
                    {estimate.half_life_bars === null ? (
                      "sem reversão à média detectável"
                    ) : (
                      <>
                        ≈ {formatRatio(estimate.half_life_bars)} barras (≈{" "}
                        {formatDecimalDuration(estimate.half_life_seconds)})
                      </>
                    )}
                  </dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Teste indicativo a 5%</dt>
                  <dd>
                    {estimate.stationary_at_5pct === null
                      ? "sem estimativa"
                      : estimate.stationary_at_5pct
                        ? "compatível com estacionariedade"
                        : "sem evidência suficiente de estacionariedade"}
                    {estimate.t_stat === null ? "" : ` · t = ${formatRatio(estimate.t_stat)}`}
                  </dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Expoente de Hurst</dt>
                  <dd>{hurstText(estimate.hurst)}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Razão de variâncias</dt>
                  <dd>
                    {(estimate.variance_ratios ?? []).length === 0 ? (
                      "sem estimativa"
                    ) : (
                      <ul>
                        {(estimate.variance_ratios ?? []).map((item) => (
                          <li key={item.lag}>{varianceRatioText(item.ratio, item.lag)}</li>
                        ))}
                      </ul>
                    )}
                  </dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Observações / lacunas</dt>
                  <dd>
                    {formatInteger(estimate.n)} / {formatInteger(estimate.gaps)}
                  </dd>
                </div>
              </dl>
              {estimate.half_life_bars === null && estimate.hurst === null ? (
                <Empty
                  title="Sem estimativa"
                  description="Preços de cripto raramente são estacionários; são necessários pelo menos 100 observações."
                />
              ) : null}
              <p className="text-muted-foreground">{estimate.warning}</p>
              <p className="text-muted-foreground">
                A razão de variâncias assume volatilidade constante, o que cripto não tem; leia como
                indício.
              </p>
            </div>
          )}
        </QueryBoundary>
      </CardContent>
    </Card>
  );
}
