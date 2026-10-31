const DECIMAL = /^\d+(\.\d+)?$/;
const INTEGER = /^\d+$/;
const SYMBOL_PATTERN = /^[A-Z0-9]+\/[A-Z0-9]+$/;

export const decimalError = (value: string, required: boolean): string | undefined => {
  const trimmed = value.trim();
  if (trimmed === "") return required ? "Informe um valor." : undefined;
  return DECIMAL.test(trimmed) ? undefined : "Use um número, com ponto decimal (ex.: 12.5).";
};

export const integerError = (value: string): string | undefined => {
  const trimmed = value.trim();
  if (trimmed === "") return undefined;
  return INTEGER.test(trimmed) ? undefined : "Use um número inteiro.";
};

export const symbolError = (value: string): string | undefined =>
  SYMBOL_PATTERN.test(value.trim().toUpperCase())
    ? undefined
    : "Use o formato BASE/COTAÇÃO, ex.: BTC/USDT.";
