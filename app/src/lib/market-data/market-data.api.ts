import { z } from "zod";
import { request } from "@/lib/shared/api/client";
import { HttpMethod } from "@/lib/shared/api/http";
import { lenientEnum, nullableDecimalSchema } from "@/lib/shared/api/schemas";
import { CandleProblem, JobStatus, ListingStatus } from "@/lib/shared/enums";

export const candleSampleSchema = z.object({
  open_time: z.string(),
  problems: z.array(lenientEnum(CandleProblem)),
});
export type CandleSample = z.infer<typeof candleSampleSchema>;

const importJobSchema = z.object({
  id: z.string(),
  exchange: z.string(),
  symbol: z.string(),
  timeframe: z.string(),
  start: z.string(),
  end: z.string(),
  status: lenientEnum(JobStatus),
  candles_imported: z.number(),
  error: z.string().nullable(),
  created_at: z.string(),
  started_at: z.string().nullable(),
  finished_at: z.string().nullable(),
  candles_rejected: z.number().optional(),
  candles_changed: z.number().optional(),
  rejection_samples: z.array(candleSampleSchema).optional(),
});
export type ImportJob = z.infer<typeof importJobSchema>;

const candleSchema = z.object({
  open_time: z.string(),
  open: z.string(),
  high: z.string(),
  low: z.string(),
  close: z.string(),
  volume: z.string(),
});
export type Candle = z.infer<typeof candleSchema>;

export type ImportInput = {
  exchange: string;
  symbol: string;
  timeframe: string;
  start: string;
  end: string;
};

export const listImports = (limit: number, signal?: AbortSignal) =>
  request({
    path: "/market-data/imports",
    schema: z.array(importJobSchema),
    query: { limit },
    signal,
  });

export const requestImport = (body: ImportInput) =>
  request({ method: HttpMethod.Post, path: "/market-data/imports", schema: importJobSchema, body });

export const listCandles = (
  params: ImportInput & { limit: number },
  signal?: AbortSignal,
): Promise<Candle[]> =>
  request({
    path: "/market-data/candles",
    schema: z.array(candleSchema),
    query: {
      exchange: params.exchange,
      symbol: params.symbol,
      timeframe: params.timeframe,
      start: params.start,
      end: params.end,
      limit: params.limit,
    },
    signal,
  });

const outlierSchema = z.object({
  open_time: z.string(),
  close: z.string(),
  return_pct: z.string(),
  sigmas: z.string(),
  reference_symbol: z.string().nullable(),
  reference_return_pct: nullableDecimalSchema,
});
export type Outlier = z.infer<typeof outlierSchema>;

export const listOutliers = (params: ImportInput, signal?: AbortSignal): Promise<Outlier[]> =>
  request({
    path: "/market-data/outliers",
    schema: z.array(outlierSchema),
    query: params,
    signal,
  });

const listingSchema = z.object({
  exchange: z.string(),
  symbol: z.string(),
  status: lenientEnum(ListingStatus),
  first_seen: z.string(),
  last_seen: z.string(),
  delisted_at: z.string().nullable(),
});
export type Listing = z.infer<typeof listingSchema>;

export const listListings = (
  exchange: string,
  symbol: string,
  signal?: AbortSignal,
): Promise<Listing[]> =>
  request({
    path: "/market-data/listings",
    schema: z.array(listingSchema),
    query: { exchange, symbol },
    signal,
  });

const momentumGridSchema = z.object({
  cells: z.array(
    z.object({
      lookback: z.number(),
      holding: z.number(),
      n: z.number(),
      correlation: nullableDecimalSchema,
      z_stat: nullableDecimalSchema,
      significant_corrected: z.boolean().nullable(),
      reason: z.string().nullable(),
    }),
  ),
  alpha_corrected: nullableDecimalSchema,
  critical_z: nullableDecimalSchema,
  candles: z.number(),
  gaps: z.number(),
  warning: z.string(),
});
export type MomentumGrid = z.infer<typeof momentumGridSchema>;

export type MomentumGridQuery = {
  exchange: string;
  symbol: string;
  timeframe: string;
  start: string;
  end: string;
  lookbacks: string;
  holdings: string;
};

export const getMomentumGrid = (params: MomentumGridQuery, signal?: AbortSignal) =>
  request({
    path: "/market-data/momentum-grid",
    schema: momentumGridSchema,
    query: params,
    signal,
  });
