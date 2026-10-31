import { describe, expect, it } from "vitest";
import type { Sweep, SweepRun } from "@/lib/backtests/backtests.api";
import { crossTable, formatScore, scoreOf, verdictText } from "@/lib/backtests/robustness";
import { JobStatus, RobustnessVerdict, SweepRankBy, Unknown } from "@/lib/shared/enums";

const run = (id: string, fast: number, slow: number, train: string): SweepRun => ({
  id,
  status: JobStatus.Completed,
  strategy_params: { fast_period: fast, slow_period: slow },
  total_return_pct: "1",
  train_return_pct: train,
  test_return_pct: "0.5",
  train_sharpe_ratio: "1.2",
  max_drawdown_pct: "3",
  round_trips: 8,
  buy_and_hold_return_pct: "2",
  error: null,
});

const ROBUSTNESS = {
  verdict: RobustnessVerdict.Plateau,
  metric: SweepRankBy.TrainReturn,
  winner_score: "20",
  neighbours: 2,
  neighbour_mean: "17",
  neighbour_min: "15",
  neighbour_ratio: "0.85",
  profitable_share: "100",
  median: "16",
  top3_mean: "18",
  scored: 4,
};

const SWEEP: Sweep = {
  id: "s",
  created_at: "2026-10-31T00:00:00Z",
  strategy_type: "ema_crossover",
  grid: { slow_period: [21, 50], fast_period: [5, 9] },
  run_count: 4,
  completed: 4,
  failed: 0,
  skipped: [],
  ranked_by: SweepRankBy.TrainReturn,
  note: "",
  robustness: ROBUSTNESS,
  runs: [run("a", 9, 21, "20"), run("b", 5, 21, "15"), run("c", 9, 50, "19"), run("d", 5, 50, "2")],
};

describe("sweep robustness view", () => {
  it("builds a cross table for two parameters", () => {
    const table = crossTable(SWEEP);
    expect(table?.rowName).toBe("fast_period");
    expect(table?.columns).toEqual(["21", "50"]);
    expect(table?.cell("9", "21")?.id).toBe("a");
    expect(table?.cell("7", "21")).toBeUndefined();
    expect(crossTable({ ...SWEEP, grid: { fast_period: [5, 9] } })).toBeNull();
  });

  it("reads the ranking metric of each run", () => {
    const first = SWEEP.runs[0];
    if (first === undefined) throw new Error("no run");
    expect(scoreOf(first, SweepRankBy.TrainReturn)).toBe("20");
    expect(scoreOf(first, SweepRankBy.TrainSharpe)).toBe("1.2");
    expect(scoreOf(first, SweepRankBy.TestSharpe)).toBeNull();
    expect(scoreOf(first, Unknown)).toBeNull();
    expect(formatScore(SweepRankBy.TrainReturn, "20")).toBe("+20,00%");
    expect(formatScore(SweepRankBy.Sharpe, "1.234")).toBe("1,23");
  });

  it("explains each verdict", () => {
    expect(verdictText(ROBUSTNESS)).toContain("~85%");
    expect(
      verdictText({ ...ROBUSTNESS, verdict: RobustnessVerdict.Peak, neighbour_ratio: "0.1" }),
    ).toContain("Pico isolado");
    expect(verdictText({ ...ROBUSTNESS, verdict: RobustnessVerdict.Unprofitable })).toContain(
      "Nenhuma combinação",
    );
    expect(verdictText({ ...ROBUSTNESS, verdict: RobustnessVerdict.Insufficient })).toContain(
      "3 valores",
    );
  });
});
