import type { Sweep, SweepRun } from "@/lib/backtests/backtests.api";
import { compareDecimal } from "@/lib/shared/format";

export const START_OFFSET_KEY = "start_offset_days";
export const DEFAULT_OFFSETS = "0, 3, 6, 9, 12, 15, 18, 21";

export type Spread = { min: string; median: string; max: string };
export type StartSensitivity = {
  runs: number;
  returnPct: Spread | null;
  drawdownPct: Spread | null;
};

export const isStartSensitivity = (sweep: Pick<Sweep, "grid">): boolean =>
  START_OFFSET_KEY in sweep.grid;

const spreadOf = (values: readonly string[]): Spread | null => {
  const sorted = [...values].sort(compareDecimal);
  const first = sorted[0];
  const last = sorted[sorted.length - 1];
  const middle = sorted[Math.floor((sorted.length - 1) / 2)];
  return first === undefined || last === undefined || middle === undefined
    ? null
    : { min: first, median: middle, max: last };
};

const present = (values: readonly (string | null | undefined)[]): string[] =>
  values.filter((value): value is string => value !== null && value !== undefined);

const completed = (runs: readonly SweepRun[]): SweepRun[] =>
  runs.filter((run) => run.total_return_pct !== null);

export const startSensitivity = (sweep: Pick<Sweep, "grid" | "runs">): StartSensitivity | null => {
  if (!isStartSensitivity(sweep)) return null;
  const done = completed(sweep.runs);
  if (done.length === 0) return null;
  return {
    runs: done.length,
    returnPct: spreadOf(present(done.map((run) => run.total_return_pct))),
    drawdownPct: spreadOf(present(done.map((run) => run.max_drawdown_pct))),
  };
};
