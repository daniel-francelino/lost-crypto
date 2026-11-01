import type { SupportedPair } from "@/lib/shared/market-data/pairs.api";

export const baseOf = (symbol: string): string => symbol.split("/")[0]?.trim().toUpperCase() ?? "";

export const coinIconSrc = (symbol: string): string => `/coins/${baseOf(symbol).toLowerCase()}.svg`;

export const coinInitial = (symbol: string): string => baseOf(symbol).slice(0, 1);

export const coinName = (symbol: string, pairs: readonly SupportedPair[] | undefined): string =>
  pairs?.find((pair) => pair.symbol === symbol.trim().toUpperCase())?.name ?? baseOf(symbol);

export const withCurrent = (
  pairs: readonly SupportedPair[],
  current: string,
): readonly SupportedPair[] => {
  const symbol = current.trim().toUpperCase();
  const known = symbol === "" || pairs.some((pair) => pair.symbol === symbol);
  const [base = "", quote = ""] = symbol.split("/");
  return known ? pairs : [...pairs, { symbol, base, quote, name: base }];
};
