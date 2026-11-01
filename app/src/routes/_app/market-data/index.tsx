import { createFileRoute } from "@tanstack/react-router";
import { MarketDataPage } from "@/components/market-data/market-data-page";
import { marketDataSearchSchema } from "@/lib/shared/market-data/search";

export const Route = createFileRoute("/_app/market-data/")({
  validateSearch: marketDataSearchSchema,
  component: MarketDataRoute,
});

function MarketDataRoute() {
  const search = Route.useSearch();
  return <MarketDataPage initial={search} />;
}
