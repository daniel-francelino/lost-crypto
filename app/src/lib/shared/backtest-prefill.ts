import { z } from "zod";

export const backtestPrefillSchema = z.object({
  strategy: z.string().optional().catch(undefined),
  symbol: z.string().optional().catch(undefined),
  timeframe: z.string().optional().catch(undefined),
  params: z.string().optional().catch(undefined),
  feeRate: z.string().optional().catch(undefined),
  slippageBps: z.string().optional().catch(undefined),
  fillTiming: z.string().optional().catch(undefined),
  risk: z.string().optional().catch(undefined),
});
export type BacktestPrefill = z.infer<typeof backtestPrefillSchema>;

export const parseJsonRecord = (text: string | undefined): Record<string, unknown> => {
  if (text === undefined) return {};
  try {
    const parsed: unknown = JSON.parse(text);
    return typeof parsed === "object" && parsed !== null && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : {};
  } catch {
    return {};
  }
};
