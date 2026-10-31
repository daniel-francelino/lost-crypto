import { z } from "zod";
import { request } from "@/lib/shared/api/client";

const coverageSchema = z.object({
  exchange: z.string(),
  symbol: z.string(),
  timeframe: z.string(),
  count: z.number(),
  first: z.string().nullable(),
  last: z.string().nullable(),
  gaps: z.array(z.object({ start: z.string(), end: z.string(), missing: z.number() })),
});
export type Coverage = z.infer<typeof coverageSchema>;

export type CoverageParams = { exchange: string; symbol: string; timeframe: string };

export const getCoverage = (params: CoverageParams, signal?: AbortSignal): Promise<Coverage> =>
  request({ path: "/market-data/coverage", schema: coverageSchema, query: params, signal });
