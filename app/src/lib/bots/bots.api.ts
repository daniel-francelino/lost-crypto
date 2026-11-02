import { z } from "zod";
import { request, requestPaged } from "@/lib/shared/api/client";
import { HttpMethod } from "@/lib/shared/api/http";
import {
  decimalSchema,
  emptySchema,
  lenientEnum,
  nullableDecimalSchema,
  nullableTimestampSchema,
} from "@/lib/shared/api/schemas";
import { type Metrics, equityPointSchema, metricsSchema } from "@/lib/shared/analytics";
import {
  BotState,
  DivergenceStep,
  ExecutionMode,
  JobStatus,
  OrderStatus,
  ParityClass,
  ParityVerdict,
  StepState,
  Side,
  SignalKind,
  type Timeframe,
} from "@/lib/shared/enums";

const riskSchema = z.object({
  max_position_fraction: decimalSchema,
  max_order_notional: nullableDecimalSchema,
  max_daily_loss_pct: nullableDecimalSchema,
  max_drawdown_pct: nullableDecimalSchema,
  max_consecutive_losses: z.number().nullable(),
  max_risk_per_trade_pct: nullableDecimalSchema,
  require_stop_loss: z.boolean(),
  max_candle_range_pct: nullableDecimalSchema,
  max_order_pct_of_volume: nullableDecimalSchema.optional(),
  max_close_jump_pct: nullableDecimalSchema.optional(),
  drawdown_action: z.string().optional(),
});
export type Risk = z.infer<typeof riskSchema>;

export const botSchema = z.object({
  id: z.string(),
  name: z.string(),
  exchange: z.string(),
  strategy_type: z.string(),
  strategy_params: z.record(z.string(), z.unknown()),
  symbol: z.string(),
  timeframe: z.string(),
  initial_capital: decimalSchema,
  fee_rate: decimalSchema,
  slippage_bps: decimalSchema,
  risk: riskSchema,
  mode: lenientEnum(ExecutionMode),
  connection_id: z.string().nullable(),
  desired_state: lenientEnum(BotState),
  observed_state: lenientEnum(BotState),
  config_version: z.number(),
  live_approved: z.boolean(),
  live_approved_at: nullableTimestampSchema,
  last_heartbeat_at: nullableTimestampSchema,
  last_error: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});
export type Bot = z.infer<typeof botSchema>;

export { type BotOverview, getOverview } from "@/lib/shared/bots/overview.api";

const summarySchema = z.object({
  mode: lenientEnum(ExecutionMode),
  quote_currency: z.string(),
  bots: z.number(),
  running: z.number(),
  open_positions: z.number(),
  initial_capital: decimalSchema,
  equity: decimalSchema,
  realized_pnl: decimalSchema,
  fees_paid: decimalSchema,
  return_pct: decimalSchema,
});
export type PortfolioSummary = z.infer<typeof summarySchema>;

const portfolioSchema = z.object({
  initial_capital: decimalSchema,
  cash: decimalSchema,
  quantity: decimalSchema,
  avg_entry_price: decimalSchema,
  last_price: nullableDecimalSchema,
  equity: decimalSchema,
  unrealized_pnl: decimalSchema,
  realized_pnl: decimalSchema,
  fees_paid: decimalSchema,
  stop_price: nullableDecimalSchema,
  take_profit_price: nullableDecimalSchema,
  reserved_cash: decimalSchema,
  native_stop_active: z.boolean(),
});
export type Portfolio = z.infer<typeof portfolioSchema>;

const orderSchema = z.object({
  id: z.string(),
  client_order_id: z.string(),
  order_type: z.string(),
  exchange_order_id: z.string().nullable(),
  symbol: z.string(),
  side: lenientEnum(Side),
  quantity: decimalSchema,
  status: lenientEnum(OrderStatus),
  filled_quantity: decimalSchema,
  avg_fill_price: nullableDecimalSchema,
  reject_reason: z.string().nullable(),
  bar_time: z.string(),
  created_at: z.string(),
  reference_price: nullableDecimalSchema.optional(),
  submitted_at: z.string().nullish(),
  first_fill_at: z.string().nullish(),
  slippage_bps: nullableDecimalSchema.optional(),
  latency_ms: z.number().nullish(),
});
export type Order = z.infer<typeof orderSchema>;

const signalSchema = z.object({
  bar_time: z.string(),
  side: lenientEnum(Side),
  kind: lenientEnum(SignalKind),
  reason: z.string(),
  decision: z.string(),
  decision_reason: z.string().nullable(),
  created_at: z.string(),
});
export type Signal = z.infer<typeof signalSchema>;

