import { z } from "zod";
import { request } from "@/lib/shared/api/client";
import { Trend, TrendFrame } from "@/lib/shared/enums";

export const registeredSymbolSchema = z.object({
  id: z.string(),
  exchange: z.string(),
  symbol: z.string(),
  active: z.boolean(),
  created_at: z.string(),
});
export type RegisteredSymbol = z.infer<typeof registeredSymbolSchema>;

const readingSchema = z.object({
  frame: z.nativeEnum(TrendFrame),
  bar_open_time: z.string(),
  trend: z.nativeEnum(Trend),
  previous_trend: z.nativeEnum(Trend).nullable(),
  confirmed: z.boolean(),
  checks: z.record(z.string(), z.boolean().nullable()),
  close: z.string().nullable(),
  ema_fast: z.string().nullable(),
  ema_slow: z.string().nullable(),
  ema_distance_pct: z.string().nullable(),
  adx: z.string().nullable(),
  computed_at: z.string(),
});
export type TrendReading = z.infer<typeof readingSchema>;

const symbolTrendsSchema = z.object({
  symbol: registeredSymbolSchema,
  readings: z.array(readingSchema),
});
export type SymbolTrends = z.infer<typeof symbolTrendsSchema>;

export const listRegisteredSymbols = (signal?: AbortSignal) =>
  request({ path: "/trends/symbols", schema: z.array(registeredSymbolSchema), signal });

export const listTrends = (signal?: AbortSignal) =>
  request({ path: "/trends", schema: z.array(symbolTrendsSchema), signal });
