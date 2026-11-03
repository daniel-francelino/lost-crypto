const LOCALE = "pt-BR";
const EMPTY = "—";

type Digits = { min: number; max: number };

const MONEY: Digits = { min: 2, max: 2 };
const PRICE: Digits = { min: 2, max: 8 };
const QUANTITY: Digits = { min: 0, max: 8 };
const PERCENT: Digits = { min: 2, max: 2 };

const formatter = (digits: Digits, signed: boolean) =>
  new Intl.NumberFormat(LOCALE, {
    minimumFractionDigits: digits.min,
    maximumFractionDigits: digits.max,
    ...(signed ? { signDisplay: "exceptZero" as const } : {}),
  });

const isDecimal = (value: string): value is Intl.StringNumericLiteral =>
  /^-?\d+(\.\d+)?$/.test(value);

const decimal = (value: string | null | undefined, digits: Digits, signed = false): string => {
  if (value === null || value === undefined || !isDecimal(value)) return EMPTY;
  return formatter(digits, signed).format(value);
};

export const formatMoney = (value: string | null | undefined, quote: string): string => {
  const text = decimal(value, MONEY);
  return text === EMPTY ? EMPTY : `${text} ${quote}`;
};

export type LeveragedEntryEstimate = { notional: string; collateral: string };

export const estimateLeveragedEntry = (
  capitalText: string,
  positionFractionText: string,
  leverageText: string,
  feeRateText: string,
  orderCapText: string,
): LeveragedEntryEstimate | null => {
  const capital = isDecimal(capitalText) ? Number(capitalText) : Number.NaN;
  const positionFraction = isDecimal(positionFractionText)
    ? Number(positionFractionText)
    : Number.NaN;
  const leverage = isDecimal(leverageText) ? Number(leverageText) : Number.NaN;
  const feeRate = isDecimal(feeRateText) ? Number(feeRateText) : Number.NaN;
  let orderCap: number | null = null;
  if (orderCapText !== "") orderCap = isDecimal(orderCapText) ? Number(orderCapText) : NaN;
  if (
    !Number.isFinite(capital) ||
    capital <= 0 ||
    !Number.isFinite(positionFraction) ||
    positionFraction <= 0 ||
    positionFraction > 1 ||
    !Number.isInteger(leverage) ||
    leverage < 1 ||
    leverage > 10 ||
    !Number.isFinite(feeRate) ||
    feeRate < 0 ||
    (orderCap !== null && (!Number.isFinite(orderCap) || orderCap <= 0))
  ) {
    return null;
  }

  const collateralBudget = capital * positionFraction;
  let notional = (collateralBudget * leverage) / (1 + feeRate * leverage);
  if (orderCap !== null) notional = Math.min(notional, orderCap);
  return {
    notional: String(notional),
    collateral: String(notional / leverage + notional * feeRate),
  };
};

export const formatSignedMoney = (value: string | null | undefined, quote: string): string => {
  const text = decimal(value, MONEY, true);
  return text === EMPTY ? EMPTY : `${text} ${quote}`;
};

export const formatPrice = (value: string | null | undefined): string => decimal(value, PRICE);

export const formatQuantity = (value: string | null | undefined): string =>
  decimal(value, QUANTITY);

export const formatPercent = (value: string | null | undefined): string => {
  const text = decimal(value, PERCENT);
  return text === EMPTY ? EMPTY : `${text}%`;
};

export const formatSignedPercent = (value: string | null | undefined): string => {
  const text = decimal(value, PERCENT, true);
  return text === EMPTY ? EMPTY : `${text}%`;
};

export const formatInteger = (value: number): string =>
  new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 0 }).format(value);

export const quoteCurrency = (symbol: string): string =>
  (symbol.split("/").at(-1) ?? symbol).split(":")[0] ?? symbol;

export const Sign = {
  Positive: "positive",
  Negative: "negative",
  Zero: "zero",
  Unknown: "unknown",
} as const;
export type Sign = (typeof Sign)[keyof typeof Sign];

export const signOf = (value: string | null | undefined): Sign => {
  if (value === null || value === undefined || !isDecimal(value)) return Sign.Unknown;
  if (/^-0(\.0+)?$/.test(value) || /^0(\.0+)?$/.test(value)) return Sign.Zero;
  return value.startsWith("-") ? Sign.Negative : Sign.Positive;
};

export const shortId = (value: string): string =>
  value.length <= 12 ? value : `${value.slice(0, 6)}…${value.slice(-4)}`;

export const compareDecimal = (a: string | null, b: string | null): number => {
  const left = a === null || !isDecimal(a) ? Number.NEGATIVE_INFINITY : Number.parseFloat(a);
  const right = b === null || !isDecimal(b) ? Number.NEGATIVE_INFINITY : Number.parseFloat(b);
  return left === right ? 0 : left < right ? -1 : 1;
};

const RATIO: Digits = { min: 2, max: 2 };

export const formatRatio = (value: string | null | undefined): string => decimal(value, RATIO);

const HOUR_SECONDS = 3600;
const DAY_SECONDS = 24 * HOUR_SECONDS;

export const formatDuration = (seconds: number | null | undefined): string => {
  if (seconds === null || seconds === undefined) return EMPTY;
  if (seconds < DAY_SECONDS) {
    const hours = Math.round(seconds / HOUR_SECONDS);
    return hours === 1 ? "1 hora" : `${formatInteger(hours)} horas`;
  }
  const days = Math.round((seconds / DAY_SECONDS) * 10) / 10;
  const text = new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 1 }).format(days);
  return days === 1 ? "1 dia" : `${text} dias`;
};

export const formatDecimalDuration = (seconds: string | null | undefined): string => {
  if (seconds === null || seconds === undefined || !isDecimal(seconds)) return EMPTY;
  return formatDuration(Number(seconds));
};

export const formatFractionAsPercent = (value: string | null | undefined): string => {
  if (value === null || value === undefined || !isDecimal(value)) return EMPTY;
  return new Intl.NumberFormat(LOCALE, { style: "percent", maximumFractionDigits: 0 }).format(
    value,
  );
};

export const formatFraction = (value: string | null | undefined): string =>
  decimal(value, { min: 0, max: 4 });

export const trimDecimalZeros = (value: string): string =>
  isDecimal(value) && value.includes(".") ? value.replace(/0+$/, "").replace(/\.$/, "") : value;

export const numberValue = (value: string): number | null =>
  value.trim() === "" ? null : Number(value);

export const numberText = (value: number | null): string => (value === null ? "" : String(value));
