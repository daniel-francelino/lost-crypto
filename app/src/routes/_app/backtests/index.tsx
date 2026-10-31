import { createFileRoute } from "@tanstack/react-router";
import { BacktestsPage } from "@/components/backtests/backtests-page";

export const Route = createFileRoute("/_app/backtests/")({
  component: BacktestsPage,
});
