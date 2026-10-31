import { describe, expect, it } from "vitest";
import type { Sweep, SweepRun } from "@/lib/backtests/backtests.api";
import { RANK_LABELS, RANK_NOTES, winnerCheck } from "@/lib/backtests/sweep";
import { JobStatus, SweepRankBy } from "@/lib/shared/enums";

const RUN: SweepRun = {
  id: "a",
  status: JobStatus.Completed,
  strategy_params: { fast_period: 9 },
  total_return_pct: "20",
  train_return_pct: "25",
  test_return_pct: "3",
  max_drawdown_pct: "8",
  round_trips: 10,
  buy_and_hold_return_pct: "12",
  error: null,
};

const sweepOf = (runs: SweepRun[]): Sweep => ({
  id: "s",
  created_at: "2026-10-31T00:00:00Z",
  strategy_type: "ema_crossover",
  grid: {},
  run_count: runs.length,
  completed: runs.length,
  failed: 0,
  skipped: [],
  trials: runs.length,
  prior_trials: 0,
  ranked_by: SweepRankBy.TrainReturn,
  note: "",
  runs,
});

describe("sweep winner check", () => {
  it("holds when the winner is positive out of sample and beats holding", () => {
    const check = winnerCheck(sweepOf([RUN]));
    expect(check?.holds).toBe(true);
    expect(check?.winner.id).toBe("a");
  });

  it("fails when the winner loses in the test part", () => {
    const check = winnerCheck(sweepOf([{ ...RUN, test_return_pct: "-2" }]));
    expect(check?.holds).toBe(false);
    expect(check?.reasons[0]).toContain("não lucrou no teste");
  });

  it("fails when the winner trails buy and hold", () => {
    expect(winnerCheck(sweepOf([{ ...RUN, total_return_pct: "5" }]))?.holds).toBe(false);
  });

  it("skips failed runs and sweeps without a test part", () => {
    const failed = { ...RUN, id: "f", status: JobStatus.Failed };
    expect(winnerCheck(sweepOf([failed, RUN]))?.winner.id).toBe("a");
    expect(winnerCheck(sweepOf([{ ...RUN, test_return_pct: null }]))).toBeNull();
  });

  it("explains every ranking in Portuguese", () => {
    for (const rank of Object.values(SweepRankBy)) {
      expect(RANK_LABELS[rank]).not.toBe("");
      expect(RANK_NOTES[rank]).not.toBe("");
    }
  });
});
