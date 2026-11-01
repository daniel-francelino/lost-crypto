import { describe, expect, it } from "vitest";
import { StrategyStyle } from "@/lib/shared/enums";
import { stopHints } from "@/lib/shared/strategies/stop-hint";

describe("stop hints by strategy style", () => {
  it("warns about a short stop in mean reversion", () => {
    const hints = stopHints(StrategyStyle.MeanReversion, {
      stop_loss_pct: "3",
      max_holding_candles: "10",
    });
    expect(hints).toHaveLength(1);
    expect(hints[0]).toContain("pior momento");
  });

  it("asks for a time limit when a mean-reversion strategy has none", () => {
    const hints = stopHints(StrategyStyle.MeanReversion, { max_holding_candles: "" });
    expect(hints.join(" ")).toContain("limite de tempo");
  });

  it("is quiet for a mean-reversion strategy with a time limit and no stop", () => {
    expect(stopHints(StrategyStyle.MeanReversion, { max_holding_candles: "10" })).toEqual([]);
  });

  it("explains the opposite signal as the exit of a trend strategy without a stop", () => {
    expect(stopHints(StrategyStyle.Trend, { stop_loss_pct: "" })[0]).toContain("sinal oposto");
    expect(stopHints(StrategyStyle.Trend, { stop_loss_pct: "5" })).toEqual([]);
  });

  it("says nothing without a known style or a stop parameter", () => {
    expect(stopHints(undefined, { stop_loss_pct: "" })).toEqual([]);
    expect(stopHints(StrategyStyle.Trend, {})).toEqual([]);
  });
});
