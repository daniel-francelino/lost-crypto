import { describe, expect, it } from "vitest";
import type { ExposureCurve } from "@/lib/backtests/backtests.api";
import { exposureRows } from "@/lib/backtests/exposure-chart-rows";

const curve = (points: ExposureCurve["points"]): ExposureCurve => ({
  run_id: "r",
  points,
  kelly_full: "2.5",
  kelly_half: "1.25",
  configured_fraction: "1",
  ruin_fraction: null,
  returns: 500,
  gaps: 0,
  bootstrap_returns: null,
  warnings: [],
});

describe("exposure chart rows", () => {
  it("labels each exposure in percent and scales the growth to percent per bar", () => {
    const rows = exposureRows(
      curve([
        { fraction: "0.25", growth: "0.0004", max_drawdown_pct: "5", bootstrap_p95: "9" },
        { fraction: "1", growth: "-0.001", max_drawdown_pct: "20", bootstrap_p95: null },
      ]),
    );
    expect(rows[0]).toMatchObject({ label: "25%", drawdown: 5, drawdownP95: 9 });
    expect(rows[0]?.growth).toBeCloseTo(0.04);
    expect(rows[1]).toMatchObject({ label: "100%", drawdown: 20, drawdownP95: null });
    expect(rows[1]?.growth).toBeCloseTo(-0.1);
  });

  it("keeps a ruin point without growth instead of inventing a number", () => {
    const rows = exposureRows(
      curve([{ fraction: "1", growth: null, max_drawdown_pct: "100", bootstrap_p50: null }]),
    );
    expect(rows[0]?.growth).toBeNull();
  });
});
