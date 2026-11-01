import { createFileRoute } from "@tanstack/react-router";
import { BacktestFormPage } from "@/components/backtests/backtest-form-page";
import { backtestPrefillSchema } from "@/lib/shared/backtest-prefill";
import { Capability } from "@/lib/shared/capability";
import { requireCapability } from "@/lib/shared/route-guards";

export const Route = createFileRoute("/_app/backtests/new")({
  validateSearch: backtestPrefillSchema,
  beforeLoad: () => requireCapability(Capability.BacktestsRun),
  component: NewBacktestRoute,
});

function NewBacktestRoute() {
  return <BacktestFormPage prefill={Route.useSearch()} />;
}
