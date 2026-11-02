import { CircleDollarSign, ShieldAlert } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader } from "lost-ui/ui/card";
import { IconCardTitle } from "@/components/shared/metrics/icon-card-title";
import type { Backtest } from "@/lib/backtests/backtests.api";
import { formatFractionAsPercent, formatMoney } from "@/lib/shared/format";
import { formatUtc } from "@/lib/shared/dates";

export function PerpetualSummaryCard({ run }: { run: Backtest }) {
  if (run.product !== "linear_perpetual" || run.metrics === null) return null;
  const metrics = run.metrics;
  const quote = run.symbol.split(":").at(-1) ?? "USDT";
  const liquidationTimes = metrics.liquidation_times ?? [];

  return (
    <Card>
      <CardHeader>
        <IconCardTitle className="text-base" icon={CircleDollarSign}>
          Resultado USDⓈ-M Perp
        </IconCardTitle>
        <CardDescription>
          Mark price e funding fazem parte do resultado. A liquidação exibida é simulada; a
          liquidação real depende das regras e taxas da Binance.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <dt className="text-sm text-muted-foreground">Alavancagem / margem</dt>
            <dd className="font-medium">
              {metrics.leverage ?? run.leverage ?? 1}x ·{" "}
              {metrics.margin_mode ?? run.margin_mode ?? "isolada"}
            </dd>
          </div>
          <div>
            <dt className="text-sm text-muted-foreground">Notional máximo</dt>
            <dd className="font-medium">
              {metrics.maximum_notional == null
                ? "—"
                : formatMoney(metrics.maximum_notional, quote)}
            </dd>
          </div>
          <div>
            <dt className="text-sm text-muted-foreground">Funding pago</dt>
            <dd className="font-medium">
              {metrics.funding_paid == null ? "—" : formatMoney(metrics.funding_paid, quote)}
            </dd>
          </div>
          <div>
            <dt className="text-sm text-muted-foreground">Funding recebido</dt>
            <dd className="font-medium">
              {metrics.funding_received == null
                ? "—"
                : formatMoney(metrics.funding_received, quote)}
            </dd>
          </div>
        </dl>
        <div className="flex items-start gap-3 rounded-md border border-warning/50 bg-warning/5 p-3">
          <ShieldAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-warning" />
          <div className="space-y-1 text-sm">
            <p className="font-medium">{metrics.liquidation_count ?? 0} liquidações simuladas</p>
            {liquidationTimes.length === 0 ? (
              <p className="text-muted-foreground">Nenhuma liquidação ocorreu no período.</p>
            ) : (
              <ul className="text-muted-foreground">
                {liquidationTimes.slice(0, 5).map((time) => (
                  <li key={time}>{formatUtc(time)}</li>
                ))}
                {liquidationTimes.length > 5 ? (
                  <li>e mais {liquidationTimes.length - 5} evento(s)</li>
                ) : null}
              </ul>
            )}
            <p className="text-muted-foreground">
              Taxa de liquidação aproximada:{" "}
              {metrics.liquidation_fee_rate == null
                ? "não informada"
                : formatFractionAsPercent(metrics.liquidation_fee_rate)}
              {metrics.liquidation_fee_source === "configured_taker_fee_proxy"
                ? " (proxy baseada na taxa taker configurada)"
                : ""}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
