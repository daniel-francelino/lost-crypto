import { describe, expect, it } from "vitest";
import { QueryKey } from "@/lib/shared/api/query-keys";

describe("market data query keys", () => {
  it("isolates Spot and USD-M series for the same base asset", () => {
    const spot = QueryKey.MarketData.candles(
      "binance",
      "BTC/USDT",
      "1h",
      "2025-01-01",
      "2025-01-02",
    );
    const perpetual = QueryKey.MarketData.candles(
      "binance-usdm",
      "BTC/USDT:USDT",
      "1h",
      "2025-01-01",
      "2025-01-02",
    );

    expect(spot).not.toEqual(perpetual);
  });

  it("keeps the market catalog cache separate by exchange", () => {
    expect(QueryKey.MarketData.catalog("binance")).not.toEqual(
      QueryKey.MarketData.catalog("binance-usdm"),
    );
  });
});