const readinessSchema = z.object({
  ready: z.boolean(),
  checks: z.array(z.object({ name: z.string(), ok: z.boolean(), detail: z.string() })),
});
export type Readiness = z.infer<typeof readinessSchema>;

const approvalSchema = z.object({ confirmation_token: z.string(), expires_at: z.string() });
export type Approval = z.infer<typeof approvalSchema>;

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
  max_close_jump_pct: string | null;
  drawdown_action: string;
};

export type BotInput = {
  name: string;
  exchange: string;
  strategy_type: string;
  strategy_params: Record<string, number>;
  symbol: string;
  timeframe: Timeframe;
  initial_capital: string;
  fee_rate: string | null;
  slippage_bps: string;
  risk: RiskInput;
  mode: string;
  connection_id: string | null;
};

export const listBots = (signal?: AbortSignal) =>
  request({ path: "/bots", schema: z.array(botSchema), signal, query: { limit: 500 } });

export const getSummary = (signal?: AbortSignal) =>
  request({ path: "/bots/summary", schema: z.array(summarySchema), signal });

export const getBot = (id: string, signal?: AbortSignal) =>
  request({ path: `/bots/${id}`, schema: botSchema, signal });

export const createBot = (body: BotInput) =>
  request({ method: HttpMethod.Post, path: "/bots", schema: botSchema, body });

export const updateBot = (id: string, body: Partial<BotInput> & { change_reason?: string }) =>
  request({ method: HttpMethod.Patch, path: `/bots/${id}`, schema: botSchema, body });

const command = (id: string, name: string, body?: unknown) =>
  request({
    method: HttpMethod.Post,
    path: `/bots/${id}/${name}`,
    schema: emptySchema,
    ...(body === undefined ? {} : { body }),
  });

export const startBot = (id: string, confirmationToken: string | null) =>
  command(
    id,
    "start",
    confirmationToken === null ? undefined : { confirmation_token: confirmationToken },
  );

export const pauseBot = (id: string, reason?: string) =>
  command(id, "pause", reason?.trim() ? { reason: reason.trim() } : undefined);

export const stopBot = (id: string, reason?: string) =>
  command(id, "stop", reason?.trim() ? { reason: reason.trim() } : undefined);

export const deleteBot = (id: string, reason?: string) =>
  request({
    method: HttpMethod.Delete,
    path: `/bots/${id}`,
    schema: emptySchema,
    ...(reason?.trim() ? { body: { reason: reason.trim() } } : {}),
  });

export const resetPortfolio = (id: string, reason?: string) =>
  command(id, "reset-portfolio", reason?.trim() ? { reason: reason.trim() } : undefined);

const interventionsSchema = z.object({
  days: z.number(),
  total: z.number(),
  after_drawdown: z.number(),
  drawdown_threshold_pct: decimalSchema,
  by_type: z.record(z.string(), z.number()),
  items: z.array(
    z.object({
      at: z.string(),
      type: z.string(),
      actor: z.string(),
      reason: z.string().nullable(),
      drawdown_pct: nullableDecimalSchema,
    }),
  ),
  system: z.object({ kill_switch_activated: z.number(), kill_switch_released: z.number() }),
});
export type Interventions = z.infer<typeof interventionsSchema>;

export const getInterventions = (id: string, days = 30, signal?: AbortSignal) =>
  request({
    path: `/bots/${id}/interventions`,
    schema: interventionsSchema,
    query: { days },
    signal,
  });

export const getPortfolio = (id: string, signal?: AbortSignal) =>
  request({ path: `/bots/${id}/portfolio`, schema: portfolioSchema, signal });

export const getPerformance = (id: string, signal?: AbortSignal): Promise<Metrics | null> =>
  request({ path: `/bots/${id}/performance`, schema: metricsSchema.nullable(), signal });

export const getBotEquity = (id: string, limit: number, signal?: AbortSignal) =>
  request({
    path: `/bots/${id}/equity`,
    schema: z.array(equityPointSchema),
    query: { limit },
    signal,
  });

export const listOrders = (id: string, limit: number, offset: number, signal?: AbortSignal) =>
  requestPaged({
    path: `/bots/${id}/orders`,
    schema: z.array(orderSchema),
    query: { limit, offset },
    signal,
  });

export const listSignals = (id: string, limit: number, offset: number, signal?: AbortSignal) =>
  requestPaged({
    path: `/bots/${id}/signals`,
    schema: z.array(signalSchema),
    query: { limit, offset },
    signal,
  });

