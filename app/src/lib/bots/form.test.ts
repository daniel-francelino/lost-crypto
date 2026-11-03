import { describe, expect, it } from "vitest";
import { defaultFormValues, futuresEntryEstimate, toBotInput } from "@/lib/bots/form";
import { decimalError, integerError, symbolError } from "@/lib/shared/validators";
import type { Strategy } from "@/lib/shared/strategies/strategies.api";
import { ExecutionMode, MarginMode, TradingProduct } from "@/lib/shared/enums";

const STRATEGY: Strategy = {
  type_key: "ema_crossover",
  name: "EMA",
  description: "",
  parameters: [{ name: "fast_period", type: "integer", default: 9, minimum: 2, description: "" }],
};

describe("bot form", () => {
  it("starts with safe paper defaults", () => {
    const values = defaultFormValues(STRATEGY);
    expect(values.mode).toBe("paper");
    expect(values.strategyType).toBe("ema_crossover");
    expect(values.params).toEqual({ fast_period: "9" });
  });

  it("builds the request with money as strings and empty optionals as null", () => {
    const input = toBotInput(
      {
        ...defaultFormValues(STRATEGY),
        name: "  ema-btc  ",
        symbol: "btc/usdt",
        connectionId: "x",
      },
      STRATEGY,
    );
    expect(input.name).toBe("ema-btc");
    expect(input.symbol).toBe("BTC/USDT");
    expect(input.initial_capital).toBe("1000");
    expect(input.fee_rate).toBeNull();
    expect(input.connection_id).toBeNull();
    expect(input.strategy_params).toEqual({ fast_period: 9 });
    expect(input.risk).toMatchObject({
      max_position_fraction: "1",
      max_daily_loss_pct: "10",
      max_drawdown_pct: null,
      max_consecutive_losses: null,
      max_candle_range_pct: "25",
      max_close_jump_pct: null,
    });
  });

  it("sends the close-jump limit only when filled, and reads it back from a bot", () => {
    const filled = { ...defaultFormValues(STRATEGY), maxCloseJumpPct: "7.5" };
    expect(toBotInput(filled, STRATEGY).risk.max_close_jump_pct).toBe("7.5");
    expect(
      toBotInput({ ...filled, maxCloseJumpPct: "  " }, STRATEGY).risk.max_close_jump_pct,
    ).toBeNull();
  });

  it("keeps the connection only for exchange modes", () => {
    const base = { ...defaultFormValues(STRATEGY), connectionId: "abc", maxConsecutiveLosses: "3" };
    expect(toBotInput({ ...base, mode: "testnet" }, STRATEGY).connection_id).toBe("abc");
    expect(toBotInput({ ...base, mode: "testnet" }, STRATEGY).risk.max_consecutive_losses).toBe(3);
  });

  it("keeps the Demo connection for isolated Futures paper and serializes its risk fields", () => {
    const input = toBotInput(
      {
        ...defaultFormValues(STRATEGY),
        exchange: "binance-usdm",
        product: TradingProduct.LinearPerpetual,
        symbol: "BTC/USDT:USDT",
        leverage: "10",
        allowShort: true,
        connectionId: "demo-account",
        minLiquidationDistancePct: "12",
      },
      STRATEGY,
    );

    expect(input).toMatchObject({
      exchange: "binance-usdm",
      product: TradingProduct.LinearPerpetual,
      mode: ExecutionMode.Paper,
      leverage: 10,
      margin_mode: MarginMode.Isolated,
      allow_short: true,
      connection_id: "demo-account",
      risk: { min_liquidation_distance_pct: "12" },
    });
  });

  it("estimates Futures notional and collateral with leverage, fee and the order cap", () => {
    const values = {
      ...defaultFormValues(STRATEGY),
      product: TradingProduct.LinearPerpetual,
      leverage: "5",
      initialCapital: "1000",
      maxPositionFraction: "0.5",
    };
    expect(futuresEntryEstimate(values)).toEqual({
      notional: expect.stringMatching(/^2493\.765586/),
      collateral: "500",
    });
    expect(futuresEntryEstimate({ ...values, maxOrderNotional: "400" })).toEqual({
      notional: "400",
      collateral: "80.2",
    });
    expect(futuresEntryEstimate({ ...values, leverage: "10.5" })).toBeNull();
  });

  it("validates decimals, integers and symbols", () => {
    expect(decimalError("12.5", true)).toBeUndefined();
    expect(decimalError("12,5", true)).toContain("ponto decimal");
    expect(decimalError("", true)).toBe("Informe um valor.");
    expect(decimalError("", false)).toBeUndefined();
    expect(integerError("3")).toBeUndefined();
    expect(integerError("3.5")).toBe("Use um número inteiro.");
    expect(symbolError("btc/usdt")).toBeUndefined();
    expect(symbolError("BTCUSDT")).toContain("BASE/COTAÇÃO");
  });
});
