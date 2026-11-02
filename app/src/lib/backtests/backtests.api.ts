import { z } from "zod";
import { request, requestPaged } from "@/lib/shared/api/client";
import { HttpMethod } from "@/lib/shared/api/http";
import { decimalSchema, lenientEnum, nullableDecimalSchema } from "@/lib/shared/api/schemas";
import { equityPointSchema, metricsSchema, tradeSchema } from "@/lib/shared/analytics";
import {
  BreakEvenStatus,
  CandleProblem,
  FillTiming,
  JobStatus,
  PeriodGranularity,
  RobustnessVerdict,
  SizingBinding,
  SizingScope,
  SlippageModel,
  SweepRankBy,
} from "@/lib/shared/enums";

const segmentsSchema = z.object({
  split_at: z.string(),
  test_fraction: z.string(),
  train: metricsSchema,
  test: metricsSchema,
});

const periodsSchema = z.object({
  granularity: lenientEnum(PeriodGranularity),
  periods: z.array(
    z.object({
      label: z.string(),
      start: z.string(),
      end: z.string(),
      candles: z.number(),
      metrics: metricsSchema,
    }),
  ),
});
export type Periods = z.infer<typeof periodsSchema>;

const costLevelSchema = z.object({
  multiplier: decimalSchema,
  fee_rate: decimalSchema,
  slippage_bps: decimalSchema,
  cost_per_side_bps: decimalSchema,
  net_pnl: decimalSchema,
  total_return_pct: decimalSchema,
  sharpe_ratio: nullableDecimalSchema,
  round_trips: z.number(),
  fees_paid: decimalSchema,
});
export type CostLevel = z.infer<typeof costLevelSchema>;

const costLadderSchema = z.object({
  levels: z.array(costLevelSchema),
  break_even_status: lenientEnum(BreakEvenStatus),
  break_even_multiplier: nullableDecimalSchema,
  break_even_cost_per_side_bps: nullableDecimalSchema,
  note: z.string(),
});
export type CostLadder = z.infer<typeof costLadderSchema>;

const toleranceSchema = z.object({
  max_drawdown_pct: nullableDecimalSchema,
  max_drawdown_days: z.number().nullable(),
  exceeded_depth: z.boolean().nullable(),
  exceeded_duration: z.boolean().nullable(),
});
export type Tolerance = z.infer<typeof toleranceSchema>;

const regimeBandSchema = z.object({
  label: z.string(),
  bars: z.number(),
  share_pct: decimalSchema,
  strategy_return_pct: nullableDecimalSchema,
  asset_return_pct: nullableDecimalSchema,
  in_market_pct: nullableDecimalSchema,
});
const regimeDimensionSchema = z.object({
  cut_low: nullableDecimalSchema,
  cut_high: nullableDecimalSchema,
  bands: z.array(regimeBandSchema),
});
const regimeSchema = z.object({
  window: z.number(),
  method: z.string(),
  volatility: regimeDimensionSchema,
  efficiency: regimeDimensionSchema,
});
export type Regime = z.infer<typeof regimeSchema>;

const breakMetricsSchema = z.object({
  breaks: z.array(
    z.object({ id: z.string(), name: z.string(), occurred_at: z.string(), created_at: z.string() }),
  ),
  segments: z.array(
    z.object({
      label: z.string(),
      start: z.string(),
      end: z.string(),
      candles: z.number(),
      metrics: metricsSchema,
    }),
  ),
});
export type BreakMetrics = z.infer<typeof breakMetricsSchema>;

const excursionSchema = z.object({
  trades: z.number(),
  worst_pct: decimalSchema,
  median_pct: decimalSchema,
  p95_pct: decimalSchema,
  worst_trades: z.array(
    z.object({ entry_at: z.string(), exit_at: z.string(), pct: decimalSchema }),
  ),
});
export type Excursion = z.infer<typeof excursionSchema>;

const randomEntriesSchema = z.object({
  available: z.boolean(),
  reason: z.string().nullish(),
  simulations: z.number().nullish(),
  as_good_or_better: z.number().nullish(),
  fraction: nullableDecimalSchema.optional(),
  trades: z.number().nullish(),
  seed: z.number().nullish(),
  observed_log_return: nullableDecimalSchema.optional(),
  overlap_allowed: z.boolean().nullish(),
});
const significanceSchema = z.object({ random_entries: randomEntriesSchema.nullish() });
export type Significance = z.infer<typeof significanceSchema>;

