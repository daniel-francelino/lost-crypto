import { z } from "zod";
import { request } from "@/lib/shared/api/client";

const pairSchema = z.object({
  symbol: z.string(),
  base: z.string(),
  quote: z.string(),
  name: z.string(),
});
export type SupportedPair = z.infer<typeof pairSchema>;

export const listSupportedPairs = (signal?: AbortSignal) =>
  request({ path: "/market-data/symbols", schema: z.array(pairSchema), signal });
