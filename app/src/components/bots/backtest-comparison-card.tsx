import { Link } from "@tanstack/react-router";
import { Button } from "lost-ui/ui/button";
import { Card, CardContent, CardDescription, CardHeader } from "lost-ui/ui/card";
import { IconCardTitle as CardTitle } from "@/components/shared/metrics/icon-card-title";
import { ErrorBlock, SkeletonBlock } from "@/components/shared/feedback/query-boundary";
import { StatTile } from "@/components/shared/metrics/stat-tile";
import { useBacktestComparison } from "@/hooks/bots/use-bots";
import { verdictText } from "@/lib/bots/backtest-comparison";
import type { Bot } from "@/lib/bots/bots.api";
import { backtestPrefillFromBot } from "@/lib/bots/execution";
import { formatDateTime } from "@/lib/shared/dates";
import { formatInteger, formatRatio } from "@/lib/shared/format";
import { AppRoute } from "@/lib/shared/routes";

export function BacktestComparisonCard({ bot }: { bot: Bot }) {
  const query = useBacktestComparison(bot.id);
  if (query.isError && query.data === undefined) {
    return <ErrorBlock error={query.error} onRetry={() => void query.refetch()} />;
  }
  if (query.data === undefined) return <SkeletonBlock rows={1} />;
  const comparison = query.data;
  const periods = comparison.realized?.return_periods ?? null;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Sharpe real × backtest</CardTitle>
        <CardDescription>
          {comparison.run_id === null
            ? "Compara o Sharpe do bot com o do backtest da mesma configuração."
            : `Backtest de ${formatDateTime(comparison.run_created_at ?? "")} com a configuração deste bot.`}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid gap-3 sm:grid-cols-3">
          <StatTile
            label="Sharpe real (anual.)"
            value={formatRatio(comparison.realized?.sharpe)}
            hint={
              periods === null
                ? "Sem retornos ainda."
                : `${formatInteger(periods)} retornos; abaixo de ${formatInteger(comparison.min_periods)} não é calculado.`
            }
          />
          <StatTile
            label="Sharpe do backtest"
            value={formatRatio(comparison.backtest?.sharpe)}
            hint="Mesma fórmula, mesmos 365 dias."
          />
          <StatTile
            label="Razão real ÷ backtest"
            value={formatRatio(comparison.ratio)}
            hint="Observação de Chan: metade ou mais costuma bastar."
          />
        </div>
        <p className="text-sm text-muted-foreground">{verdictText(comparison)}</p>
        {comparison.run_id === null ? (
          <Button variant="outline" asChild>
            <Link to={AppRoute.BacktestsNew} search={backtestPrefillFromBot(bot)}>
              Rodar backtest com esta configuração
            </Link>
          </Button>
        ) : null}
      </CardContent>
    </Card>
  );
}
