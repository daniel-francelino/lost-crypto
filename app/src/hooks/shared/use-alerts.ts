import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  type AlertFilters,
  getAlertSummary,
  listAlerts,
  markAlertRead,
  markAllAlertsRead,
} from "@/lib/shared/alerts/alerts.api";
import { QueryKey } from "@/lib/shared/api/query-keys";
import { Poll } from "@/lib/shared/polling";

export const useAlertSummary = () =>
  useQuery({
    queryKey: QueryKey.Alerts.summary(),
    queryFn: ({ signal }) => getAlertSummary(signal),
    refetchInterval: Poll.Status,
  });

export const useAlerts = (filters: AlertFilters) =>
  useQuery({
    queryKey: QueryKey.Alerts.list(
      filters.unreadOnly,
      filters.severity,
      filters.limit,
      filters.offset,
    ),
    queryFn: ({ signal }) => listAlerts(filters, signal),
    refetchInterval: Poll.Overview,
    placeholderData: keepPreviousData,
  });

export const useMarkAlertRead = () => {
  const client = useQueryClient();
  return useMutation({
    mutationFn: markAlertRead,
    onSuccess: () => client.invalidateQueries({ queryKey: QueryKey.Alerts.all() }),
  });
};

export const useMarkAllAlertsRead = () => {
  const client = useQueryClient();
  return useMutation({
    mutationFn: markAllAlertsRead,
    onSuccess: () => client.invalidateQueries({ queryKey: QueryKey.Alerts.all() }),
  });
};
