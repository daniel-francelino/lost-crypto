import { createFileRoute } from "@tanstack/react-router";
import { SymbolsPage } from "@/components/market-data/symbols-page";

export const Route = createFileRoute("/_app/symbols/")({
  component: SymbolsPage,
});
