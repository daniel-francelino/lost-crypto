import { describe, expect, it } from "vitest";
import { prefillFromRun } from "@/lib/shared/bot-prefill";

const RUN = {
  strategy_type: "ema_crossover",
  symbol: "BTC/USDT",
  timeframe: "1h",
  strategy_params: { fast_period: 9 },
};

describe("bot prefill from a backtest", () => {
  it("carries the drawdown tolerance into the bot's drawdown limit", () => {
    const prefill = prefillFromRun({ ...RUN, max_drawdown_tolerance_pct: "15.500000000000000000" });
    expect(prefill.maxDrawdownPct).toBe("15.5");
    expect(prefillFromRun({ ...RUN, max_drawdown_tolerance_pct: "20.000" }).maxDrawdownPct).toBe(
      "20",
    );
  });

  it("leaves the limit empty when the backtest had no tolerance", () => {
    expect(prefillFromRun({ ...RUN, max_drawdown_tolerance_pct: null })).not.toHaveProperty(
      "maxDrawdownPct",
    );
    expect(prefillFromRun(RUN).params).toBe('{"fast_period":9}');
  });
});
