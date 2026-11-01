import { describe, expect, it } from "vitest";
import type { Sweep, SweepRun } from "@/lib/backtests/backtests.api";
import { isStartSensitivity, startSensitivity } from "@/lib/backtests/start-sensitivity";

const run = (total: string | null, drawdown: string | null): SweepRun =>
  ({ total_return_pct: total, max_drawdown_pct: drawdown }) as SweepRun;

const sweep = (grid: Record<string, unknown>, runs: SweepRun[]): Pick<Sweep, "grid" | "runs"> => ({
  grid,
  runs,
});

describe("start-date sensitivity", () => {
  it("only applies to a sweep that has the start-offset axis", () => {
    expect(isStartSensitivity(sweep({ fast_period: [3] }, []))).toBe(false);
    expect(startSensitivity(sweep({ fast_period: [3] }, [run("5", "2")]))).toBeNull();
    expect(isStartSensitivity(sweep({ start_offset_days: [0, 3] }, []))).toBe(true);
  });

  it("picks the minimum, the lower median and the maximum without doing arithmetic", () => {
    const result = startSensitivity(
      sweep({ start_offset_days: [0, 3, 6, 9] }, [
        run("12.5", "8"),
        run("-4", "20"),
        run("30", "5"),
        run("7", "11"),
      ]),
    );
    expect(result?.runs).toBe(4);
    expect(result?.returnPct).toEqual({ min: "-4", median: "7", max: "30" });
    expect(result?.drawdownPct).toEqual({ min: "5", median: "8", max: "20" });
  });

  it("ignores runs that did not finish and returns nothing when none did", () => {
    const grid = { start_offset_days: [0, 3] };
    expect(startSensitivity(sweep(grid, [run(null, null), run("4", "1")]))?.runs).toBe(1);
    expect(startSensitivity(sweep(grid, [run(null, null)]))).toBeNull();
  });

  it("handles one run: all three numbers are the same", () => {
    const result = startSensitivity(sweep({ start_offset_days: [0] }, [run("3", "1")]));
    expect(result?.returnPct).toEqual({ min: "3", median: "3", max: "3" });
  });
});
