import type { ExposureCurve } from "@/lib/backtests/backtests.api";

export type ExposureRow = {
  label: string;
  growth: number | null;
  drawdown: number;
  drawdownP95: number | null;
};

const PERCENT = 100;

const numeric = (value: string | null | undefined): number | null =>
  value === null || value === undefined ? null : Number.parseFloat(value);

export const exposureRows = (curve: ExposureCurve): ExposureRow[] =>
  curve.points.map((point) => ({
    label: `${Math.round(Number.parseFloat(point.fraction) * PERCENT)}%`,
    growth: point.growth === null ? null : Number.parseFloat(point.growth) * PERCENT,
    drawdown: Number.parseFloat(point.max_drawdown_pct),
    drawdownP95: numeric(point.bootstrap_p95),
  }));
