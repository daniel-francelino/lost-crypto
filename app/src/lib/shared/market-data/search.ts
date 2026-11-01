import { z } from "zod";

export const marketDataSearchSchema = z.object({
  symbol: z.string().optional().catch(undefined),
  timeframe: z.string().optional().catch(undefined),
  start: z.string().optional().catch(undefined),
  end: z.string().optional().catch(undefined),
});
export type MarketDataSearch = z.infer<typeof marketDataSearchSchema>;
