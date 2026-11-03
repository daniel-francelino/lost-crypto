import { z } from "zod";
import { request } from "@/lib/shared/api/client";
import {
  decimalSchema,
  lenientEnum,
  nullableDecimalSchema,
  nullableTimestampSchema,
} from "@/lib/shared/api/schemas";
import { BotState, ExecutionMode, TradingProduct } from "@/lib/shared/enums";

const overviewSchema = z.object({
  id: z.string(),
  name: z.string(),
  mode: lenientEnum(ExecutionMode),
  exchange: z.string(),
  symbol: z.string(),
  timeframe: z.string(),
  strategy_type: z.string(),
  strategy_params: z.record(z.string(), z.unknown()),
  desired_state: lenientEnum(BotState),
  observed_state: lenientEnum(BotState),
  equity: decimalSchema,
  return_pct: decimalSchema,
  realized_pnl: decimalSchema,
  fees_paid: decimalSchema,
  in_position: z.boolean(),
  last_price: nullableDecimalSchema,
  product: lenientEnum(TradingProduct).optional(),
  position_side: z.string().nullable().optional(),
  leverage: z.number().optional(),
  unrealized_pnl: decimalSchema.optional(),
  isolated_margin: decimalSchema.optional(),
  liquidation_price: nullableDecimalSchema.optional(),
  liquidation_price_source: z.string().nullable().optional(),
  funding_paid: decimalSchema.optional(),
  funding_received: decimalSchema.optional(),
  last_heartbeat_at: nullableTimestampSchema,
  interventions_30d: z.number(),
});
export type BotOverview = z.infer<typeof overviewSchema>;

export const getOverview = (signal?: AbortSignal) =>
  request({ path: "/bots/overview", schema: z.array(overviewSchema), signal });
