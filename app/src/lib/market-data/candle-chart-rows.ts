import type { Candle } from "@/lib/market-data/market-data.api";
import { formatUtcShort } from "@/lib/shared/dates";
import { downsample } from "@/lib/shared/equity-chart-rows";

export const closeChartRows = (candles: Candle[]) =>
  downsample(candles).map((candle) => ({
    label: formatUtcShort(candle.open_time),
    close: Number.parseFloat(candle.close),
  }));
