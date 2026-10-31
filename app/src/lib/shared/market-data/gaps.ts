import type { RangeCoverage } from "@/lib/shared/market-data/coverage.api";
import { Timeframe } from "@/lib/shared/enums";

export const MAX_MISSING_SHARE = 0.01;
export const MAX_GAP_SECONDS = 24 * 3600;

const TIMEFRAME_SECONDS: Record<string, number> = {
  [Timeframe.M1]: 60,
  [Timeframe.M5]: 300,
  [Timeframe.M15]: 900,
  [Timeframe.H1]: 3600,
  [Timeframe.H4]: 4 * 3600,
  [Timeframe.D1]: 24 * 3600,
};

export const timeframeSeconds = (timeframe: string): number => TIMEFRAME_SECONDS[timeframe] ?? 3600;

export const largestGapSeconds = (range: RangeCoverage, timeframe: string): number =>
  range.largest_gap * timeframeSeconds(timeframe);

export const gapsOverLimit = (
  range: RangeCoverage | null | undefined,
  timeframe: string,
): boolean =>
  range !== null &&
  range !== undefined &&
  range.expected > 0 &&
  (range.missing / range.expected > MAX_MISSING_SHARE ||
    largestGapSeconds(range, timeframe) > MAX_GAP_SECONDS);
