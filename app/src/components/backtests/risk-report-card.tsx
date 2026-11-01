import { Card, CardContent, CardDescription, CardHeader } from "lost-ui/ui/card";
import { EmptyState } from "@/components/shared/feedback/empty-state";
import { IconCardTitle as CardTitle } from "@/components/shared/metrics/icon-card-title";
import type { Backtest } from "@/lib/backtests/backtests.api";
import { formatUtc } from "@/lib/shared/dates";
import { FillTiming } from "@/lib/shared/enums";
import { formatInteger } from "@/lib/shared/format";

const RISK_SIZING = "risk_limits";

export function RiskReportCard({ run }: { run: Backtest }) {
  const report = run.risk_report;
  if (report === null || report === undefined) return null;
  const likeBot = report.sizing === RISK_SIZING;
  const timing =
    run.fill_timing === FillTiming.SignalClose
      ? "no fechamento do candle do sinal (como os bots)"
      : "na abertura do candle seguinte";
  const refusals = Object.entries(report.refusals).sort(([, a], [, b]) => b - a);
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Como foi dimensionado</CardTitle>
        <CardDescription>
          {likeBot
            ? "Dimensionado como um bot: cada sinal passou pelos limites de risco, com pausas."
            : "Sem limites de risco: cada compra usa todo o caixa."}{" "}
          Sinais executados {timing}.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        {report.paused_at === null ? null : (
          <p className="font-medium text-warning">
            Pausado em {formatUtc(report.paused_at)}: {report.paused_reason}. Daí em diante só os
            stops funcionaram, como num bot pausado.
          </p>
        )}
        {refusals.length === 0 ? (
          <EmptyState
            title="Nenhum sinal recusado"
            description="Todas as entradas passaram pelos limites de risco."
            variant="naked"
            size="sm"
          />
        ) : (
          <ul className="space-y-1" aria-label="Sinais recusados por motivo">
            {refusals.map(([reason, count]) => (
              <li key={reason} className="flex justify-between gap-4">
                <span className="text-muted-foreground">{reason}</span>
                <span className="tabular-nums">{formatInteger(count)}</span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
