import { describe, expect, it } from "vitest";
import { gridValue, windowParamOf, windowsText } from "@/lib/backtests/half-life-hint";

describe("half-life window hint", () => {
  it("knows the window parameter only for mean-reversion strategies", () => {
    expect(windowParamOf("mean_reversion_zscore")).toBe("lookback");
    expect(windowParamOf("ema_crossover")).toBeNull();
  });

  it("shows nothing when the server suggests no window", () => {
    expect(windowsText(undefined)).toBeNull();
    expect(windowsText([])).toBeNull();
    expect(windowsText([7, 14, 27])).toBe("7, 14, 27");
  });

  it("writes the windows as a sweep grid list", () => {
    expect(gridValue([7, 14, 27])).toBe("7, 14, 27");
  });
});
