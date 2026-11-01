import type { Backtest, DataQuality } from "@/lib/backtests/backtests.api";
import type { Metrics } from "@/lib/shared/analytics";
import { toMs } from "@/lib/shared/dates";
import { belowFivePercent } from "@/lib/shared/significance";
import {
  compareDecimal,
  formatFraction,
  formatDuration,
  formatPercent,
  formatRatio,
  formatSignedPercent,
} from "@/lib/shared/format";

export const ScreeningLevel = {
  Warning: "warning",
  Info: "info",
} as const;
export type ScreeningLevel = (typeof ScreeningLevel)[keyof typeof ScreeningLevel];

export type ScreeningFlag = { id: string; level: ScreeningLevel; text: string };

export const CHAN_THRESHOLDS = {
  minSharpe: "1",
  maxDrawdownPct: "10",
  maxDrawdownDays: 120,
  minRoundTripsPerYear: 12,
  minExposurePct: "20",
  minTestFraction: "0.25",
  minTStat: "1.645",
  maxWindowReuse: 10,
} as const;

const DAY_MS = 24 * 3600 * 1000;
const DAY_SECONDS = 24 * 3600;
const YEAR_DAYS = 365;

const below = (value: string | null | undefined, limit: string): boolean =>
  value !== null && value !== undefined && compareDecimal(value, limit) < 0;

const above = (value: string | null | undefined, limit: string): boolean =>
  value !== null && value !== undefined && compareDecimal(value, limit) > 0;

const yearsOf = (run: Pick<Backtest, "start" | "end">): number =>
  Math.max((toMs(run.end) - toMs(run.start)) / DAY_MS / YEAR_DAYS, 1 / YEAR_DAYS);

const significanceFlags = (metrics: Metrics): ScreeningFlag[] =>
  belowFivePercent(metrics.sharpe_t_stat, CHAN_THRESHOLDS.minTStat)
    ? [
        {
          id: "significance",
          level: ScreeningLevel.Warning,
          text: `Estatística t de ${formatRatio(metrics.sharpe_t_stat)}: não se distingue de acaso a 5% (teste gaussiano, otimista para cripto).`,
        },
      ]
    : [];

const sharpeFlags = (metrics: Metrics): ScreeningFlag[] => {
  if (below(metrics.sharpe_ratio, CHAN_THRESHOLDS.minSharpe)) {
    return [
      {
        id: "sharpe",
        level: ScreeningLevel.Warning,
        text: `Sharpe anualizado de ${formatRatio(metrics.sharpe_ratio)}: abaixo de 1 a estratégia não se sustenta sozinha.`,
      },
    ];
  }
  const periods = metrics.return_periods;
  if (metrics.sharpe_ratio === null && periods !== null && periods !== undefined) {
    return [
      {
        id: "sample",
        level: ScreeningLevel.Info,
        text: `Amostra curta (${periods} retornos): o Sharpe não foi calculado.`,
      },
    ];
  }
  return [];
};

const drawdownFlags = (metrics: Metrics): ScreeningFlag[] => {
  const flags: ScreeningFlag[] = [];
  if (above(metrics.max_drawdown_pct, CHAN_THRESHOLDS.maxDrawdownPct)) {
    flags.push({
      id: "drawdown-depth",
      level: ScreeningLevel.Warning,
      text: `Drawdown máximo de ${formatPercent(metrics.max_drawdown_pct)}: acima de 10% um Sharpe alto é improvável.`,
    });
  }
  const seconds = metrics.max_drawdown_duration_seconds;
  if (
    seconds !== null &&
    seconds !== undefined &&
    seconds > CHAN_THRESHOLDS.maxDrawdownDays * DAY_SECONDS
  ) {
    flags.push({
      id: "drawdown-duration",
      level: ScreeningLevel.Warning,
      text: `Ficou ${formatDuration(seconds)} abaixo do pico: mais de ~4 meses é difícil de aguentar.`,
    });
  }
  if (metrics.drawdown_open === true) {
    flags.push({
      id: "drawdown-open",
      level: ScreeningLevel.Info,
      text: `Termina ${formatPercent(metrics.current_drawdown_pct)} abaixo do pico, sem ter se recuperado.`,
    });
  }
  return flags;
};

const activityFlags = (metrics: Metrics, run: Pick<Backtest, "start" | "end">): ScreeningFlag[] => {
  const flags: ScreeningFlag[] = [];
  const perYear = metrics.round_trips / yearsOf(run);
  if (perYear < CHAN_THRESHOLDS.minRoundTripsPerYear) {
    flags.push({
      id: "few-trades",
      level: ScreeningLevel.Info,
      text: `Poucas operações (${metrics.round_trips} no período): com poucas operações por ano o resultado depende de sorte.`,
    });
  }
  if (below(metrics.exposure_pct, CHAN_THRESHOLDS.minExposurePct)) {
    flags.push({
      id: "exposure",
      level: ScreeningLevel.Info,
      text: `Posicionado só ${formatPercent(metrics.exposure_pct)} do tempo: o tempo parado em caixa reduz a volatilidade e embeleza o Sharpe.`,
    });
  }
  if (compareDecimal(metrics.total_return_pct, metrics.buy_and_hold_return_pct) < 0) {
    flags.push({
      id: "benchmark",
      level: ScreeningLevel.Warning,
      text: `Rendeu ${formatSignedPercent(metrics.total_return_pct)}, menos que comprar e segurar (${formatSignedPercent(metrics.buy_and_hold_return_pct)}).`,
    });
  }
  return flags;
};

