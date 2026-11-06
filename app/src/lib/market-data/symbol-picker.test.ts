import { describe, expect, it } from "vitest";
import { PICKER_LIMIT, pickerView, toggleSelection } from "@/lib/market-data/symbol-picker";
import { ExchangeId } from "@/lib/shared/enums";
import type { Market } from "@/lib/shared/market-data/markets.api";
import type { RegisteredSymbol } from "@/lib/shared/market-data/registry.api";

const market = (symbol: string, overrides: Partial<Market> = {}): Market => ({
  exchange: ExchangeId.BinanceUsdm,
  symbol,
  base: symbol.split("/")[0] ?? null,
  quote: "USDT",
  settlement: "USDT",
  product: "linear_perpetual",
  contract_size: "1",
  active: true,
  ...overrides,
});

const registered = (
  symbol: string,
  active = true,
  exchange = "binance-usdm",
): RegisteredSymbol => ({
  id: symbol,
  exchange,
  symbol,
  active,
  created_at: "2026-11-06T00:00:00Z",
});

const MARKETS = [
  market("SOL/USDT:USDT"),
  market("BTC/USDT:USDT"),
  market("ETH/USDT:USDT"),
  market("BTC/USDC:USDC", { quote: "USDC", settlement: "USDC" }),
  market("BTC/USDT", { product: "spot", settlement: null }),
];

describe("pickerView", () => {
  it("offers only the USDT perpetuals of Futures, sorted by coin", () => {
    const view = pickerView(MARKETS, [], ExchangeId.BinanceUsdm, "");
    expect(view.rows.map((row) => row.symbol)).toEqual([
      "BTC/USDT:USDT",
      "ETH/USDT:USDT",
      "SOL/USDT:USDT",
    ]);
    expect(view.total).toBe(3);
  });

  it("offers only the USDT spot pairs of Spot", () => {
    const view = pickerView(MARKETS, [], ExchangeId.Binance, "");
    expect(view.rows.map((row) => row.symbol)).toEqual(["BTC/USDT"]);
  });

  it("marks the pairs that are already registered and active", () => {
    const view = pickerView(
      MARKETS,
      [registered("BTC/USDT:USDT"), registered("ETH/USDT:USDT", false)],
      ExchangeId.BinanceUsdm,
      "",
    );
    expect(view.rows.map((row) => [row.base, row.registered])).toEqual([
      ["BTC", true],
      ["ETH", false],
      ["SOL", false],
    ]);
  });

  it("does not count a registration of another exchange", () => {
    const view = pickerView(
      MARKETS,
      [registered("BTC/USDT", true, ExchangeId.Binance)],
      ExchangeId.BinanceUsdm,
      "",
    );
    expect(view.rows.every((row) => !row.registered)).toBe(true);
  });

  it("searches by coin, ignoring case and spaces", () => {
    expect(
      pickerView(MARKETS, [], ExchangeId.BinanceUsdm, "  so ").rows.map((row) => row.base),
    ).toEqual(["SOL"]);
    expect(pickerView(MARKETS, [], ExchangeId.BinanceUsdm, "zzz")).toEqual({ rows: [], total: 0 });
  });

  it("shows at most the limit and still reports the total", () => {
    const many = Array.from({ length: PICKER_LIMIT + 20 }, (_, index) =>
      market(`C${String(index).padStart(3, "0")}/USDT:USDT`),
    );
    const view = pickerView(many, [], ExchangeId.BinanceUsdm, "");
    expect(view.rows).toHaveLength(PICKER_LIMIT);
    expect(view.total).toBe(PICKER_LIMIT + 20);
  });
});

describe("toggleSelection", () => {
  it("adds and removes a symbol without mutating the list", () => {
    const start = ["BTC/USDT:USDT"];
    expect(toggleSelection(start, "ETH/USDT:USDT")).toEqual(["BTC/USDT:USDT", "ETH/USDT:USDT"]);
    expect(toggleSelection(start, "BTC/USDT:USDT")).toEqual([]);
    expect(start).toEqual(["BTC/USDT:USDT"]);
  });
});
