import type { EquityPoint } from "@/lib/shared/analytics";
import { formatDateTimeShort } from "@/lib/shared/dates";

const MAX_POINTS = 1000;

export type EquityRow = { label: string; time: string; equity: number };

export const downsample = <T>(rows: T[], max: number = MAX_POINTS): T[] => {
  if (rows.length <= max) return rows;
  const step = Math.ceil(rows.length / max);
  const picked = rows.filter((_, index) => index % step === 0);
  const last = rows.at(-1);
  return last !== undefined && picked.at(-1) !== last ? [...picked, last] : picked;
};

export const equityChartRows = (points: EquityPoint[]): EquityRow[] =>
  downsample(points).map((point) => ({
    label: formatDateTimeShort(point.time),
    time: point.time,
    equity: Number.parseFloat(point.equity),
  }));

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
