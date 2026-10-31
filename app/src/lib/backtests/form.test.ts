import { describe, expect, it } from "vitest";
import {
  buildGrid,
  combinationCount,
  defaultBacktestValues,
  gridError,
  toBacktestInput,
} from "@/lib/backtests/form";
import { toMs } from "@/lib/shared/dates";
import { parseGridList } from "@/lib/shared/strategies/params";
import type { Strategy } from "@/lib/shared/strategies/strategies.api";

const STRATEGY: Strategy = {
  type_key: "ema_crossover",
  name: "EMA",
  description: "",
  parameters: [
    { name: "fast_period", type: "integer", default: 9, minimum: 2, description: "" },
    { name: "slow_period", type: "integer", default: 21, minimum: 3, description: "" },
    { name: "stop_loss_pct", type: "number", default: null, minimum: null, description: "" },
  ],
};
const NOW = toMs("2026-10-31T12:00:00Z");

describe("backtest form", () => {
  it("defaults to the last 90 days in UTC with an out-of-sample split", () => {
    const values = defaultBacktestValues(STRATEGY, NOW);
    expect(values.start).toBe("2026-08-02");
    expect(values.end).toBe("2026-10-31");
    expect(values.testFraction).toBe("0.3");
  });

  it("builds the request with UTC day boundaries and string money", () => {
    const input = toBacktestInput(defaultBacktestValues(STRATEGY, NOW), STRATEGY);
    expect(input.start).toBe("2026-08-02T00:00:00Z");
    expect(input.end).toBe("2026-10-31T23:59:59Z");
    expect(input.initial_capital).toBe("1000");
    expect(input.fee_rate).toBeNull();
    expect(input.seed).toBe(0);
    expect(input.strategy_params).toEqual({ fast_period: 9, slow_period: 21 });
  });

  it("parses comma separated grid values", () => {
    expect(parseGridList("5, 9,12", true)).toEqual([5, 9, 12]);
    expect(parseGridList("1.5,2", false)).toEqual([1.5, 2]);
    expect(parseGridList("", true)).toBe("Informe ao menos um valor.");
    expect(parseGridList("5,x", true)).toBe('"x" não é um número.');
    expect(parseGridList("5.5", true)).toBe('"5.5" não é um número inteiro.');
  });

  it("builds a grid, counts combinations and enforces the limit of 200", () => {
    const grid = buildGrid(STRATEGY, {
      fast_period: "5,9,12",
      slow_period: "21,50",
      stop_loss_pct: "",
    });
    expect(grid).toEqual({ fast_period: [5, 9, 12], slow_period: [21, 50] });
    if (typeof grid === "string") throw new Error(grid);
    expect(combinationCount(grid)).toBe(6);
    expect(gridError(grid)).toBeUndefined();
    expect(gridError({})).toContain("ao menos um parâmetro");
    const big = {
      a: Array.from({ length: 15 }, (_, i) => i),
      b: Array.from({ length: 15 }, (_, i) => i),
    };
    expect(gridError(big)).toContain("225");
    expect(buildGrid(STRATEGY, { fast_period: "a" })).toContain("fast_period");
  });
});
