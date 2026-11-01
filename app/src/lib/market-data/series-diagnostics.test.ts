import { describe, expect, it } from "vitest";
import {
  hurstText,
  sampleEveryValue,
  varianceRatioText,
} from "@/lib/market-data/series-diagnostics";

describe("series diagnostics text", () => {
  it("reads the Hurst exponent around one half", () => {
    expect(hurstText("0.32")).toContain("reverter");
    expect(hurstText("0.5")).toContain("passeio aleatório");
    expect(hurstText("0.62")).toContain("tendência");
    expect(hurstText(null)).toContain("sem estimativa");
  });

  it("reads the variance ratio around one", () => {
    expect(varianceRatioText("0.7", 4)).toContain("abaixo de 1");
    expect(varianceRatioText("1.02", 2)).toContain("perto de 1");
    expect(varianceRatioText("1.5", 8)).toContain("acima de 1");
    expect(varianceRatioText("0.7", 4)).toContain("lag 4");
  });

  it("falls back to every candle on a bad sampling step", () => {
    expect(sampleEveryValue("4")).toBe(4);
    expect(sampleEveryValue("0")).toBe(1);
    expect(sampleEveryValue("abc")).toBe(1);
    expect(sampleEveryValue("5000")).toBe(1);
  });
});
