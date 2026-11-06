import type { SupportedPair } from "@/lib/shared/market-data/pairs.api";

export const baseOf = (symbol: string): string => symbol.split("/")[0]?.trim().toUpperCase() ?? "";

const LOCAL_ICONS = new Set([
  "ada",
  "atom",
  "avax",
  "bnb",
  "btc",
  "doge",
  "dot",
  "etc",
  "eth",
  "link",
  "ltc",
  "sol",
  "trx",
  "xrp",
]);
const REMOTE_ICONS = "https://bin.bnbstatic.com/static/assets/logos";
const MULTIPLIER_PREFIX = /^(?:1000000|1000|1M)(?=[A-Z])/;

export const coinIconSources = (symbol: string): string[] => {
  const base = baseOf(symbol).replace(MULTIPLIER_PREFIX, "");
  if (base === "") return [];
  const local = LOCAL_ICONS.has(base.toLowerCase()) ? [`/coins/${base.toLowerCase()}.svg`] : [];
  return [...local, `${REMOTE_ICONS}/${base}.png`];
};

export const quoteOf = (symbol: string): string =>
  symbol.split("/")[1]?.split(":")[0]?.trim().toUpperCase() ?? "";

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
