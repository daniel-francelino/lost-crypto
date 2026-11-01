import { z } from "zod";
import { request } from "@/lib/shared/api/client";
import { decimalSchema, nullableDecimalSchema } from "@/lib/shared/api/schemas";

const halfLifeSchema = z.object({
  n: z.number(),
  slope: nullableDecimalSchema,
  t_stat: nullableDecimalSchema,
  stationary_at_5pct: z.boolean().nullable(),
  half_life_bars: nullableDecimalSchema,
  half_life_seconds: nullableDecimalSchema,
  log_prices: z.boolean(),
  gaps: z.number(),
  warning: z.string(),
  sample_every: z.number().optional(),
  hurst: nullableDecimalSchema.optional(),
  suggested_windows: z.array(z.number()).optional(),
  variance_ratios: z
    .array(z.object({ lag: z.number(), ratio: decimalSchema, z_stat: decimalSchema }))
    .optional(),
});
export type HalfLifeEstimate = z.infer<typeof halfLifeSchema>;

export type HalfLifeQuery = {
  exchange: string;
  symbol: string;
  timeframe: string;
  start: string;
  end: string;
  sample_every?: number;
};

export const getHalfLife = (params: HalfLifeQuery, signal?: AbortSignal) =>
  request({ path: "/market-data/half-life", schema: halfLifeSchema, query: params, signal });
