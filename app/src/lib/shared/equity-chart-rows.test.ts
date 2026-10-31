import { describe, expect, it } from "vitest";
import { compareChartRows, downsample, equityChartRows } from "@/lib/shared/equity-chart-rows";

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
});
