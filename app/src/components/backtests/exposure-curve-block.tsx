import { useState } from "react";
import { LineChart } from "lost-ui/charts/line-chart";
import { useExposureCurve } from "@/hooks/backtests/use-backtests";
import type { Backtest } from "@/lib/backtests/backtests.api";
import { exposureRows } from "@/lib/backtests/exposure-chart-rows";
import { JobStatus } from "@/lib/shared/enums";
import {
  formatFractionAsPercent,
  formatInteger,
  formatPercent,
  formatRatio,
} from "@/lib/shared/format";

const GROWTH = [{ key: "growth", label: "Crescimento por barra (%)", color: "var(--primary)" }];
const DRAWDOWN = [
  { key: "drawdown", label: "Drawdown máximo (%)", color: "var(--destructive)" },
  { key: "drawdownP95", label: "Drawdown, bootstrap 95º (%)", color: "var(--warning)" },
];

export function ExposureCurveBlock({ run }: { run: Backtest }) {
  const [bootstrap, setBootstrap] = useState(false);
  const query = useExposureCurve(run.id, bootstrap, run.status === JobStatus.Completed);
  return (
    <section className="space-y-3 border-t pt-4" aria-label="Curva por exposição">
      <h3 className="font-medium">Curva por exposição</h3>
      <p className="text-muted-foreground">
        Crescimento e drawdown se a posição fosse uma fração de 0 a 100% do patrimônio. Kelly é um
        teto a ser descontado, nunca uma recomendação de aumentar a posição: leia a faixa, não um
        ponto ótimo.
      </p>
      <label className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={bootstrap}
          onChange={(event) => setBootstrap(event.target.checked)}
        />
        Incluir bootstrap dos retornos (mais lento; destrói a autocorrelação da série real)
      </label>
      {query.isPending ? <p>Calculando a curva…</p> : null}
      {query.isError ? (
        <p role="alert">Não foi possível calcular a curva. Tente novamente.</p>
      ) : null}
      {query.data ? (
        <div className="space-y-3">
          <p>
            Kelly cheio {formatRatio(query.data.kelly_full)} · meio Kelly{" "}
            {formatRatio(query.data.kelly_half)} · fração configurada{" "}
            {formatFractionAsPercent(query.data.configured_fraction)}
            {query.data.ruin_fraction === null
              ? ""
              : ` · ruína acima de ${formatRatio(query.data.ruin_fraction)}× (uma barra zera a conta)`}{" "}
            · {formatInteger(query.data.returns)} retornos
            {query.data.bootstrap_returns === null
              ? ""
              : `, bootstrap sobre os últimos ${formatInteger(query.data.bootstrap_returns)}`}
          </p>
          <div className="grid gap-4 lg:grid-cols-2">
            <LineChart
              data={exposureRows(query.data)}
              xKey="label"
              series={GROWTH}
              showLegend
              className="h-48 w-full"
            />
            <LineChart
              data={exposureRows(query.data)}
              xKey="label"
              series={bootstrap ? DRAWDOWN : DRAWDOWN.slice(0, 1)}
              showLegend
              className="h-48 w-full"
            />
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <caption className="sr-only">Crescimento e drawdown por exposição</caption>
              <thead>
                <tr className="text-muted-foreground">
                  <th className="py-1 pr-3">Exposição</th>
                  <th className="py-1 pr-3">Crescimento por barra</th>
                  <th className="py-1 pr-3">Drawdown máx.</th>
                  {bootstrap ? <th className="py-1 pr-3">Bootstrap 50º / 95º</th> : null}
                </tr>
              </thead>
              <tbody>
                {query.data.points.map((point) => (
                  <tr key={point.fraction}>
                    <td className="py-1 pr-3">{formatFractionAsPercent(point.fraction)}</td>
                    <td className="py-1 pr-3">
                      {point.growth === null ? "zera a conta" : formatPercent(point.growth)}
                    </td>
                    <td className="py-1 pr-3">{formatPercent(point.max_drawdown_pct)}</td>
                    {bootstrap ? (
                      <td className="py-1 pr-3">
                        {formatPercent(point.bootstrap_p50)} / {formatPercent(point.bootstrap_p95)}
                      </td>
                    ) : null}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
            {query.data.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
