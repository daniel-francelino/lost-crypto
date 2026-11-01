import { describe, expect, it } from "vitest";
import { matchedText, unavailableText } from "@/lib/backtests/significance";

describe("random entries text", () => {
  it("states how many simulations matched, with the denominator", () => {
    const text = matchedText({
      available: true,
      as_good_or_better: 12,
      simulations: 1000,
      fraction: "0.012",
    });
    expect(text).toContain("12 de 1.000");
    expect(text).toContain("igualaram ou superaram");
  });

  it("has no matched text when the test was not computed", () => {
    expect(matchedText({ available: false, reason: "x" })).toBeNull();
    expect(matchedText({ available: true })).toBeNull();
  });

  it("translates the known reason and keeps an unknown one visible", () => {
    expect(unavailableText("fewer than 10 completed trades: the test needs more")).toContain(
      "Menos de 10 operações",
    );
    expect(unavailableText("something else")).toBe("something else");
    expect(unavailableText(null)).toBe("Teste não calculado.");
  });
});
