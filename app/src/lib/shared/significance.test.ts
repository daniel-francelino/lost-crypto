import { describe, expect, it } from "vitest";
import { significanceHint, significanceValue } from "@/lib/shared/significance";

describe("significance text", () => {
  it("shows the strictest table level in Portuguese decimal format", () => {
    expect(significanceValue({ sharpe_t_stat: "2.5", significance_p: "0.01" })).toBe("p < 0,01");
  });

  it("says so when the statistic does not reach the loosest level", () => {
    expect(significanceValue({ sharpe_t_stat: "0.4", significance_p: null })).toBe(
      "não distinguível de acaso",
    );
  });

  it("is n/a for old results and short samples", () => {
    expect(significanceValue({})).toBe("n/d");
    expect(significanceValue({ sharpe_t_stat: null, significance_p: null })).toBe("n/d");
    expect(significanceHint({})).toContain("Amostra curta");
  });

  it("always carries the p-value disclaimer", () => {
    expect(significanceHint({ sharpe_t_stat: "2.5", significance_p: "0.01" })).toContain(
      "Valor-p não é a chance",
    );
  });
});
