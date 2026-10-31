import { describe, expect, it } from "vitest";
import {
  buildStrategyParams,
  defaultParamValues,
  paramsFromRecord,
  validateParam,
} from "@/lib/shared/strategies/params";
import type { Strategy } from "@/lib/shared/strategies/strategies.api";

const STRATEGY: Strategy = {
  type_key: "ema_crossover",
  name: "EMA",
  description: "",
  parameters: [
    { name: "fast_period", type: "integer", default: 9, minimum: 2, description: "" },
    { name: "stop_loss_pct", type: "number", default: null, minimum: null, description: "" },
  ],
};
const [FAST, STOP] = STRATEGY.parameters as [
  Strategy["parameters"][number],
  Strategy["parameters"][number],
];

describe("strategy params", () => {
  it("starts from the defaults and leaves optional parameters empty", () => {
    expect(defaultParamValues(STRATEGY)).toEqual({ fast_period: "9", stop_loss_pct: "" });
  });

  it("reads the values of an existing bot over the defaults", () => {
    expect(paramsFromRecord(STRATEGY, { fast_period: 12, other: 1 })).toEqual({
      fast_period: "12",
      stop_loss_pct: "",
    });
  });

  it("validates type, integers and minimums", () => {
    expect(validateParam(FAST, "")).toBe("Informe um valor.");
    expect(validateParam(FAST, "abc")).toBe("Use um número.");
    expect(validateParam(FAST, "2.5")).toBe("Use um número inteiro.");
    expect(validateParam(FAST, "1")).toBe("O mínimo é 2.");
    expect(validateParam(FAST, "5")).toBeUndefined();
    expect(validateParam(STOP, "")).toBeUndefined();
    expect(validateParam(STOP, "3.5")).toBeUndefined();
  });

  it("builds numeric params, skipping the empty ones", () => {
    expect(buildStrategyParams(STRATEGY, { fast_period: "12", stop_loss_pct: "" })).toEqual({
      fast_period: 12,
    });
    expect(buildStrategyParams(STRATEGY, { fast_period: "9", stop_loss_pct: "2.5" })).toEqual({
      fast_period: 9,
      stop_loss_pct: 2.5,
    });
  });
});
