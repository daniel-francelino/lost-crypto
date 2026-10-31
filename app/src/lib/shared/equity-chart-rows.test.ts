import { describe, expect, it } from "vitest";
import {
  compareChartRows,
  downsample,
  downsampleExtremes,
  equityChartRows,
  underwaterRows,
} from "@/lib/shared/equity-chart-rows";

describe("equity chart rows", () => {
  it("turns decimal strings into numbers for drawing only", () => {
    const rows = equityChartRows([{ time: "2026-10-31T00:00:00Z", equity: "1000.50" }]);
    expect(rows[0]?.equity).toBe(1000.5);
    expect(rows[0]?.time).toBe("2026-10-31T00:00:00Z");
  });

  it("keeps the first and last points when a long series is thinned", () => {
    const points = Array.from({ length: 5000 }, (_, index) => index);
    const thinned = downsample(points, 1000);
    expect(thinned.length).toBeLessThanOrEqual(1001);
    expect(thinned[0]).toBe(0);
    expect(thinned.at(-1)).toBe(4999);
    expect(downsample([1, 2, 3], 1000)).toEqual([1, 2, 3]);
  });

  it("merges several curves onto one time axis", () => {
    const rows = compareChartRows([
      { id: "a", points: [{ time: "2026-10-31T00:00:00Z", equity: "1" }] },
      {
        id: "b",
        points: [
          { time: "2026-10-31T00:00:00Z", equity: "2" },
          { time: "2026-10-31T01:00:00Z", equity: "3" },
        ],
      },
    ]);
    expect(rows).toHaveLength(2);
    expect(rows[0]).toMatchObject({ a: 1, b: 2 });
    expect(rows[1]).toMatchObject({ b: 3 });
  });

  it("keeps the deepest point when a long series is thinned", () => {
    const values = Array.from({ length: 5000 }, (_, index) => (index === 3333 ? -50 : index % 7));
    const thinned = downsampleExtremes(values, (value) => value, 1000);
    expect(thinned.length).toBeLessThanOrEqual(1002);
    expect(Math.min(...thinned)).toBe(-50);
    expect(thinned[0]).toBe(values[0]);
    expect(thinned.at(-1)).toBe(values.at(-1));
  });

  it("draws the equity trough even after thinning", () => {
    const points = Array.from({ length: 3000 }, (_, index) => ({
      time: new Date(Date.UTC(2026, 0, 1, index)).toISOString(),
      equity: index === 1777 ? "400" : "1000",
    }));
    expect(Math.min(...equityChartRows(points).map((row) => row.equity))).toBe(400);
  });

  it("computes the distance below the running peak in percent", () => {
    const rows = underwaterRows([
      { time: "2026-10-31T00:00:00Z", equity: "100" },
      { time: "2026-10-31T01:00:00Z", equity: "120" },
      { time: "2026-10-31T02:00:00Z", equity: "90" },
      { time: "2026-10-31T03:00:00Z", equity: "130" },
    ]);
    expect(rows.map((row) => row.drawdown)).toEqual([0, 0, -25, 0]);
  });
});
