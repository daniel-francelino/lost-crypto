import { SignedValue } from "@/components/shared/status/signed-value";
import { StatTile } from "@/components/shared/metrics/stat-tile";
import type { Metrics } from "@/lib/shared/analytics";
import {
  formatInteger,
  formatPercent,
  formatSignedMoney,
  formatSignedPercent,
  formatMoney,
} from "@/lib/shared/format";

type MetricsGridProps = { metrics: Metrics; quote: string };

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
      <StatTile label="Drawdown máximo" value={formatPercent(metrics.max_drawdown_pct)} />
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
