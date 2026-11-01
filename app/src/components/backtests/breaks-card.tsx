import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "lost-ui/ui/card";
import type { Backtest } from "@/lib/backtests/backtests.api";
import { formatUtcDay } from "@/lib/shared/dates";
import { formatInteger, formatRatio, formatSignedPercent } from "@/lib/shared/format";
import { registeredAfter } from "@/lib/shared/market-data/regime-breaks";

export function BreaksCard({ run }: { run: Backtest }) {
  const block = run.break_metrics;
  if (block === null || block === undefined) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Resultado entre as quebras de regime</CardTitle>
        <CardDescription>
          Mesma execução, cortada nas quebras que você nomeou. Julgue a estratégia pelo trecho que
          ainda vale, não pela média de regimes diferentes.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <ul className="space-y-1" aria-label="Quebras usadas">
          {block.breaks.map((item) => (
            <li key={item.id}>
              <strong>{item.name}</strong> em {formatUtcDay(item.occurred_at)}
              {registeredAfter(item.created_at, run.created_at)
                ? " · registrada depois desta execução: a data pode ter sido escolhida olhando o resultado"
                : ""}
            </li>
          ))}
        </ul>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <caption className="sr-only">Métricas por trecho entre as quebras</caption>
            <thead>
              <tr className="text-muted-foreground">
                <th className="py-1 pr-3">Trecho</th>
                <th className="py-1 pr-3">Candles</th>
                <th className="py-1 pr-3">Retorno</th>
                <th className="py-1 pr-3">Sharpe</th>
                <th className="py-1 pr-3">Drawdown máx.</th>
              </tr>
            </thead>
            <tbody>
              {block.segments.map((segment) => (
                <tr key={segment.start}>
                  <td className="py-1 pr-3">
                    {segment.label} ({formatUtcDay(segment.start)} a {formatUtcDay(segment.end)})
                  </td>
                  <td className="py-1 pr-3">{formatInteger(segment.candles)}</td>
                  <td className="py-1 pr-3">
                    {formatSignedPercent(segment.metrics.total_return_pct)}
                  </td>
                  <td className="py-1 pr-3">{formatRatio(segment.metrics.sharpe_ratio)}</td>
                  <td className="py-1 pr-3">
                    {formatSignedPercent(segment.metrics.max_drawdown_pct)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
