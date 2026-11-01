import { Card, CardContent, CardDescription, CardHeader } from "lost-ui/ui/card";
import { IconCardTitle as CardTitle } from "@/components/shared/metrics/icon-card-title";
import type { Regime } from "@/lib/backtests/backtests.api";
import { formatInteger, formatPercent, formatRatio } from "@/lib/shared/format";

const LABEL: Record<string, string> = { low: "Baixa", medium: "Média", high: "Alta" };

function DimensionTable({
  title,
  dimension,
  featureLabel,
}: {
  title: string;
  dimension: Regime["volatility"];
  featureLabel: string;
}) {
  return (
    <section className="space-y-2">
      <h3 className="text-sm font-semibold">{title}</h3>
      <p className="text-xs text-muted-foreground">
        Limites dos tercis: {formatRatio(dimension.cut_low)} / {formatRatio(dimension.cut_high)}
      </p>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[620px] text-sm">
          <thead>
            <tr className="border-b text-left text-muted-foreground">
              <th className="p-2">{featureLabel}</th>
              <th className="p-2 text-right">Barras</th>
              <th className="p-2 text-right">Fatia</th>
              <th className="p-2 text-right">Estratégia</th>
              <th className="p-2 text-right">Ativo</th>
              <th className="p-2 text-right">No mercado</th>
            </tr>
          </thead>
          <tbody>
            {dimension.bands.map((band) => (
              <tr className="border-b last:border-0" key={band.label}>
                <th className="p-2 text-left font-medium">{LABEL[band.label] ?? band.label}</th>
                <td className="p-2 text-right tabular-nums">{formatInteger(band.bars)}</td>
                <td className="p-2 text-right tabular-nums">{formatPercent(band.share_pct)}</td>
                <td className="p-2 text-right tabular-nums">
                  {formatPercent(band.strategy_return_pct)}
                </td>
                <td className="p-2 text-right tabular-nums">
                  {formatPercent(band.asset_return_pct)}
                </td>
                <td className="p-2 text-right tabular-nums">{formatPercent(band.in_market_pct)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function RegimeCard({ regime }: { regime: Regime }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Resultados por regime</CardTitle>
        <CardDescription>
          Descritivo, não serve para prever o regime. Os limites usam tercis da série inteira; cada
          barra é classificada apenas com dados anteriores.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <DimensionTable
          title="Volatilidade realizada"
          dimension={regime.volatility}
          featureLabel="Volatilidade"
        />
        <DimensionTable
          title="Eficiência da tendência"
          dimension={regime.efficiency}
          featureLabel="Eficiência"
        />
      </CardContent>
    </Card>
  );
}
