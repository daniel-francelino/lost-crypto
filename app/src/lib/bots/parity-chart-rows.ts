import type { ParitySummary } from "@/lib/bots/bots.api";
import type { EquityPoint } from "@/lib/shared/analytics";
import { formatDateTimeShort, toMs } from "@/lib/shared/dates";

export type ParityRow = { label: string; time: string; bot?: number; replay?: number };

export const parityChartRows = (bot: EquityPoint[], summary: ParitySummary): ParityRow[] => {
  const start = toMs(summary.period_start);
  const byTime = new Map<number, ParityRow>();
  const row = (time: string): ParityRow => {
    const ms = toMs(time);
    const existing = byTime.get(ms) ?? { label: formatDateTimeShort(time), time };
    byTime.set(ms, existing);
    return existing;
  };
  for (const point of bot) {
    if (toMs(point.time) > start) row(point.time).bot = Number.parseFloat(point.equity);
  }
  for (const [time, equity] of summary.replay_equity) {
    row(time).replay = Number.parseFloat(equity);
  }
  return [...byTime.entries()].sort(([a], [b]) => a - b).map(([, value]) => value);
};
