import { useQuery } from "@tanstack/react-query";
import { QueryKey } from "@/lib/shared/api/query-keys";
import { Poll } from "@/lib/shared/polling";
import { getCapabilities, getStatus } from "@/lib/shared/system/system.api";

const CAPABILITIES_STALE_MS = 60_000;

export const useSystemStatus = () =>
  useQuery({
    queryKey: QueryKey.System.status(),
    queryFn: ({ signal }) => getStatus(signal),
    refetchInterval: Poll.Status,
  });

export const useCapabilities = () =>
  useQuery({
    queryKey: QueryKey.System.capabilities(),
    queryFn: ({ signal }) => getCapabilities(signal),
    staleTime: CAPABILITIES_STALE_MS,
  });
