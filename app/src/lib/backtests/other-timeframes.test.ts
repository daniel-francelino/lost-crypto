import { describe, expect, it } from "vitest";
import {
  type RunSource,
  hasStoredCandles,
  inputWithTimeframe,
  otherTimeframes,
} from "@/lib/backtests/other-timeframes";

const RUN: RunSource = {
  exchange: "binance",
  strategy_type: "ema_crossover",
  strategy_params: { fast_period: 9, slow_period: 21, label: "x" },
  symbol: "BTC/USDT",
  start: "2025-01-01T00:00:00Z",
  end: "2025-06-01T00:00:00Z",
  initial_capital: "1000",
  fee_rate: "0.001",
  slippage_bps: "5",
  slippage_model: "volatility_size",
  slippage_k_range: "0.4",
  slippage_k_size: "0.2",
  seed: 7,
  test_fraction: "0.3",
  max_drawdown_tolerance_pct: "20",
  max_drawdown_tolerance_days: 90,
  allow_gaps: true,
  fill_timing: "signal_close",
  risk: { max_position_fraction: "0.5", max_daily_loss_pct: "10", require_stop_loss: false },
};

describe("the same backtest at another interval", () => {
  it("offers the intervals of the comparison except the current one", () => {
    expect(otherTimeframes("1h")).toEqual(["5m", "15m"]);
    expect(otherTimeframes("1d")).toEqual(["5m", "15m", "1h"]);
  });

  it("changes only the timeframe", () => {
    const input = inputWithTimeframe(RUN, "15m");
    expect(input.timeframe).toBe("15m");
    expect(input).toMatchObject({
      exchange: "binance",
      symbol: "BTC/USDT",
      start: RUN.start,
      end: RUN.end,
      initial_capital: "1000",
      fee_rate: "0.001",
      slippage_bps: "5",
      slippage_model: "volatility_size",
      slippage_k_range: "0.4",
      slippage_k_size: "0.2",
      seed: 7,
      test_fraction: "0.3",
      allow_gaps: true,
      fill_timing: "signal_close",
    });
    expect(input.strategy_params).toEqual({ fast_period: 9, slow_period: 21 });
  });

  it("never repeats the cost ladder, which belongs to the original run", () => {
    expect(inputWithTimeframe(RUN, "5m").cost_sensitivity).toBe(false);
  });

  it("keeps the risk limits of a bot-like run and none of an all-in run", () => {
    expect(inputWithTimeframe(RUN, "5m").risk).toMatchObject({
      max_position_fraction: "0.5",
      max_daily_loss_pct: "10",
    });
    expect(inputWithTimeframe({ ...RUN, risk: null }, "5m").risk).toBeNull();
  });

  it("only allows an interval that has stored candles", () => {
    expect(hasStoredCandles(120)).toBe(true);
    expect(hasStoredCandles(0)).toBe(false);
    expect(hasStoredCandles(undefined)).toBe(false);
  });
});
