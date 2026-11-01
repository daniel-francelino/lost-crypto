import { AlertTriangle, Info } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader } from "lost-ui/ui/card";
import { IconCardTitle as CardTitle } from "@/components/shared/metrics/icon-card-title";
import type { Backtest } from "@/lib/backtests/backtests.api";
import { ScreeningLevel, screeningFlags } from "@/lib/backtests/screening";
import type { Metrics } from "@/lib/shared/analytics";

type ScreeningPanelProps = { run: Backtest; metrics: Metrics };

export function ScreeningPanel({ run, metrics }: ScreeningPanelProps) {
  const flags = screeningFlags({ ...run, metrics });
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Triagem rápida</CardTitle>
        <CardDescription>
          Regras práticas de Chan (Quantitative Trading, cap. 2) para descartar ideias cedo. Vêm de
          ações e futuros, não foram calibradas para cripto: são uma peneira, não uma aprovação.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {flags.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Nenhum sinal de alerta nas regras práticas.
          </p>
        ) : (
          <ul className="space-y-2" aria-label="Alertas da triagem">
            {flags.map((flag) => (
              <li key={flag.id} className="flex items-start gap-2 text-sm">
                {flag.level === ScreeningLevel.Warning ? (
                  <AlertTriangle
                    className="mt-0.5 size-4 shrink-0 text-warning"
                    aria-hidden="true"
                  />
                ) : (
                  <Info
                    className="mt-0.5 size-4 shrink-0 text-muted-foreground"
                    aria-hidden="true"
                  />
                )}
                <span>
                  <span className="sr-only">
                    {flag.level === ScreeningLevel.Warning ? "Alerta: " : "Observação: "}
                  </span>
                  {flag.text}
                </span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
