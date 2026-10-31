import { TZDate } from "@date-fns/tz";
import { addDays, format, parseISO } from "date-fns";

const UTC = "UTC";
const MS_PER_SECOND = 1000;
const DAY_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

export const nowMs = (): number => Date.now();

export const toMs = (iso: string): number => parseISO(iso).getTime();

export const localZone = (): string => Intl.DateTimeFormat().resolvedOptions().timeZone;

const zoneLabel = (ms: number, zone: string): string => {
  if (zone === UTC) return UTC;
  const parts = new Intl.DateTimeFormat("pt-BR", { timeZone: zone, timeZoneName: "short" })
    .formatToParts(ms)
    .find((part) => part.type === "timeZoneName");
  return parts?.value ?? zone;
};

const formatIn = (iso: string, zone: string, pattern: string): string => {
  const ms = toMs(iso);
  if (Number.isNaN(ms)) return "—";
  return `${format(new TZDate(ms, zone), pattern)} ${zoneLabel(ms, zone)}`;
};

const DATE_TIME = "dd/MM/yyyy HH:mm:ss";
const DATE_TIME_SHORT = "dd/MM HH:mm";

export const formatDateTime = (iso: string | null): string =>
  iso === null ? "—" : formatIn(iso, localZone(), DATE_TIME);

export const formatDateTimeShort = (iso: string | null): string =>
  iso === null ? "—" : formatIn(iso, localZone(), DATE_TIME_SHORT);

export const formatUtc = (iso: string | null): string =>
  iso === null ? "—" : formatIn(iso, UTC, DATE_TIME);

export const formatUtcShort = (iso: string | null): string =>
  iso === null ? "—" : formatIn(iso, UTC, DATE_TIME_SHORT);

export const formatUtcDay = (iso: string | null): string =>
  iso === null ? "—" : formatIn(iso, UTC, "dd/MM/yyyy");

export const ageSeconds = (iso: string | null, now: number = nowMs()): number | null => {
  if (iso === null) return null;
  const ms = toMs(iso);
  return Number.isNaN(ms) ? null : Math.max(0, Math.round((now - ms) / MS_PER_SECOND));
};

export const formatAge = (seconds: number | null): string => {
  if (seconds === null) return "—";
  if (seconds < 60) return `há ${seconds} s`;
  if (seconds < 3600) return `há ${Math.floor(seconds / 60)} min`;
  if (seconds < 86400) return `há ${Math.floor(seconds / 3600)} h`;
  return `há ${Math.floor(seconds / 86400)} d`;
};

export const isDayString = (value: string): boolean =>
  DAY_PATTERN.test(value) && !Number.isNaN(parseISO(value).getTime());

export const dayStartUtcIso = (day: string): string => `${day}T00:00:00Z`;

export const dayEndUtcIso = (day: string): string => `${day}T23:59:59Z`;

export const dayString = (ms: number): string => format(new TZDate(ms, UTC), "yyyy-MM-dd");

export const daysAgoString = (days: number, now: number = nowMs()): string =>
  dayString(addDays(new TZDate(now, UTC), -days).getTime());

export const countdownSeconds = (expiresAtIso: string, now: number = nowMs()): number =>
  Math.max(0, Math.ceil((toMs(expiresAtIso) - now) / MS_PER_SECOND));

export const secondsUntil = (ms: number, now: number = nowMs()): number =>
  Math.round((ms - now) / MS_PER_SECOND);

export const addSecondsMs = (base: number, seconds: number): number =>
  base + seconds * MS_PER_SECOND;

export const ageSecondsSinceMs = (ms: number, now: number = nowMs()): number =>
  Math.max(0, Math.round((now - ms) / MS_PER_SECOND));
