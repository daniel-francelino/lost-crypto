import { describe, expect, it } from "vitest";
import {
  baseOf,
  coinIconSrc,
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
    expect(coinIconSrc("SOL/USDT")).toBe("/coins/sol.svg");
    expect(coinInitial("doge/usdt")).toBe("D");
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
