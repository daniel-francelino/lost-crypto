import { createFileRoute } from "@tanstack/react-router";
import { MarketDataPage } from "@/components/market-data/market-data-page";

export const Route = createFileRoute("/_app/market-data/")({
  component: MarketDataPage,
});
