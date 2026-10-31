import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  getAlertSummary,
  listAlerts,
  markAlertRead,
  markAllAlertsRead,
} from "@/lib/shared/alerts/alerts.api";
import { clearSession } from "@/lib/shared/api/session";
import { AlertKind, AlertSeverity, Unknown } from "@/lib/shared/enums";
import { alertKindLabel, alertSeverityLabel } from "@/lib/shared/labels";

const ALERT = {
  id: 7,
  kind: AlertKind.WorkerDown,
  severity: AlertSeverity.Critical,
  message: "No worker heartbeat.",
  bot_id: null,
  payload: {},
  opened_at: "2026-10-31T12:00:00Z",
  resolved_at: null,
  read_at: null,
};

type Call = { url: string; init: RequestInit };
const calls: Call[] = [];

const stubFetch = (response: () => Response) => {
  calls.length = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init: RequestInit) => {
      calls.push({ url, init });
      return response();
    }),
  );
};

beforeEach(() => clearSession());
afterEach(() => vi.unstubAllGlobals());

describe("alerts api", () => {
  it("lists alerts with the filters in the query and reads the total from the header", async () => {
    stubFetch(
      () =>
        new Response(JSON.stringify([ALERT]), {
          status: 200,
          headers: { "X-Total-Count": "41" },
        }),
    );
    const result = await listAlerts({
      unreadOnly: true,
      severity: AlertSeverity.Critical,
      limit: 25,
      offset: 50,
    });
    expect(result.total).toBe(41);
    expect(result.data[0]?.kind).toBe(AlertKind.WorkerDown);
    const url = calls[0]?.url ?? "";
    expect(url).toContain("/alerts?");
    expect(url).toContain("unread=true");
    expect(url).toContain("severity=critical");
    expect(url).toContain("limit=25");
    expect(url).toContain("offset=50");
  });

  it("keeps a kind or severity the app does not know as unknown instead of failing", async () => {
    stubFetch(
      () =>
        new Response(JSON.stringify([{ ...ALERT, kind: "brand_new", severity: "fatal" }]), {
          status: 200,
        }),
    );
    const result = await listAlerts({ unreadOnly: false, severity: null, limit: 25, offset: 0 });
    expect(result.data[0]?.kind).toBe(Unknown);
    expect(result.data[0]?.severity).toBe(Unknown);
  });

  it("reads the summary used by the header indicator", async () => {
    stubFetch(
      () => new Response(JSON.stringify({ unread: 3, open: 2, critical_open: 1 }), { status: 200 }),
    );
    expect(await getAlertSummary()).toEqual({ unread: 3, open: 2, critical_open: 1 });
  });

  it("marks one alert as read with a POST and accepts the empty answer", async () => {
    stubFetch(() => new Response(null, { status: 204 }));
    await markAlertRead(7);
    expect(calls[0]?.url).toContain("/alerts/7/read");
    expect(calls[0]?.init.method).toBe("POST");
  });

  it("marks everything as read and returns how many alerts changed", async () => {
    stubFetch(() => new Response(JSON.stringify({ marked: 4 }), { status: 200 }));
    expect(await markAllAlertsRead()).toBe(4);
    expect(calls[0]?.url).toContain("/alerts/read-all");
  });
});

describe("alert labels", () => {
  it("has a Portuguese label for every kind and severity the API can send", () => {
    for (const kind of Object.values(AlertKind)) {
      expect(alertKindLabel(kind)).not.toBe("Desconhecido");
    }
    for (const severity of Object.values(AlertSeverity)) {
      expect(alertSeverityLabel(severity)).not.toBe("Desconhecido");
    }
    expect(alertKindLabel("brand_new")).toBe("Desconhecido");
  });
});
