import { SignedValue } from "@/components/shared/status/signed-value";
import { StatTile } from "@/components/shared/metrics/stat-tile";
import type { Metrics } from "@/lib/shared/analytics";
import { formatUtcShort } from "@/lib/shared/dates";
import {
  formatDuration,
  formatInteger,
  formatMoney,
  formatPercent,
  formatRatio,
  formatSignedMoney,
  formatSignedPercent,
} from "@/lib/shared/format";

type MetricsGridProps = { metrics: Metrics; quote: string };

const NOT_AVAILABLE = "n/d (resultado antigo)";

const sampleHint = (metrics: Metrics): string => {
  if (metrics.return_periods === null || metrics.return_periods === undefined) {
    return NOT_AVAILABLE;
  }
  const exposure =
    metrics.exposure_pct === null || metrics.exposure_pct === undefined
      ? ""
      : ` · posicionado ${formatPercent(metrics.exposure_pct)} do tempo`;
  return `${formatInteger(metrics.return_periods)} retornos${exposure}`;
};

const drawdownHint = (metrics: Metrics): string => {
  const seconds = metrics.max_drawdown_duration_seconds;
  if (seconds === null || seconds === undefined) return NOT_AVAILABLE;
  if (seconds === 0) return "Nunca ficou abaixo do pico.";
  const peak = metrics.max_drawdown_peak_at ?? null;
  const trough = metrics.max_drawdown_trough_at ?? null;
  const when =
    peak === null || trough === null
      ? ""
      : ` · queda mais funda de ${formatUtcShort(peak)} a ${formatUtcShort(trough)} UTC`;
  return `Maior tempo abaixo do pico: ${formatDuration(seconds)}${when}`;
};

function DrawdownValue({ metrics }: { metrics: Metrics }) {
  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      {formatPercent(metrics.max_drawdown_pct)}
      {metrics.drawdown_open === true ? (
        <span className="rounded-md border border-warning/50 px-2 py-0.5 text-xs font-medium">
          em aberto: {formatPercent(metrics.current_drawdown_pct)}
        </span>
      ) : null}
    </span>
  );
}

export function MetricsGrid({ metrics, quote }: MetricsGridProps) {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
      <StatTile label="Capital final" value={formatMoney(metrics.final_equity, quote)} />
      <StatTile
        label="Resultado líquido"
        value={
          <SignedValue raw={metrics.net_pnl} text={formatSignedMoney(metrics.net_pnl, quote)} />
        }
      />
      <StatTile
        label="Retorno"
        value={
          <SignedValue
            raw={metrics.total_return_pct}
            text={formatSignedPercent(metrics.total_return_pct)}
          />
        }
        hint={`Comprar e segurar: ${formatSignedPercent(metrics.buy_and_hold_return_pct)}`}
      />
      <StatTile
        label="Retorno anualizado"
        value={formatSignedPercent(metrics.annualized_return_pct)}
        hint="Composto; não calculado para menos de 30 dias."
      />
      <StatTile
        label="Sharpe (anual.)"
        value={formatRatio(metrics.sharpe_ratio)}
        hint={sampleHint(metrics)}
      />
      <StatTile
        label="Sortino (anual.)"
        value={formatRatio(metrics.sortino_ratio)}
        hint="Só penaliza a volatilidade das perdas."
      />
      <StatTile
        label="Volatilidade anual"
        value={formatPercent(metrics.annualized_volatility_pct)}
        hint="Anualizada com 365 dias: cripto negocia todo dia."
      />
      <StatTile
        label="Information ratio"
        value={formatRatio(metrics.information_ratio)}
        hint="Contra comprar e segurar o mesmo par."
      />
      <StatTile
        label="Drawdown máximo"
        value={<DrawdownValue metrics={metrics} />}
        hint={drawdownHint(metrics)}
      />
      <StatTile label="Taxas pagas" value={formatMoney(metrics.fees_paid, quote)} />
      <StatTile
        label="Operações completas"
        value={formatInteger(metrics.round_trips)}
        hint={`${formatInteger(metrics.fills)} execuções`}
      />
      <StatTile label="Taxa de acerto" value={formatPercent(metrics.win_rate_pct)} />
      <StatTile
        label="Fator de lucro"
        value={metrics.profit_factor ?? "—"}
        hint={`${formatInteger(metrics.rejected_signals)} sinais rejeitados`}
      />
    </div>
  );
}
