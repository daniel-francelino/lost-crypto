import { AreaChart } from "lost-ui/charts/area-chart";
import { EmptyState as Empty } from "@/components/shared/feedback/empty-state";
import type { EquityPoint } from "@/lib/shared/analytics";
import { equityChartRows } from "@/lib/shared/equity-chart-rows";

const SERIES = [{ key: "equity", label: "Capital" }];

type EquityChartProps = { points: EquityPoint[]; summary: string };

export function EquityChart({ points, summary }: EquityChartProps) {
  if (points.length < 2) {
    return (
      <Empty title="Ainda sem curva" description="A curva aparece depois de alguns candles." />
    );
  }
  return (
    <figure className="space-y-2">
      <AreaChart
        data={equityChartRows(points)}
        xKey="label"
        series={SERIES}
        curve="monotone"
        showYAxis
        gradient
        className="h-64 w-full"
      />
      <figcaption className="text-xs text-muted-foreground">{summary}</figcaption>
    </figure>
  );
}
