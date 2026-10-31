import type { Strategy, StrategyParameter } from "@/lib/shared/strategies/strategies.api";

const INTEGER_TYPE = "integer";
const NUMBER_PATTERN = /^-?\d+(\.\d+)?$/;
const NUMBER = NUMBER_PATTERN;

export type ParamValues = Record<string, string>;

export const defaultParamValues = (strategy: Strategy | undefined): ParamValues =>
  Object.fromEntries(
    (strategy?.parameters ?? []).map((param) => [
      param.name,
      param.default === null ? "" : String(param.default),
    ]),
  );

export const paramsFromRecord = (
  strategy: Strategy | undefined,
  record: Record<string, unknown>,
): ParamValues => {
  const defaults = defaultParamValues(strategy);
  const values: ParamValues = { ...defaults };
  for (const param of strategy?.parameters ?? []) {
    const value = record[param.name];
    if (typeof value === "number" || typeof value === "string") values[param.name] = String(value);
  }
  return values;
};

export const validateParam = (param: StrategyParameter, raw: string): string | undefined => {
  const text = raw.trim();
  if (text === "") return param.default === null ? undefined : "Informe um valor.";
  if (!NUMBER_PATTERN.test(text)) return "Use um número.";
  if (param.type === INTEGER_TYPE && text.includes(".")) return "Use um número inteiro.";
  if (param.minimum !== null && Number.parseFloat(text) < param.minimum) {
    return `O mínimo é ${param.minimum}.`;
  }
  return undefined;
};

export const buildStrategyParams = (
  strategy: Strategy | undefined,
  values: ParamValues,
): Record<string, number> => {
  const params: Record<string, number> = {};
  for (const param of strategy?.parameters ?? []) {
    const text = (values[param.name] ?? "").trim();
    if (text === "") continue;
    params[param.name] =
      param.type === INTEGER_TYPE ? Number.parseInt(text, 10) : Number.parseFloat(text);
  }
  return params;
};

export const parseGridList = (text: string, integer: boolean): number[] | string => {
  const parts = text
    .split(",")
    .map((part) => part.trim())
    .filter((part) => part !== "");
  if (parts.length === 0) return "Informe ao menos um valor.";
  const values: number[] = [];
  for (const part of parts) {
    if (!NUMBER.test(part)) return `"${part}" não é um número.`;
    if (integer && part.includes(".")) return `"${part}" não é um número inteiro.`;
    values.push(integer ? Number.parseInt(part, 10) : Number.parseFloat(part));
  }
  return values;
};
