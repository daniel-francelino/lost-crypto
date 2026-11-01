import { describe, expect, it } from "vitest";
import type { RealizedVsBacktest } from "@/lib/bots/bots.api";
import {
  ComparisonVerdict,
  reasonText,
  verdictOf,
  verdictText,
} from "@/lib/bots/backtest-comparison";

const BASE: RealizedVsBacktest = {
  run_id: "r1",
  run_created_at: "2026-11-01T00:00:00Z",
  realized: { sharpe: "1.2", return_periods: 120, days: "5" },
  backtest: { sharpe: "2.0" },
  ratio: "0.6",
  min_periods: 30,
  chan_min_ratio: "0.5",
  reason: null,
};

describe("realized vs backtest verdict", () => {
  it("splits at Chan's one half", () => {
    expect(verdictOf({ ...BASE, ratio: "0.6" })).toBe(ComparisonVerdict.Acceptable);
    expect(verdictOf({ ...BASE, ratio: "0.5" })).toBe(ComparisonVerdict.Acceptable);
    expect(verdictOf({ ...BASE, ratio: "0.49" })).toBe(ComparisonVerdict.Below);
  });

  it("has no verdict without a ratio and explains why in Portuguese", () => {
    const short = { ...BASE, ratio: null, reason: "short live sample: no realized Sharpe yet" };
    expect(verdictOf(short)).toBe(ComparisonVerdict.Unavailable);
    expect(verdictText(short)).toContain("Amostra real ainda curta");
    expect(reasonText("a reason the UI does not know")).toBe("a reason the UI does not know");
    expect(reasonText(null)).toBeNull();
  });

  it("never presents the half as a rule", () => {
    expect(verdictText({ ...BASE, ratio: "0.3" })).toContain("não norma");
  });
});
