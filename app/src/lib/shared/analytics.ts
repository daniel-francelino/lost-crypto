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
