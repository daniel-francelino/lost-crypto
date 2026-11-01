import { Link } from "@tanstack/react-router";
import { Card, CardContent, CardDescription, CardHeader } from "lost-ui/ui/card";
import { IconCardTitle as CardTitle } from "@/components/shared/metrics/icon-card-title";
import type { Backtest, DataQuality } from "@/lib/backtests/backtests.api";
import { dayString, formatUtc, toMs } from "@/lib/shared/dates";
import {
  formatDuration,
  formatInteger,
  formatRatio,
  formatSignedPercent,
} from "@/lib/shared/format";
import { candleProblemsText } from "@/lib/shared/market-data/quality-labels";
import { AppRoute } from "@/lib/shared/routes";

type Row = { label: string; value: string; warn: boolean };

const gapRow = (quality: DataQuality): Row | null => {
  const gaps = quality.gaps;
  if (gaps === null || gaps === undefined) return null;
  if (gaps.missing === 0) return { label: "Lacunas", value: "nenhuma no período", warn: false };
  return {
    label: "Lacunas",
    value: `${formatInteger(gaps.missing)} de ${formatInteger(gaps.expected)} candles faltando em ${gaps.gap_count} buraco(s); maior: ${formatDuration(gaps.largest_gap_seconds)}${gaps.allowed && gaps.over_limit ? " — rodado com “Rodar mesmo com lacunas”" : ""}`,
    warn: gaps.over_limit,
  };
};

const invalidRow = (quality: DataQuality): Row | null => {
  const count = quality.invalid_candles;
  if (count === null || count === undefined) return null;
  const first = quality.invalid_samples?.[0];
  return {
    label: "Candles inválidos",
    value:
      count === 0
        ? "nenhum"
        : `${formatInteger(count)}${first === undefined ? "" : ` (ex.: ${formatUtc(first.open_time)} — ${candleProblemsText(first.problems)})`}`,
    warn: count > 0,
  };
};

const outlierRow = (quality: DataQuality): Row | null => {
  const count = quality.outliers;
  if (count === null || count === undefined) return null;
  const sigmas = formatRatio(quality.outlier_sigmas);
  const samples = (quality.outlier_samples ?? [])
    .slice(0, 3)
    .map((o) => `${formatUtc(o.open_time)} (${formatSignedPercent(o.return_pct)})`)
    .join("; ");
  return {
    label: `Movimentos acima de ${sigmas}σ`,
    value: count === 0 ? "nenhum" : `${formatInteger(count)}: ${samples}${count > 3 ? "…" : ""}`,
    warn: count > 0,
  };
};

const sampleRow = (quality: DataQuality): Row | null => {
  const sample = quality.sample;
  if (sample === null || sample === undefined) return null;
  return {
    label: "Tamanho da amostra",
    value: `${formatInteger(sample.bars)} candles e ${formatInteger(sample.round_trips)} operações para ${sample.free_parameters} parâmetros livres (regra prática: ≥ ${formatInteger(sample.min_bars)} candles e ≥ ${sample.min_round_trips} operações)`,
    warn: !sample.meets_bar_rule || !sample.meets_trade_rule,
  };
};

export function DataQualityCard({ run, quality }: { run: Backtest; quality: DataQuality }) {
  const rows = [
    gapRow(quality),
    invalidRow(quality),
    outlierRow(quality),
    sampleRow(quality),
  ].filter((row): row is Row => row !== null);
  if (rows.length === 0) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Qualidade dos dados</CardTitle>
        <CardDescription>
          No que este resultado se apoia. Nada foi removido: movimentos fora do comum podem ser
          reais (crashes) ou erros de dado, e merecem uma olhada antes de confiar no número.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <dl className="grid gap-x-4 gap-y-2 text-sm sm:grid-cols-[auto_1fr]">
          {rows.map((row) => (
            <div key={row.label} className="contents">
              <dt className="text-muted-foreground">{row.label}</dt>
              <dd className={row.warn ? "font-medium text-warning" : undefined}>
                {row.warn ? <span className="sr-only">Atenção: </span> : null}
                {row.value}
              </dd>
            </div>
          ))}
        </dl>
        <Link
          to={AppRoute.MarketData}
          search={{
            symbol: run.symbol,
            timeframe: run.timeframe,
            start: dayString(toMs(run.start)),
            end: dayString(toMs(run.end)),
          }}
          className="text-sm font-medium underline-offset-4 hover:underline"
        >
          Revisar estes dados na tela de dados de mercado
        </Link>
      </CardContent>
    </Card>
  );
}
