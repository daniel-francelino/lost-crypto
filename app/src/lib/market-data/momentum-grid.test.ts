import { describe, expect, it } from "vitest";
import type { MomentumGrid } from "@/lib/market-data/market-data.api";
import {
  cellAt,
  cellText,
  gridError,
  holdingsOf,
  lookbacksOf,
  parseLags,
} from "@/lib/market-data/momentum-grid";

const grid = (cells: MomentumGrid["cells"]): MomentumGrid =>
  ({
    cells,
    alpha_corrected: "0.0125",
    critical_z: "2.5",
    candles: 500,
    gaps: 0,
    warning: "w",
  }) as MomentumGrid;

const cell = (lookback: number, holding: number, over = {}): MomentumGrid["cells"][number] => ({
  lookback,
  holding,
  n: 40,
  correlation: "0.21",
  z_stat: "2.8",
  significant_corrected: true,
  reason: null,
  ...over,
});

describe("lag lists", () => {
  it("parses whole numbers separated by commas", () => {
    expect(parseLags("1, 5,10")).toEqual({ values: [1, 5, 10], error: null });
  });

  it("refuses empty, zero, decimals and text", () => {
    expect(parseLags("").error).toContain("ao menos um");
    expect(parseLags("0, 5").error).toContain("inteiros");
    expect(parseLags("1.5").error).toContain("inteiros");
    expect(parseLags("a").error).toContain("inteiros");
  });

  it("limits the number of cells of the whole grid", () => {
    const eleven = parseLags("1,2,3,4,5,6,7,8,9,10,11");
    expect(gridError(eleven, eleven)).toContain("121");
    expect(gridError(parseLags("1,5"), parseLags("1,5,10"))).toBeNull();
    expect(gridError(parseLags(""), parseLags("1"))).toContain("ao menos um");
  });
});

describe("grid cells", () => {
  it("writes the number, the sample and the verdict in words", () => {
    const text = cellText(cell(1, 1));
    expect(text).toContain("r = 0,21");
    expect(text).toContain("n = 40");
    expect(text).toContain("passa a 5% com correção");
    expect(cellText(cell(1, 1, { significant_corrected: false }))).toContain("não passa");
  });

  it("shows a dash when there is no correlation", () => {
    expect(cellText(cell(1, 1, { correlation: null }))).toBe("—");
  });

  it("finds the axes and a cell by its lags", () => {
    const g = grid([cell(1, 1), cell(1, 5), cell(5, 1), cell(5, 5)]);
    expect(lookbacksOf(g)).toEqual([1, 5]);
    expect(holdingsOf(g)).toEqual([1, 5]);
    expect(cellAt(g, 5, 1)?.lookback).toBe(5);
    expect(cellAt(g, 9, 9)).toBeUndefined();
  });
});
