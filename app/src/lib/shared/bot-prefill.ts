import { z } from "zod";

export const botPrefillSchema = z.object({
  strategy: z.string().optional().catch(undefined),
  symbol: z.string().optional().catch(undefined),
  timeframe: z.string().optional().catch(undefined),
  params: z.string().optional().catch(undefined),
});
export type BotPrefill = z.infer<typeof botPrefillSchema>;

export const prefillFromRun = (run: {
  strategy_type: string;
  symbol: string;
  timeframe: string;
  strategy_params: Record<string, unknown>;
}): BotPrefill => ({
  strategy: run.strategy_type,
  symbol: run.symbol,
  timeframe: run.timeframe,
  params: JSON.stringify(run.strategy_params),
});

export const prefillParams = (prefill: BotPrefill): Record<string, unknown> => {
  if (prefill.params === undefined) return {};
  try {
    const parsed: unknown = JSON.parse(prefill.params);
    return typeof parsed === "object" && parsed !== null && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : {};
  } catch {
    return {};
  }
};
