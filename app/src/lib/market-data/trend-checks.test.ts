import { describe, expect, it } from "vitest";
import { checkRows, checkText } from "@/lib/market-data/trend-checks";
import { Trend, TrendFrame } from "@/lib/shared/enums";
import type { TrendReading } from "@/lib/shared/market-data/registry.api";

const reading = (checks: TrendReading["checks"]): TrendReading => ({
  frame: TrendFrame.Day,
  bar_open_time: "2026-11-06T00:00:00Z",
  trend: Trend.Bearish,
  previous_trend: null,
  confirmed: false,
  checks,
  close: null,
  ema_fast: null,
  ema_slow: null,
  ema_distance_pct: null,
  adx: null,
  computed_at: "2026-11-06T00:00:10Z",
});

describe("trend checks", () => {
  it("says in words whether a check passed", () => {
    expect(checkText(true)).toBe("Passou");
    expect(checkText(false)).toBe("Não passou");
    expect(checkText(null)).toBe("Sem dados ainda");
    expect(checkText(undefined)).toBe("Sem dados ainda");
  });

  it("lists the four checks in a fixed order, whatever order the API sent", () => {
    const rows = checkRows(reading({ structure: true, adx: false, distance: true, slope: null }));
    expect(rows).toEqual([
      { label: "Distância entre as EMAs", text: "Passou" },
      { label: "Inclinação da EMA lenta", text: "Sem dados ainda" },
      { label: "Força da tendência (ADX)", text: "Não passou" },
      { label: "Topos e fundos", text: "Passou" },
    ]);
  });

  it("has nothing to list for a sideways reading", () => {
    expect(checkRows(reading({}))).toEqual([]);
  });
});
