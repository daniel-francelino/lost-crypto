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
  require_stop_loss: boolean;
  max_candle_range_pct: string | null;
  max_order_pct_of_volume: string | null;
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
