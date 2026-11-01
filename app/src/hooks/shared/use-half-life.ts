import { useQuery } from "@tanstack/react-query";
import { getHalfLife } from "@/lib/shared/market-data/half-life.api";
import { QueryKey } from "@/lib/shared/api/query-keys";

type HalfLifeRange = {
  exchange: string;
  symbol: string;
  timeframe: string;
  start: string;
  end: string;
  sampleEvery?: number;
  enabled?: boolean;
};

export const useHalfLife = ({
  exchange,
  symbol,
  timeframe,
  start,
  end,
  sampleEvery = 1,
  enabled = true,
}: HalfLifeRange) =>
  useQuery({
    queryKey: QueryKey.MarketData.halfLife(exchange, symbol, timeframe, start, end, sampleEvery),
    queryFn: ({ signal }) =>
      getHalfLife(
        {
          exchange,
          symbol,
          timeframe,
          start: `${start}T00:00:00Z`,
          end: `${end}T23:59:59Z`,
          sample_every: sampleEvery,
        },
        signal,
      ),
    enabled: enabled && start < end,
  });
