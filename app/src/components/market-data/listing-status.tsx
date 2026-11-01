import { useQuery } from "@tanstack/react-query";
import { CalendarSearch } from "lucide-react";
import { EmptyState } from "@/components/shared/feedback/empty-state";
import { listListings } from "@/lib/market-data/market-data.api";
import { QueryKey } from "@/lib/shared/api/query-keys";
import { formatUtcDay } from "@/lib/shared/dates";
import { ListingStatus } from "@/lib/shared/enums";

type ListingStatusLineProps = { exchange: string; symbol: string };

export function ListingStatusLine({ exchange, symbol }: ListingStatusLineProps) {
  const query = useQuery({
    queryKey: QueryKey.MarketData.listings(exchange, symbol),
    queryFn: ({ signal }) => listListings(exchange, symbol, signal),
  });
  const listing = query.data?.[0];
  if (query.data === undefined) return null;
  if (listing === undefined) {
    return (
      <EmptyState
        icon={<CalendarSearch aria-hidden="true" />}
        title={`Sem histórico de listagem para ${symbol}`}
        description="O registro diário da exchange começa no dia em que o worker passou a gravá-lo."
        variant="naked"
        size="sm"
        className="items-start text-left"
      />
    );
  }
  if (listing.status === ListingStatus.Delisted) {
    return (
      <p className="text-sm font-medium text-destructive">
        {symbol} foi deslistado em {formatUtcDay(listing.delisted_at)} (visto desde{" "}
        {formatUtcDay(listing.first_seen)}).
      </p>
    );
  }
  return (
    <p className="text-sm text-muted-foreground">
      {symbol}{" "}
      {listing.status === ListingStatus.Inactive ? "está listado, mas suspenso" : "está listado"}{" "}
      (visto pela primeira vez em {formatUtcDay(listing.first_seen)}, última verificação{" "}
      {formatUtcDay(listing.last_seen)}).
    </p>
  );
}
