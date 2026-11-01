import { describe, expect, it } from "vitest";
import {
  breaksCrossing,
  registeredAfter,
  stretchesOf,
} from "@/lib/shared/market-data/regime-breaks";
import type { RegimeBreak } from "@/lib/shared/market-data/regime-breaks.api";

const item = (name: string, day: string, over: Partial<RegimeBreak> = {}): RegimeBreak => ({
  id: name,
  name,
  occurred_at: `${day}T00:00:00Z`,
  exchange: null,
  symbol: null,
  note: null,
  created_by: "admin",
  created_at: "2026-01-01T00:00:00Z",
  ...over,
});

const BREAKS = [item("crash-2022", "2022-05-12"), item("etf", "2024-01-10")];

describe("regime breaks inside a date range", () => {
  it("lists only the breaks strictly after the start and up to the end", () => {
    expect(breaksCrossing(BREAKS, "binance", "BTC/USDT", "2022-01-01", "2024-12-31")).toHaveLength(
      2,
    );
    expect(breaksCrossing(BREAKS, "binance", "BTC/USDT", "2022-05-12", "2024-12-31")).toHaveLength(
      1,
    );
    expect(breaksCrossing(BREAKS, "binance", "BTC/USDT", "2022-05-13", "2022-12-31")).toHaveLength(
      0,
    );
    expect(breaksCrossing(BREAKS, "binance", "BTC/USDT", "2022-01-01", "2022-05-12")).toHaveLength(
      1,
    );
  });

  it("respects the scope of a break and keeps global ones", () => {
    const scoped = [
      item("eth-only", "2023-03-01", { symbol: "ETH/USDT" }),
      item("global", "2023-04-01"),
      item("other-exchange", "2023-05-01", { exchange: "kraken" }),
    ];
    const names = breaksCrossing(scoped, "binance", "BTC/USDT", "2023-01-01", "2023-12-31").map(
      (found) => found.name,
    );
    expect(names).toEqual(["global"]);
  });

  it("returns them in date order", () => {
    const names = breaksCrossing(
      [item("b", "2023-06-01"), item("a", "2023-02-01")],
      "binance",
      "BTC/USDT",
      "2023-01-01",
      "2023-12-31",
    ).map((found) => found.name);
    expect(names).toEqual(["a", "b"]);
  });
});

describe("stretches between breaks", () => {
  it("cuts the range at each break, ending the stretch the day before it", () => {
    const crossing = breaksCrossing(BREAKS, "binance", "BTC/USDT", "2022-01-01", "2024-12-31");
    expect(stretchesOf(crossing, "2022-01-01", "2024-12-31")).toEqual([
      { start: "2022-01-01", end: "2022-05-11", label: "antes de crash-2022" },
      { start: "2022-05-12", end: "2024-01-09", label: "entre crash-2022 e etf" },
      { start: "2024-01-10", end: "2024-12-31", label: "depois de etf" },
    ]);
  });

  it("is a single stretch when nothing crosses", () => {
    expect(stretchesOf([], "2023-01-01", "2023-02-01")).toHaveLength(1);
  });
});

describe("registered after the run", () => {
  it("compares the registration time with the run", () => {
    expect(registeredAfter("2026-02-01T00:00:00Z", "2026-01-01T00:00:00Z")).toBe(true);
    expect(registeredAfter("2025-12-01T00:00:00Z", "2026-01-01T00:00:00Z")).toBe(false);
  });
});
