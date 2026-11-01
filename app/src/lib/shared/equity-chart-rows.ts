import type { EquityPoint } from "@/lib/shared/analytics";
import { formatDateTimeShort } from "@/lib/shared/dates";

const MAX_POINTS = 1000;

export type EquityRow = { label: string; time: string; equity: number };
export type UnderwaterRow = { label: string; time: string; drawdown: number };

export const downsample = <T>(rows: T[], max: number = MAX_POINTS): T[] => {
  if (rows.length <= max) return rows;
  const step = Math.ceil(rows.length / max);
  const picked = rows.filter((_, index) => index % step === 0);
  const last = rows.at(-1);
  return last !== undefined && picked.at(-1) !== last ? [...picked, last] : picked;
};

const extremesOf = <T>(bucket: T[], value: (row: T) => number): T[] => {
  let low = 0;
  let high = 0;
  bucket.forEach((row, index) => {
    if (value(row) < value(bucket[low] as T)) low = index;
    if (value(row) > value(bucket[high] as T)) high = index;
  });
  const indexes = [...new Set([low, high])].sort((a, b) => a - b);
  return indexes.map((index) => bucket[index] as T);
};

export const downsampleExtremes = <T>(
  rows: T[],
  value: (row: T) => number,
  max: number = MAX_POINTS,
): T[] => {
  if (rows.length <= max) return rows;
  const size = Math.ceil(rows.length / Math.floor(max / 2));
  const picked: T[] = [];
  for (let start = 0; start < rows.length; start += size) {
    picked.push(...extremesOf(rows.slice(start, start + size), value));
  }
  const first = rows[0];
  const last = rows.at(-1);
  const head = first !== undefined && picked[0] !== first ? [first] : [];
  const tail = last !== undefined && picked.at(-1) !== last ? [last] : [];
  return [...head, ...picked, ...tail];
};

const equityRows = (points: EquityPoint[]): EquityRow[] =>
  points.map((point) => ({
    label: formatDateTimeShort(point.time),
    time: point.time,
    equity: Number.parseFloat(point.equity),
  }));

export const equityChartRows = (points: EquityPoint[]): EquityRow[] =>
  downsampleExtremes(equityRows(points), (row) => row.equity);

export const underwaterRows = (points: EquityPoint[]): UnderwaterRow[] => {
  let peak = Number.NEGATIVE_INFINITY;
  const rows = equityRows(points).map((row) => {
    peak = Math.max(peak, row.equity);
    const drawdown = peak > 0 ? ((row.equity - peak) / peak) * 100 : 0;
    return { label: row.label, time: row.time, drawdown };
  });
  return downsampleExtremes(rows, (row) => row.drawdown);
};

export const compareChartRows = (
  curves: { id: string; points: EquityPoint[] }[],
): Record<string, string | number>[] => {
  const byTime = new Map<string, Record<string, string | number>>();
  for (const curve of curves) {
    for (const point of downsample(curve.points)) {
      const row = byTime.get(point.time) ?? {
        time: point.time,
        label: formatDateTimeShort(point.time),
      };
      row[curve.id] = Number.parseFloat(point.equity);
      byTime.set(point.time, row);
    }
  }
  return [...byTime.values()].sort((a, b) => String(a["time"]).localeCompare(String(b["time"])));
};
