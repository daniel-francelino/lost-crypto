import { describe, expect, it } from "vitest";
import type { Backtest } from "@/lib/backtests/backtests.api";
import { ScreeningLevel, screeningFlags } from "@/lib/backtests/screening";
import type { Metrics } from "@/lib/shared/analytics";

const BASE: Metrics = {
  initial_capital: "1000",
  final_equity: "1300",
  net_pnl: "300",
  total_return_pct: "30",
  buy_and_hold_return_pct: "10",
  max_drawdown_pct: "5",
  fees_paid: "2",
  fills: 60,
  round_trips: 30,
  win_rate_pct: "55",
  profit_factor: "1.6",
  avg_trade_pnl: "10",
  open_position: false,
  rejected_signals: 0,
  sharpe_ratio: "1.8",
  return_periods: 8760,
  exposure_pct: "60",
  max_drawdown_duration_seconds: 10 * 86400,
  drawdown_open: false,
  current_drawdown_pct: "0",
};
type Run = Pick<Backtest, "start" | "end" | "segments">;

const YEAR: Run = { start: "2025-01-01T00:00:00Z", end: "2025-12-31T23:59:59Z", segments: null };

const ids = (metrics: Metrics, run: Run = YEAR) =>
  screeningFlags({ ...run, metrics }).map((flag) => flag.id);

describe("screening flags (Chan's rules of thumb)", () => {
  it("raises nothing for a healthy result", () => {
    expect(ids(BASE)).toEqual([]);
  });

  it("flags a test window looked at too many times, only when there is a split", () => {
    const segments = {
      split_at: "2025-09-01T00:00:00Z",
      test_fraction: "0.3",
      train: BASE,
      test: BASE,
    } as Backtest["segments"];
    const split = { ...YEAR, segments };
    const flagged = (priorRuns: number, run: Run) =>
      screeningFlags({ ...run, prior_runs: priorRuns, metrics: BASE }).map((flag) => flag.id);
    expect(flagged(10, split)).toEqual(["reuse"]);
    expect(flagged(9, split)).toEqual([]);
    expect(flagged(50, YEAR)).toEqual([]);
  });

  it("flags a holding limit that is long against the sample", () => {
    const withLimit = (limit: unknown, periods = 8760) =>
      screeningFlags({
        ...YEAR,
        strategy_params: { max_holding_candles: limit },
        metrics: { ...BASE, return_periods: periods },
      }).map((flag) => flag.id);
    expect(withLimit(500)).toEqual(["long-holding"]);
    expect(withLimit(100)).toEqual([]);
    expect(withLimit(null)).toEqual([]);
    expect(withLimit(50, 0)).toEqual([]);
  });

  it("flags each rule on its own", () => {
    expect(ids({ ...BASE, sharpe_ratio: "0.7" })).toEqual(["sharpe"]);
    expect(ids({ ...BASE, max_drawdown_pct: "12.5" })).toEqual(["drawdown-depth"]);
    expect(ids({ ...BASE, max_drawdown_duration_seconds: 150 * 86400 })).toEqual([
      "drawdown-duration",
    ]);
    expect(ids({ ...BASE, round_trips: 3 })).toEqual(["few-trades"]);
    expect(ids({ ...BASE, exposure_pct: "8" })).toEqual(["exposure"]);
    expect(ids({ ...BASE, sharpe_t_stat: "1.2" })).toEqual(["significance"]);
    expect(ids({ ...BASE, sharpe_t_stat: "1.7" })).toEqual([]);
    expect(ids({ ...BASE, total_return_pct: "5" })).toEqual(["benchmark"]);
    expect(ids({ ...BASE, drawdown_open: true, current_drawdown_pct: "3" })).toEqual([
      "drawdown-open",
    ]);
  });

  it("reports a short sample instead of a missing Sharpe", () => {
    expect(ids({ ...BASE, sharpe_ratio: null, return_periods: 12 })).toEqual(["sample"]);
  });

  it("lists warnings before information", () => {
    const flags = screeningFlags({
      ...YEAR,
      metrics: { ...BASE, exposure_pct: "8", sharpe_ratio: "0.2" },
    });
    expect(flags.map((flag) => flag.level)).toEqual([ScreeningLevel.Warning, ScreeningLevel.Info]);
  });

  it("flags a train profit that does not hold in the test part", () => {
    const segments = {
      split_at: "2025-09-01T00:00:00Z",
      test_fraction: "0.3",
      train: { ...BASE, total_return_pct: "40" },
      test: { ...BASE, total_return_pct: "-4" },
    };
    expect(ids(BASE, { ...YEAR, segments })).toEqual(["out-of-sample"]);
  });

  it("ignores metrics stored before the new fields existed", () => {
    const old: Metrics = { ...BASE };
    delete old.sharpe_ratio;
    delete old.return_periods;
    delete old.exposure_pct;
    delete old.max_drawdown_duration_seconds;
    delete old.drawdown_open;
    expect(ids(old)).toEqual([]);
  });

  it("flags data problems and small samples from data_quality", () => {
    const quality = {
      outliers: 2,
      invalid_candles: 0,
      gaps: {
        expected: 100,
        present: 90,
        missing: 10,
        gap_count: 1,
        largest_gap_candles: 10,
        largest_gap_seconds: 36000,
        over_limit: true,
        allowed: true,
        gaps: [],
      },
      sample: {
        free_parameters: 2,
        bars: 300,
        round_trips: 30,
        min_bars: 504,
        min_round_trips: 30,
        meets_bar_rule: false,
        meets_trade_rule: true,
      },
    };
    const flags = screeningFlags({ ...YEAR, metrics: BASE, data_quality: quality });
    expect(flags.map((flag) => flag.id)).toEqual(["outliers", "gaps", "sample-bars"]);
  });

  it("flags a small test part", () => {
    const flags = screeningFlags({ ...YEAR, metrics: BASE, test_fraction: "0.1" });
    expect(flags.map((flag) => flag.id)).toEqual(["small-test"]);
    expect(screeningFlags({ ...YEAR, metrics: BASE, test_fraction: "0.3" })).toEqual([]);
  });
});
