import { AreaChart } from "lost-ui/charts/area-chart";
import { Empty } from "lost-ui/data/empty";
import type { EquityPoint } from "@/lib/shared/analytics";
import { underwaterRows } from "@/lib/shared/equity-chart-rows";

const SERIES = [{ key: "drawdown", label: "Abaixo do pico (%)", color: "var(--destructive)" }];

type UnderwaterChartProps = { points: EquityPoint[] };

export function UnderwaterChart({ points }: UnderwaterChartProps) {
  if (points.length < 2) {
    return (
      <Empty title="Ainda sem curva" description="A curva aparece depois de alguns candles." />
    );
  }
  return (
    <figure className="space-y-2">
      <AreaChart
        data={underwaterRows(points)}
        xKey="label"
        series={SERIES}
        curve="linear"
        showYAxis
        className="h-36 w-full"
      />
      <figcaption className="text-xs text-muted-foreground">
        Quanto o capital estava abaixo do maior valor já atingido (0% = no pico). A largura de cada
        vale é o tempo até recuperar.
      </figcaption>
    </figure>
  );
}
