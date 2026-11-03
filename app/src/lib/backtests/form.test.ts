import { describe, expect, it } from "vitest";
import {
  buildGrid,
  combinationCount,
  defaultBacktestValues,
  gridError,
  applyBacktestPrefill,
  sampleAdvice,
  testFractionWarning,
  toBacktestInput,
} from "@/lib/backtests/form";
import { toMs } from "@/lib/shared/dates";
import { parseGridList } from "@/lib/shared/strategies/params";
import { TradingProduct } from "@/lib/shared/enums";
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

  it("sends cost sensitivity and the drawdown tolerance, never cost sensitivity in a sweep", () => {
    const values = {
      ...defaultBacktestValues(STRATEGY, NOW),
      costSensitivity: true,
      toleranceDrawdownPct: "15",
      toleranceDrawdownDays: " 90 ",
    };
    const input = toBacktestInput(values, STRATEGY);
    expect(input.cost_sensitivity).toBe(true);
    expect(input.max_drawdown_tolerance_pct).toBe("15");
    expect(input.max_drawdown_tolerance_days).toBe(90);
    expect(toBacktestInput({ ...values, sweep: true }, STRATEGY).cost_sensitivity).toBe(false);
    const plain = toBacktestInput(defaultBacktestValues(STRATEGY, NOW), STRATEGY);
    expect(plain.max_drawdown_tolerance_pct).toBeNull();
    expect(plain.max_drawdown_tolerance_days).toBeNull();
  });

  it("warns about a small test part and short samples, and sends allow_gaps", () => {
    expect(testFractionWarning("0.2")).toContain("0.25");
    expect(testFractionWarning("0.25")).toBeUndefined();
    expect(testFractionWarning("0.3")).toBeUndefined();
    expect(testFractionWarning("")).toBeUndefined();
    const values = defaultBacktestValues(STRATEGY, NOW);
    expect(sampleAdvice(STRATEGY, values.params, 400)).toEqual({
      freeParameters: 2,
      minBars: 504,
      enough: false,
    });
    const withStop = { ...values.params, stop_loss_pct: "3" };
    expect(sampleAdvice(STRATEGY, withStop, 2000).freeParameters).toBe(3);
    expect(toBacktestInput({ ...values, allowGaps: true }, STRATEGY).allow_gaps).toBe(true);
  });

  it("fills the form from a bot and sends its risk limits and timing", () => {
    const values = applyBacktestPrefill(
      defaultBacktestValues(STRATEGY, NOW),
      {
        strategy: "ema_crossover",
        symbol: "ETH/USDT",
        params: '{"fast_period":5,"slow_period":13}',
        slippageBps: "7.500000000000000000",
        fillTiming: "signal_close",
        risk: '{"max_position_fraction":"0.500000000000000000","max_daily_loss_pct":null,"max_consecutive_losses":3,"require_stop_loss":true}',
      },
      [STRATEGY],
    );
    expect(values.symbol).toBe("ETH/USDT");
    expect(values.params["fast_period"]).toBe("5");
    expect(values.riskEnabled).toBe(true);
    const input = toBacktestInput(values, STRATEGY);
    expect(input.fill_timing).toBe("signal_close");
    expect(input.slippage_bps).toBe("7.5");
    expect(input.risk).toMatchObject({
      max_position_fraction: "0.5",
      max_daily_loss_pct: null,
      max_consecutive_losses: 3,
      require_stop_loss: true,
    });
    const plain = toBacktestInput(defaultBacktestValues(STRATEGY, NOW), STRATEGY);
    expect(plain.risk).toBeNull();
    expect(plain.fill_timing).toBe("next_open");
  });

  it("keeps USD-M settings when a Futures bot opens a backtest", () => {
    const values = applyBacktestPrefill(
      defaultBacktestValues(STRATEGY, NOW),
      {
        product: TradingProduct.LinearPerpetual,
        leverage: "7",
        allowShort: true,
        connectionId: "demo-connection",
        symbol: "ETH/USDT:USDT",
        initialCapital: "2500",
      },
      [STRATEGY],
    );

    expect(values.product).toBe(TradingProduct.LinearPerpetual);
    expect(values.exchange).toBe("binance-usdm");
    expect(values.symbol).toBe("ETH/USDT:USDT");
    expect(values.leverage).toBe("7");
    expect(values.allowShort).toBe(true);
    expect(values.connectionId).toBe("demo-connection");
    expect(values.initialCapital).toBe("2500");
  });
});
