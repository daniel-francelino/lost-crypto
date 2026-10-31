import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { ComparePage } from "@/components/backtests/compare-page";

export const Route = createFileRoute("/_app/backtests/compare")({
  validateSearch: z.object({ ids: z.array(z.string()).catch([]) }),
  component: CompareRoute,
});

function CompareRoute() {
  const { ids } = Route.useSearch();
  return <ComparePage ids={ids} />;
}
