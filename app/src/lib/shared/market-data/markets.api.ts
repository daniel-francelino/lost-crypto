import { z } from "zod";
import { request } from "@/lib/shared/api/client";

const marketSchema = z.object({
  exchange: z.string(),
  symbol: z.string(),
  base: z.string().nullable(),
  quote: z.string().nullable(),
  settlement: z.string().nullable(),
  product: z.string(),
  contract_size: z.string(),
  active: z.boolean(),
});

export type Market = z.infer<typeof marketSchema>;

export const listMarkets = (exchange: string, signal?: AbortSignal) =>
  request({
    path: "/market-data/markets",
    schema: z.array(marketSchema),
    query: { exchange, active_only: true },
    signal,
  });
