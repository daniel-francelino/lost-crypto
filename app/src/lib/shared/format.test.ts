import { describe, expect, it } from "vitest";
import {
  Sign,
  formatMoney,
  formatDuration,
  formatPercent,
  formatRatio,
  formatPrice,
  formatQuantity,
  formatSignedMoney,
  quoteCurrency,
  shortId,
  signOf,
} from "@/lib/shared/format";

const NBSP = new RegExp(String.fromCharCode(160), "g");
const plain = (text: string) => text.replace(NBSP, " ");

describe("format", () => {
  it("formats decimal strings without going through floating point", () => {
    expect(plain(formatMoney("1234567890123456.78", "USDT"))).toBe("1.234.567.890.123.456,78 USDT");
    expect(plain(formatMoney("0.1", "USDT"))).toBe("0,10 USDT");
  });

  it("shows a dash for a missing or invalid value, never zero", () => {
    expect(formatMoney(null, "USDT")).toBe("—");
    expect(formatMoney(undefined, "USDT")).toBe("—");
    expect(formatMoney("abc", "USDT")).toBe("—");
    expect(formatPercent(null)).toBe("—");
  });

  it("keeps small prices and quantities precise", () => {
    expect(plain(formatPrice("0.00001234"))).toBe("0,00001234");
    expect(plain(formatQuantity("0.00012000"))).toBe("0,00012");
    expect(plain(formatQuantity("3"))).toBe("3");
  });

  it("signs profit and loss and leaves zero unsigned", () => {
    expect(plain(formatSignedMoney("12.5", "USDT"))).toBe("+12,50 USDT");
    expect(plain(formatSignedMoney("-12.5", "USDT"))).toBe("-12,50 USDT");
    expect(plain(formatSignedMoney("0", "USDT"))).toBe("0,00 USDT");
  });

  it("formats percentages from the percent units the API sends", () => {
    expect(plain(formatPercent("12.3456"))).toBe("12,35%");
  });

  it("classifies the sign of a decimal string", () => {
    expect(signOf("-0.01")).toBe(Sign.Negative);
    expect(signOf("0.01")).toBe(Sign.Positive);
    expect(signOf("0.000")).toBe(Sign.Zero);
    expect(signOf("-0")).toBe(Sign.Zero);
    expect(signOf(null)).toBe(Sign.Unknown);
  });

  it("derives the quote currency from the symbol and shortens identifiers", () => {
    expect(quoteCurrency("BTC/USDT")).toBe("USDT");
    expect(shortId("lc-0123456789abcdef0123")).toBe("lc-012…0123");
    expect(shortId("short")).toBe("short");
  });

  it("formats ratios and drawdown durations", () => {
    expect(formatRatio("1.23456")).toBe("1,23");
    expect(formatRatio(null)).toBe("—");
    expect(formatRatio(undefined)).toBe("—");
    expect(formatDuration(undefined)).toBe("—");
    expect(formatDuration(3600)).toBe("1 hora");
    expect(formatDuration(5 * 3600)).toBe("5 horas");
    expect(formatDuration(86400)).toBe("1 dia");
    expect(formatDuration(36 * 3600)).toBe("1,5 dias");
    expect(formatDuration(120 * 86400)).toBe("120 dias");
  });
});
