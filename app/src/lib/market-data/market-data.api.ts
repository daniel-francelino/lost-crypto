import { z } from "zod";
import { request } from "@/lib/shared/api/client";
import { HttpMethod } from "@/lib/shared/api/http";
import { lenientEnum } from "@/lib/shared/api/schemas";
import { JobStatus } from "@/lib/shared/enums";

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