export const getReadiness = (id: string, signal?: AbortSignal) =>
  request({ path: `/bots/${id}/live-readiness`, schema: readinessSchema, signal });

export const promoteToLive = (id: string, connectionId: string) =>
  request({
    method: HttpMethod.Post,
    path: `/bots/${id}/promote-to-live`,
    schema: botSchema,
    body: { connection_id: connectionId },
  });

export const requestApproval = (id: string, confirmName: string) =>
  request({
    method: HttpMethod.Post,
    path: `/bots/${id}/live-approvals`,
    schema: approvalSchema,
    body: { confirm_name: confirmName },
  });

const slippageStatsSchema = z.object({
  mean: nullableDecimalSchema,
  median: nullableDecimalSchema,
  worst: nullableDecimalSchema,
});

const qualityByTypeSchema = z.object({
  orders: z.number(),
  slippage_bps: slippageStatsSchema,
  latency_ms: z.object({ mean: z.number().nullable(), max: z.number().nullable() }),
});

const executionQualitySchema = z.object({
  configured_slippage_bps: decimalSchema,
  by_type: z.record(z.string(), qualityByTypeSchema),
  above_configured: z.boolean(),
});
export type ExecutionQuality = z.infer<typeof executionQualitySchema>;

export const getExecutionQuality = (id: string, signal?: AbortSignal) =>
  request({ path: `/bots/${id}/execution-quality`, schema: executionQualitySchema, signal });

const paritySummarySchema = z.object({
  session_id: z.string(),
  session_mode: z.string(),
  period_start: z.string(),
  period_end: z.string().nullable(),
  candles: z.number(),
  fill_timing: z.string(),
  counts: z.record(z.string(), z.number()),
  verdict: lenientEnum(ParityVerdict),
  differences: z.array(
    z.object({
      bar_time: z.string(),
      side: lenientEnum(Side),
      kind: lenientEnum(ParityClass),
      bot: z.string(),
      replay: z.string(),
    }),
  ),
  bot_return_pct: nullableDecimalSchema,
  replay_return_pct: nullableDecimalSchema,
  simplified_return_pct: nullableDecimalSchema,
  replay_equity: z.array(z.tuple([z.string(), z.string()])),
});
export type ParitySummary = z.infer<typeof paritySummarySchema>;

const paritySchema = z.object({
  id: z.string(),
  status: lenientEnum(JobStatus),
  created_at: z.string(),
  finished_at: nullableTimestampSchema,
  unexplained: z.number().nullable(),
  summary: paritySummarySchema.nullable(),
  error: z.string().nullable(),
});
export type Parity = z.infer<typeof paritySchema>;

export const getParity = (id: string, signal?: AbortSignal) =>
  request({ path: `/bots/${id}/parity`, schema: paritySchema.nullable(), signal });

export const requestParity = (id: string) =>
  request({ method: HttpMethod.Post, path: `/bots/${id}/parity`, schema: paritySchema });

const realizedSharpeSchema = z.object({
  sharpe: nullableDecimalSchema,
  return_periods: z.number().nullable(),
  days: nullableDecimalSchema,
});
const realizedVsBacktestSchema = z.object({
  run_id: z.string().nullable(),
  run_created_at: nullableTimestampSchema,
  realized: realizedSharpeSchema.nullable(),
  backtest: z.object({ sharpe: nullableDecimalSchema }).nullable(),
  ratio: nullableDecimalSchema,
  min_periods: z.number(),
  chan_min_ratio: decimalSchema,
  reason: z.string().nullable(),
});
export type RealizedVsBacktest = z.infer<typeof realizedVsBacktestSchema>;

export const getBacktestComparison = (id: string, runId?: string, signal?: AbortSignal) =>
  request({
    path: `/bots/${id}/backtest-comparison`,
    ...(runId === undefined ? {} : { query: { run_id: runId } }),
    schema: realizedVsBacktestSchema,
    signal,
  });

const stepSchema = z.object({
  key: lenientEnum(DivergenceStep),
  state: lenientEnum(StepState),
  detail: z.string(),
  values: z.record(z.string(), z.union([z.string(), z.number(), z.null()])).optional(),
});
export type DivergenceStepResult = z.infer<typeof stepSchema>;

export const getDivergence = (id: string, signal?: AbortSignal) =>
  request({ path: `/bots/${id}/divergence`, schema: z.array(stepSchema), signal });
