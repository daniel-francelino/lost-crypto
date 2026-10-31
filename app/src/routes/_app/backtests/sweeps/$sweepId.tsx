import { createFileRoute } from "@tanstack/react-router";
import { SweepPage } from "@/components/backtests/sweep-page";

export const Route = createFileRoute("/_app/backtests/sweeps/$sweepId")({
  component: SweepRoute,
});

function SweepRoute() {
  const { sweepId } = Route.useParams();
  return <SweepPage sweepId={sweepId} />;
}
