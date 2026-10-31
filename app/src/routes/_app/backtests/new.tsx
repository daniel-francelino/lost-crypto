import { createFileRoute } from "@tanstack/react-router";
import { BacktestFormPage } from "@/components/backtests/backtest-form-page";
import { Capability } from "@/lib/shared/capability";
import { requireCapability } from "@/lib/shared/route-guards";

export const Route = createFileRoute("/_app/backtests/new")({
  beforeLoad: () => requireCapability(Capability.BacktestsRun),
  component: BacktestFormPage,
});
