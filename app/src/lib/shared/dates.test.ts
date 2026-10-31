import { describe, expect, it } from "vitest";
import {
  addSecondsMs,
  ageSeconds,
  countdownSeconds,
  dayEndUtcIso,
  dayStartUtcIso,
  daysAgoString,
  formatAge,
  formatUtc,
  formatUtcDay,
  isDayString,
  toMs,
} from "@/lib/shared/dates";

const NOW = toMs("2026-10-31T12:00:00Z");

describe("dates", () => {
  it("shows UTC explicitly", () => {
    expect(formatUtc("2026-10-31T01:18:01Z")).toBe("31/10/2026 01:18:01 UTC");
    expect(formatUtcDay("2026-10-31T23:59:59Z")).toBe("31/10/2026 UTC");
    expect(formatUtc(null)).toBe("—");
    expect(formatUtc("not a date")).toBe("—");
  });

  it("computes ages and words them", () => {
    expect(ageSeconds("2026-10-31T11:59:30Z", NOW)).toBe(30);
    expect(ageSeconds("2026-10-31T12:00:10Z", NOW)).toBe(0);
    expect(ageSeconds(null, NOW)).toBeNull();
    expect(formatAge(30)).toBe("há 30 s");
    expect(formatAge(120)).toBe("há 2 min");
    expect(formatAge(7200)).toBe("há 2 h");
    expect(formatAge(172800)).toBe("há 2 d");
    expect(formatAge(null)).toBe("—");
  });

  it("builds UTC day boundaries and validates day strings", () => {
    expect(dayStartUtcIso("2026-10-31")).toBe("2026-10-31T00:00:00Z");
    expect(dayEndUtcIso("2026-10-31")).toBe("2026-10-31T23:59:59Z");
    expect(isDayString("2026-10-31")).toBe(true);
    expect(isDayString("2026-13-40")).toBe(false);
    expect(isDayString("31/10/2026")).toBe(false);
    expect(daysAgoString(30, NOW)).toBe("2026-10-01");
  });

  it("counts down to an expiry and never goes below zero", () => {
    expect(countdownSeconds("2026-10-31T12:05:00Z", NOW)).toBe(300);
    expect(countdownSeconds("2026-10-31T11:00:00Z", NOW)).toBe(0);
    expect(addSecondsMs(NOW, 900) - NOW).toBe(900000);
  });
});
