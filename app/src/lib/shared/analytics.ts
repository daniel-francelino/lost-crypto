import { z } from "zod";
import { decimalSchema, nullableDecimalSchema } from "@/lib/shared/api/schemas";

export const metricsSchema = z.object({
  initial_capital: decimalSchema,
  final_equity: decimalSchema,
  net_pnl: decimalSchema,
  total_return_pct: decimalSchema,
  buy_and_hold_return_pct: decimalSchema,
  max_drawdown_pct: decimalSchema,
  fees_paid: decimalSchema,
  fills: z.number(),
  round_trips: z.number(),
  win_rate_pct: nullableDecimalSchema,
  profit_factor: nullableDecimalSchema,
  avg_trade_pnl: nullableDecimalSchema,
  open_position: z.boolean(),
  rejected_signals: z.number(),
  funding_paid: nullableDecimalSchema.optional(),
  funding_received: nullableDecimalSchema.optional(),
  liquidation_count: z.number().nullish(),
  liquidation_times: z.array(z.string()).nullish(),
  maximum_notional: nullableDecimalSchema.optional(),
  minimum_liquidation_distance_pct: nullableDecimalSchema.optional(),
  leverage: z.number().nullish(),
  margin_mode: z.string().nullish(),
  liquidation_fee_rate: nullableDecimalSchema.optional(),
  liquidation_fee_source: z.string().nullish(),
  sharpe_ratio: nullableDecimalSchema.optional(),
  sortino_ratio: nullableDecimalSchema.optional(),
  information_ratio: nullableDecimalSchema.optional(),
  sharpe_t_stat: nullableDecimalSchema.optional(),
  significance_p: nullableDecimalSchema.optional(),
  annualized_return_pct: nullableDecimalSchema.optional(),
  annualized_volatility_pct: nullableDecimalSchema.optional(),
  exposure_pct: nullableDecimalSchema.optional(),
  return_periods: z.number().nullish(),
  return_gaps: z.number().nullish(),
  annualization_factor: nullableDecimalSchema.optional(),
  max_drawdown_duration_seconds: z.number().nullish(),
  max_drawdown_duration_bars: z.number().nullish(),
  max_drawdown_peak_at: z.string().nullish(),
  max_drawdown_trough_at: z.string().nullish(),
  current_drawdown_pct: nullableDecimalSchema.optional(),
  drawdown_open: z.boolean().nullish(),
});
export type Metrics = z.infer<typeof metricsSchema>;

export const equityPointSchema = z.object({ time: z.string(), equity: decimalSchema });
export type EquityPoint = z.infer<typeof equityPointSchema>;

export const tradeSchema = z.object({
  time: z.string(),
  side: z.string(),
  quantity: decimalSchema,
  price: decimalSchema,
  fee: decimalSchema,
  notional: decimalSchema,
});
export type Trade = z.infer<typeof tradeSchema>;
