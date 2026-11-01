import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "lost-ui/ui/card";
import type { Backtest } from "@/lib/backtests/backtests.api";
import { formatUtcDay } from "@/lib/shared/dates";
import { formatInteger, formatPercent } from "@/lib/shared/format";

export function ExcursionCard({ run }: { run: Backtest }) {
  const block = run.excursion;
  if (block === null || block === undefined) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Excursão adversa das operações</CardTitle>
        <CardDescription>
          Quanto cada operação chegou a cair abaixo da entrada antes de terminar. Um stop mais curto
          que isso dispara no ruído que a própria estratégia já teve. Em tendência o stop faz parte
          do sinal; em reversão à média o livro o põe além da pior excursão, só contra cisne negro.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <dl className="grid gap-2 sm:grid-cols-4">
          <div>
            <dt className="text-muted-foreground">Operações</dt>
            <dd>{formatInteger(block.trades)}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Pior</dt>
            <dd>{formatPercent(block.worst_pct)}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">95º percentil</dt>
            <dd>{formatPercent(block.p95_pct)}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Mediana</dt>
            <dd>{formatPercent(block.median_pct)}</dd>
          </div>
        </dl>
        <ul className="space-y-1" aria-label="As piores operações">
          {block.worst_trades.map((trade) => (
            <li key={`${trade.entry_at}-${trade.exit_at}`}>
              {formatUtcDay(trade.entry_at)} a {formatUtcDay(trade.exit_at)}:{" "}
              {formatPercent(trade.pct)}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
