import { describe, expect, it } from "vitest";
import { CandleProblem, Unknown } from "@/lib/shared/enums";
import { candleProblemsText } from "@/lib/shared/market-data/quality-labels";
import { gapsOverLimit } from "@/lib/shared/market-data/gaps";

const RANGE = {
  start: "2026-01-01T00:00:00Z",
  end: "2026-01-10T00:00:00Z",
  expected: 200,
  present: 200,
  missing: 0,
  largest_gap: 0,
  gaps: [],
};

describe("data quality helpers", () => {
  it("names candle problems in Portuguese, unknown codes included", () => {
    expect(candleProblemsText([CandleProblem.HighBelowBody, Unknown])).toBe(
      "máxima abaixo da abertura/fechamento, problema desconhecido",
    );
  });

  it("applies the same gap limits as the API (1% missing or a hole over 24 h)", () => {
    expect(gapsOverLimit(RANGE, "1h")).toBe(false);
    expect(gapsOverLimit({ ...RANGE, missing: 2, present: 198, largest_gap: 1 }, "1h")).toBe(false);
    expect(gapsOverLimit({ ...RANGE, missing: 3, present: 197, largest_gap: 3 }, "1h")).toBe(true);
    expect(gapsOverLimit({ ...RANGE, missing: 1, present: 199, largest_gap: 1 }, "4h")).toBe(false);
    expect(gapsOverLimit({ ...RANGE, expected: 2000, missing: 7, largest_gap: 7 }, "4h")).toBe(
      true,
    );
    expect(gapsOverLimit(null, "1h")).toBe(false);
  });
});
