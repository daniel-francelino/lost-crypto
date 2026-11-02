import { useQuery } from "@tanstack/react-query";
import { QueryKey } from "@/lib/shared/api/query-keys";
import { getOverview } from "@/lib/shared/bots/overview.api";
import { Poll } from "@/lib/shared/polling";

export const useOverview = () =>
  useQuery({
    queryKey: QueryKey.Bots.overview(),
    queryFn: ({ signal }) => getOverview(signal),
    refetchInterval: Poll.Overview,
  });
