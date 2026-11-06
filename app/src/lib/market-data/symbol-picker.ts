import { ExchangeId, TradingProduct } from "@/lib/shared/enums";
import type { Market } from "@/lib/shared/market-data/markets.api";
import type { RegisteredSymbol } from "@/lib/shared/market-data/registry.api";

export const PICKER_LIMIT = 80;
const QUOTE = "USDT";

export type PickerRow = { symbol: string; base: string; registered: boolean };

export type PickerView = { rows: PickerRow[]; total: number };

const isOffered = (market: Market, exchange: string): boolean => {
  if (exchange === ExchangeId.BinanceUsdm) {
    return market.product === TradingProduct.LinearPerpetual && market.settlement === QUOTE;
  }
  return market.product === TradingProduct.Spot && market.quote === QUOTE;
};

const baseOfMarket = (market: Market): string =>
  market.base ?? market.symbol.split("/")[0] ?? market.symbol;

export const pickerView = (
  markets: readonly Market[],
  registered: readonly RegisteredSymbol[],
  exchange: string,
  query: string,
): PickerView => {
  const taken = new Set(
    registered.filter((item) => item.exchange === exchange && item.active).map((i) => i.symbol),
  );
  const needle = query.trim().toUpperCase();
  const matches = markets
    .filter((market) => isOffered(market, exchange))
    .map((market) => ({
      symbol: market.symbol,
      base: baseOfMarket(market),
      registered: taken.has(market.symbol),
    }))
    .filter((row) => needle === "" || row.base.toUpperCase().includes(needle))
    .sort((a, b) => a.base.localeCompare(b.base));
  return { rows: matches.slice(0, PICKER_LIMIT), total: matches.length };
};

export const toggleSelection = (selected: readonly string[], symbol: string): string[] =>
  selected.includes(symbol) ? selected.filter((item) => item !== symbol) : [...selected, symbol];
