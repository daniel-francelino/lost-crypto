import { dayString, toMs } from "@/lib/shared/dates";
import type { RegimeBreak } from "@/lib/shared/market-data/regime-breaks.api";

const DAY_MS = 24 * 3600 * 1000;

export type Stretch = { start: string; end: string; label: string };

const dayOf = (iso: string): string => dayString(toMs(iso));

const appliesTo = (item: RegimeBreak, exchange: string, symbol: string): boolean =>
  (item.exchange === null || item.exchange === exchange) &&
  (item.symbol === null || item.symbol === symbol);

export const breaksCrossing = (
  breaks: readonly RegimeBreak[],
  exchange: string,
  symbol: string,
  start: string,
  end: string,
): RegimeBreak[] =>
  breaks
    .filter((item) => appliesTo(item, exchange, symbol))
    .filter((item) => dayOf(item.occurred_at) > start && dayOf(item.occurred_at) <= end)
    .sort((a, b) => toMs(a.occurred_at) - toMs(b.occurred_at));

const dayBefore = (day: string): string => dayString(toMs(`${day}T00:00:00Z`) - DAY_MS);

const labelOf = (position: number, names: readonly string[]): string => {
  if (position === 0) return `antes de ${names[0] ?? ""}`;
  if (position === names.length) return `depois de ${names[position - 1] ?? ""}`;
  return `entre ${names[position - 1] ?? ""} e ${names[position] ?? ""}`;
};

export const stretchesOf = (
  crossing: readonly RegimeBreak[],
  start: string,
  end: string,
): Stretch[] => {
  const days = crossing.map((item) => dayOf(item.occurred_at));
  const names = crossing.map((item) => item.name);
  const edges = [start, ...days, end];
  return edges.slice(0, -1).map((from, position) => ({
    start: from,
    end: position === days.length ? end : dayBefore(edges[position + 1] ?? end),
    label: labelOf(position, names),
  }));
};

export const registeredAfter = (breakCreatedAt: string, runCreatedAt: string): boolean =>
  toMs(breakCreatedAt) > toMs(runCreatedAt);
