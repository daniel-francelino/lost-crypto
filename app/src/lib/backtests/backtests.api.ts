import { z } from "zod";
import { request, requestPaged } from "@/lib/shared/api/client";
import { HttpMethod } from "@/lib/shared/api/http";
import { lenientEnum, nullableDecimalSchema } from "@/lib/shared/api/schemas";
import { equityPointSchema, metricsSchema, tradeSchema } from "@/lib/shared/analytics";
import { JobStatus } from "@/lib/shared/enums";

const segmentsSchema = z.object({
  split_at: z.string(),
  test_fraction: z.string(),
  train: metricsSchema,
  test: metricsSchema,
});

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
  sweep_id: z.string().nullable(),
  data_hash: z.string().nullable(),
  candles_count: z.number().nullable(),
  metrics: metricsSchema.nullable(),
  segments: segmentsSchema.nullable(),
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
  test_return_pct: nullableDecimalSchema,
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
  ranked_by: z.string(),
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