const dataQualitySchema = z.object({
  gaps: z
    .object({
      expected: z.number(),
      present: z.number(),
      missing: z.number(),
      gap_count: z.number(),
      largest_gap_candles: z.number(),
      largest_gap_seconds: z.number(),
      over_limit: z.boolean(),
      allowed: z.boolean(),
      gaps: z.array(z.object({ start: z.string(), end: z.string(), missing: z.number() })),
    })
    .nullish(),
  invalid_candles: z.number().nullish(),
  invalid_samples: z
    .array(z.object({ open_time: z.string(), problems: z.array(lenientEnum(CandleProblem)) }))
    .optional(),
  outlier_sigmas: nullableDecimalSchema.optional(),
  outliers: z.number().nullish(),
  outlier_samples: z
    .array(z.object({ open_time: z.string(), return_pct: decimalSchema, sigmas: decimalSchema }))
    .optional(),
  sample: z
    .object({
      free_parameters: z.number(),
      bars: z.number(),
      round_trips: z.number(),
      min_bars: z.number(),
      min_round_trips: z.number(),
      meets_bar_rule: z.boolean(),
      meets_trade_rule: z.boolean(),
    })
    .nullish(),
});
export type DataQuality = z.infer<typeof dataQualitySchema>;

export const backtestSchema = z.object({
  id: z.string(),
  status: lenientEnum(JobStatus),
  strategy_type: z.string(),
  strategy_params: z.record(z.string(), z.unknown()),
  exchange: z.string(),
  symbol: z.string(),
  timeframe: z.string(),
  start: z.string(),
  end: z.string(),
  initial_capital: z.string(),
  fee_rate: z.string(),
  slippage_bps: z.string(),
  slippage_model: lenientEnum(SlippageModel).optional(),
  slippage_k_range: nullableDecimalSchema.optional(),
  slippage_k_size: nullableDecimalSchema.optional(),
  seed: z.number(),
  test_fraction: z.string().nullable(),
  cost_sensitivity: z.boolean().optional(),
  max_drawdown_tolerance_pct: nullableDecimalSchema.optional(),
  max_drawdown_tolerance_days: z.number().nullish(),
  allow_gaps: z.boolean().optional(),
  fill_timing: lenientEnum(FillTiming).optional(),
  risk: z.record(z.string(), z.unknown()).nullish(),
  risk_report: z
    .object({
      sizing: z.string(),
      paused_at: z.string().nullable(),
      paused_reason: z.string().nullable(),
      refusals: z.record(z.string(), z.number()),
    })
    .nullish(),
  tail_risk: z.record(z.string(), z.unknown()).nullish(),
  regime: regimeSchema.nullish(),
  significance: significanceSchema.nullish(),
  break_metrics: breakMetricsSchema.nullish(),
  excursion: excursionSchema.nullish(),
  prior_runs: z.number().nullish(),
  sweep_id: z.string().nullable(),
  data_hash: z.string().nullable(),
  candles_count: z.number().nullable(),
  metrics: metricsSchema.nullable(),
  segments: segmentsSchema.nullable(),
  periods: periodsSchema.nullish(),
  cost_ladder: costLadderSchema.nullish(),
  tolerance: toleranceSchema.nullish(),
  data_quality: dataQualitySchema.nullish(),
  error: z.string().nullable(),
  created_at: z.string(),
  started_at: z.string().nullable(),
  finished_at: z.string().nullable(),
});
export type Backtest = z.infer<typeof backtestSchema>;

const sweepRunSchema = z.object({
  id: z.string(),
  status: lenientEnum(JobStatus),
  strategy_params: z.record(z.string(), z.unknown()),
  start: z.string().optional(),
  total_return_pct: nullableDecimalSchema,
  train_return_pct: nullableDecimalSchema.optional(),
  test_return_pct: nullableDecimalSchema,
  sharpe_ratio: nullableDecimalSchema.optional(),
  train_sharpe_ratio: nullableDecimalSchema.optional(),
  test_sharpe_ratio: nullableDecimalSchema.optional(),
  max_drawdown_pct: nullableDecimalSchema,
  round_trips: z.number().nullable(),
  buy_and_hold_return_pct: nullableDecimalSchema,
  error: z.string().nullable(),
});
export type SweepRun = z.infer<typeof sweepRunSchema>;

const sweepSchema = z.object({
  id: z.string(),
  created_at: z.string(),
  strategy_type: z.string(),
  grid: z.record(z.string(), z.unknown()),
  run_count: z.number(),
  completed: z.number(),
  failed: z.number(),
  skipped: z.array(z.record(z.string(), z.unknown())),
  trials: z.number().optional(),
  prior_trials: z.number().optional(),
  ranked_by: lenientEnum(SweepRankBy),
  robustness: z
    .object({
      verdict: lenientEnum(RobustnessVerdict),
      metric: lenientEnum(SweepRankBy),
      winner_score: nullableDecimalSchema,
      neighbours: z.number(),
      neighbour_mean: nullableDecimalSchema,
      neighbour_min: nullableDecimalSchema,
      neighbour_ratio: nullableDecimalSchema,
      profitable_share: nullableDecimalSchema,
      median: nullableDecimalSchema,
      top3_mean: nullableDecimalSchema,
      scored: z.number(),
    })
    .nullish(),
  note: z.string(),
  runs: z.array(sweepRunSchema),
});
export type Sweep = z.infer<typeof sweepSchema>;

