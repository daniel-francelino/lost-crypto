import { useQuery } from "@tanstack/react-query";
import { QueryKey } from "@/lib/shared/api/query-keys";
import { dayEndUtcIso, dayStartUtcIso } from "@/lib/shared/dates";
import { getCoverage } from "@/lib/shared/market-data/coverage.api";

export type RangeParams = {
  exchange: string;
  symbol: string;
  timeframe: string;
  start: string;
  end: string;
};

export const useRangeCoverage = ({ exchange, symbol, timeframe, start, end }: RangeParams) =>
  useQuery({
    queryKey: QueryKey.MarketData.coverage(exchange, symbol, timeframe, start, end),
    queryFn: ({ signal }) =>
      getCoverage(
        {
          exchange,
          symbol: symbol.trim().toUpperCase(),
          timeframe,
          start: dayStartUtcIso(start),
          end: dayEndUtcIso(end),
        },
        signal,
      ),
    enabled: symbol.trim() !== "",
  });
