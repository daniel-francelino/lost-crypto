import { useQuery } from "@tanstack/react-query";
import { ConnectionStatus } from "@/lib/shared/enums";
import { QueryKey } from "@/lib/shared/api/query-keys";
import { listConnections } from "@/lib/shared/exchanges/connections.api";
import { Poll } from "@/lib/shared/polling";
import { listStrategies } from "@/lib/shared/strategies/strategies.api";

const CATALOG_STALE_MS = 5 * 60_000;

export const useStrategies = () =>
  useQuery({
    queryKey: QueryKey.Strategies.all(),
    queryFn: ({ signal }) => listStrategies(signal),
    staleTime: CATALOG_STALE_MS,
  });

export const useConnections = (pollWhilePending = false) =>
  useQuery({
    queryKey: QueryKey.Exchanges.connections(),
    queryFn: ({ signal }) => listConnections(signal),
    refetchInterval: (query) =>
      pollWhilePending && query.state.data?.some((item) => item.status === ConnectionStatus.Pending)
        ? Poll.Connections
        : false,
  });