export type BacktestInput = {
  exchange: string;
  strategy_type: string;
  strategy_params: Record<string, number>;
  symbol: string;
  timeframe: string;
  start: string;
  end: string;
  initial_capital: string;
  fee_rate: string | null;
  slippage_bps: string;
  slippage_model: string;
  slippage_k_range: string;
  slippage_k_size: string;
  seed: number;
  test_fraction: string | null;
  cost_sensitivity: boolean;
  max_drawdown_tolerance_pct: string | null;
  max_drawdown_tolerance_days: number | null;
  allow_gaps: boolean;
  fill_timing: string;
  risk: RiskInput | null;
};

export type RiskInput = {
  max_position_fraction: string;
  max_order_notional: string | null;
  max_daily_loss_pct: string | null;
  max_drawdown_pct: string | null;
  max_consecutive_losses: number | null;
  max_risk_per_trade_pct: string | null;
  min_liquidation_distance_pct?: string | null;
  require_stop_loss: boolean;
  max_candle_range_pct: string | null;
  max_order_pct_of_volume: string | null;
  max_close_jump_pct: string | null;
  drawdown_action: string;
};

export const listBacktests = (limit: number, offset: number, signal?: AbortSignal) =>
  requestPaged({
    path: "/backtests",
    schema: z.array(backtestSchema),
    query: { limit, offset },
    signal,
  });

export const getBacktest = (id: string, signal?: AbortSignal) =>
  request({ path: `/backtests/${id}`, schema: backtestSchema, signal });

export const sizingSchema = z.object({
  run_id: z.string(),
  scope: lenientEnum(SizingScope),
  tolerable_loss_pct: decimalSchema,
  sample: z.object({ returns: z.number(), gaps: z.number(), min_required: z.number() }),
  kelly: z
    .object({
      full: decimalSchema,
      half: decimalSchema,
      growth_full: decimalSchema,
      growth_half: decimalSchema,
      mean: nullableDecimalSchema,
      variance: nullableDecimalSchema,
    })
    .nullable(),
  tail: z
    .object({
      strategy_worst_loss_pct: nullableDecimalSchema,
      asset_worst_loss_pct: nullableDecimalSchema,
      cap_strategy: nullableDecimalSchema,
      cap_asset: nullableDecimalSchema,
      strategy_at: z.string().nullable(),
      asset_at: z.string().nullable(),
    })
    .nullable(),
  configured_fraction: decimalSchema,
  suggested_max_position_fraction: decimalSchema,
  binding: lenientEnum(SizingBinding),
  above_reference: z.boolean(),
  warnings: z.array(z.string()),
});
export type SizingAdvice = z.infer<typeof sizingSchema>;
export const getSizing = (
  id: string,
  tolerableLossPct: string,
  scope: "day" | "bar",
  signal?: AbortSignal,
) =>
  request({
    path: `/backtests/${id}/sizing`,
    schema: sizingSchema,
    query: { tolerable_loss_pct: tolerableLossPct, scope },
    signal,
  });

export const createBacktest = (body: BacktestInput) =>
  request({ method: HttpMethod.Post, path: "/backtests", schema: backtestSchema, body });

export const createSweep = (body: BacktestInput, grid: Record<string, number[]>) =>
  request({
    method: HttpMethod.Post,
    path: "/backtests/sweeps",
    schema: sweepSchema,
    body: { ...body, grid },
  });

export const getSweep = (id: string, signal?: AbortSignal) =>
  request({ path: `/backtests/sweeps/${id}`, schema: sweepSchema, signal });

export const getTrades = (id: string, signal?: AbortSignal) =>
  request({ path: `/backtests/${id}/trades`, schema: z.array(tradeSchema), signal });

export const getBacktestEquity = (id: string, signal?: AbortSignal) =>
  request({ path: `/backtests/${id}/equity`, schema: z.array(equityPointSchema), signal });

export const compareBacktests = (ids: string[], signal?: AbortSignal) =>
  request({ path: "/backtests/compare", schema: z.array(backtestSchema), query: { ids }, signal });

const exposurePointSchema = z.object({
  fraction: decimalSchema,
  growth: nullableDecimalSchema,
  max_drawdown_pct: decimalSchema,
  bootstrap_p50: nullableDecimalSchema.optional(),
  bootstrap_p95: nullableDecimalSchema.optional(),
});
const exposureCurveSchema = z.object({
  run_id: z.string(),
  points: z.array(exposurePointSchema),
  kelly_full: nullableDecimalSchema,
  kelly_half: nullableDecimalSchema,
  configured_fraction: decimalSchema,
  ruin_fraction: nullableDecimalSchema,
  returns: z.number(),
  gaps: z.number(),
  bootstrap_returns: z.number().nullable(),
  warnings: z.array(z.string()),
});
export type ExposureCurve = z.infer<typeof exposureCurveSchema>;

export const getExposureCurve = (id: string, bootstrap: boolean, signal?: AbortSignal) =>
  request({
    path: `/backtests/${id}/exposure-curve`,
    schema: exposureCurveSchema,
    query: { steps: 20, bootstrap, simulations: 100, seed: 0 },
    signal,
  });
