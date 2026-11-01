import { z } from "zod";
import { request } from "@/lib/shared/api/client";

const gapSchema = z.object({ start: z.string(), end: z.string(), missing: z.number() });

const rangeCoverageSchema = z.object({
  start: z.string(),
  end: z.string(),
  expected: z.number(),
  present: z.number(),
  missing: z.number(),
  largest_gap: z.number(),
  gaps: z.array(gapSchema),
});
export type RangeCoverage = z.infer<typeof rangeCoverageSchema>;

const coverageSchema = z.object({
  exchange: z.string(),
  symbol: z.string(),
  timeframe: z.string(),
  count: z.number(),
  first: z.string().nullable(),
  last: z.string().nullable(),
  gaps: z.array(gapSchema),
  in_range: rangeCoverageSchema.nullish(),
});
export type Coverage = z.infer<typeof coverageSchema>;

export type CoverageParams = {
  exchange: string;
  symbol: string;
  timeframe: string;
  start?: string;
  end?: string;
};

export const getCoverage = (params: CoverageParams, signal?: AbortSignal): Promise<Coverage> =>
  request({ path: "/market-data/coverage", schema: coverageSchema, query: params, signal });
