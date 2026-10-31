import { createFileRoute } from "@tanstack/react-router";
import { BacktestDetailPage } from "@/components/backtests/backtest-detail-page";

export const Route = createFileRoute("/_app/backtests/$runId/")({
  component: BacktestDetailRoute,
});

function BacktestDetailRoute() {
  const { runId } = Route.useParams();
  return <BacktestDetailPage runId={runId} />;
}