const segmentFlags = (run: Pick<Backtest, "segments">): ScreeningFlag[] => {
  const segments = run.segments;
  if (segments === null) return [];
  const trainUp = above(segments.train.total_return_pct, "0");
  const testDown = !above(segments.test.total_return_pct, "0");
  if (!(trainUp && testDown)) return [];
  return [
    {
      id: "out-of-sample",
      level: ScreeningLevel.Warning,
      text: `Lucrou no treino (${formatSignedPercent(segments.train.total_return_pct)}) mas não no teste (${formatSignedPercent(segments.test.total_return_pct)}): sinal de ajuste excessivo.`,
    },
  ];
};

const dataFlags = (quality: DataQuality | null | undefined): ScreeningFlag[] => {
  if (quality === null || quality === undefined) return [];
  const flags: ScreeningFlag[] = [];
  const outliers = quality.outliers ?? 0;
  if (outliers > 0) {
    flags.push({
      id: "outliers",
      level: ScreeningLevel.Warning,
      text: `${outliers} movimento(s) fora do comum nos dados: o resultado pode depender de dados errados. Confira em "Qualidade dos dados".`,
    });
  }
  if ((quality.invalid_candles ?? 0) > 0) {
    flags.push({
      id: "invalid-candles",
      level: ScreeningLevel.Warning,
      text: `${quality.invalid_candles ?? 0} candle(s) inválido(s) no período.`,
    });
  }
  if (quality.gaps?.over_limit === true) {
    flags.push({
      id: "gaps",
      level: ScreeningLevel.Warning,
      text: `Rodado com lacunas acima do limite (${quality.gaps.missing} candles faltando): operações que atravessam um buraco são executadas depois dele.`,
    });
  }
  const sample = quality.sample;
  if (sample !== null && sample !== undefined && !sample.meets_bar_rule) {
    flags.push({
      id: "sample-bars",
      level: ScreeningLevel.Warning,
      text: `Amostra pequena para ${sample.free_parameters} parâmetros: ${sample.bars} candles, e a regra prática pede ${sample.min_bars}.`,
    });
  }
  if (sample !== null && sample !== undefined && !sample.meets_trade_rule) {
    flags.push({
      id: "sample-trades",
      level: ScreeningLevel.Info,
      text: `Só ${sample.round_trips} operações independentes (menos de ${sample.min_round_trips}): cada uma pesa muito no resultado.`,
    });
  }
  return flags;
};

const fractionFlags = (fraction: string | null | undefined): ScreeningFlag[] =>
  fraction !== null &&
  fraction !== undefined &&
  compareDecimal(fraction, CHAN_THRESHOLDS.minTestFraction) < 0
    ? [
        {
          id: "small-test",
          level: ScreeningLevel.Info,
          text: `Fração de teste de ${formatFraction(fraction)}: o livro sugere o teste com pelo menos ⅓ do treino (fração ≥ 0.25).`,
        },
      ]
    : [];

const reuseFlags = (
  priorRuns: number | null | undefined,
  segments: Backtest["segments"],
): ScreeningFlag[] =>
  segments !== null &&
  priorRuns !== null &&
  priorRuns !== undefined &&
  priorRuns >= CHAN_THRESHOLDS.maxWindowReuse
    ? [
        {
          id: "reuse",
          level: ScreeningLevel.Warning,
          text: `Esta janela já foi usada em ${priorRuns} outras execuções: a cada olhada o teste deixa de ser fora da amostra.`,
        },
      ]
    : [];

export const screeningFlags = (
  run: Pick<Backtest, "start" | "end" | "segments"> & {
    prior_runs?: number | null | undefined;
    metrics: Metrics;
    data_quality?: DataQuality | null | undefined;
    test_fraction?: string | null | undefined;
  },
): ScreeningFlag[] => {
  const sampleKnown = run.data_quality?.sample !== null && run.data_quality?.sample !== undefined;
  const flags = [
    ...sharpeFlags(run.metrics),
    ...significanceFlags(run.metrics),
    ...drawdownFlags(run.metrics),
    ...activityFlags(run.metrics, run).filter((flag) => !(sampleKnown && flag.id === "few-trades")),
    ...segmentFlags(run),
    ...dataFlags(run.data_quality),
    ...fractionFlags(run.test_fraction),
    ...reuseFlags(run.prior_runs, run.segments),
  ];
  return [
    ...flags.filter((flag) => flag.level === ScreeningLevel.Warning),
    ...flags.filter((flag) => flag.level === ScreeningLevel.Info),
  ];
};
