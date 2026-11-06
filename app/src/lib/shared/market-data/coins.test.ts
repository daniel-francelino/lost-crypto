import { describe, expect, it } from "vitest";
import {
  baseOf,
  coinIconSources,
  coinInitial,
  coinName,
  withCurrent,
} from "@/lib/shared/market-data/coins";

const PAIRS = [
  { symbol: "BTC/USDT", base: "BTC", quote: "USDT", name: "Bitcoin" },
  { symbol: "ETH/USDT", base: "ETH", quote: "USDT", name: "Ethereum" },
];

describe("coins", () => {
  it("finds the icon of a symbol by its base asset", () => {
    expect(baseOf("btc/usdt")).toBe("BTC");
    expect(coinIconSources("SOL/USDT")[0]).toBe("/coins/sol.svg");
    expect(coinInitial("doge/usdt")).toBe("D");
  });

  it("falls back to the exchange logos for coins without a bundled icon", () => {
    expect(coinIconSources("PEPE/USDT:USDT")).toEqual([
      "https://bin.bnbstatic.com/static/assets/logos/PEPE.png",
    ]);
    expect(coinIconSources("1000PEPE/USDT:USDT")).toEqual([
      "https://bin.bnbstatic.com/static/assets/logos/PEPE.png",
    ]);
    expect(coinIconSources("BTC/USDT:USDT")).toEqual([
      "/coins/btc.svg",
      "https://bin.bnbstatic.com/static/assets/logos/BTC.png",
    ]);
    expect(coinIconSources("")).toEqual([]);
  });

  it("names a known pair and falls back to the base asset", () => {
    expect(coinName("ETH/USDT", PAIRS)).toBe("Ethereum");
    expect(coinName("XYZ/USDT", PAIRS)).toBe("XYZ");
    expect(coinName("BTC/USDT", undefined)).toBe("BTC");
  });

  it("keeps a saved symbol that is no longer offered", () => {
    expect(withCurrent(PAIRS, "ETH/USDT")).toBe(PAIRS);
    expect(withCurrent(PAIRS, "")).toBe(PAIRS);
    expect(withCurrent(PAIRS, "ETH/BTC").map((pair) => pair.symbol)).toEqual([
      "BTC/USDT",
      "ETH/USDT",
      "ETH/BTC",
    ]);
  });
});
