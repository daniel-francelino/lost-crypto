import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";
import { ApiError, ApiErrorKind } from "@/lib/shared/api/api-error";
import { request, requestPaged } from "@/lib/shared/api/client";
import { HttpMethod } from "@/lib/shared/api/http";
import {
  clearSession,
  ensureSession,
  getAccessToken,
  login,
  logout,
  setSession,
} from "@/lib/shared/api/session";
import { Role } from "@/lib/shared/enums";

const USER = {
  id: "1",
  username: "ana",
  role: Role.Admin,
  is_active: true,
  created_at: "2026-10-31T00:00:00Z",
  last_login_at: null,
  can_write: true,
};

const token = (access: string) => ({
  access_token: access,
  token_type: "bearer",
  expires_in: 900,
  user: USER,
});

const json = (status: number, body: unknown, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify(body), { status, headers });

type Call = { url: string; init: RequestInit };
const calls: Call[] = [];

const stubFetch = (handler: (call: Call) => Response) => {
  calls.length = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init: RequestInit) => {
      const call = { url, init };
      calls.push(call);
      return handler(call);
    }),
  );
};

const refreshCalls = () => calls.filter((call) => call.url.endsWith("/auth/refresh"));
const bearer = (call: Call) => (call.init.headers as Record<string, string>)["Authorization"];

beforeEach(() => clearSession());
afterEach(() => vi.unstubAllGlobals());

describe("request", () => {
  it("sends the bearer token and parses the response with the schema", async () => {
    setSession("tok-1", 900, USER);
    stubFetch(() => json(200, { name: "x" }));
    const result = await request({ path: "/ping", schema: z.object({ name: z.string() }) });
    expect(result).toEqual({ name: "x" });
    expect(bearer(calls[0] as Call)).toBe("Bearer tok-1");
  });

  it("serialises arrays as repeated keys and skips empty values", async () => {
    stubFetch(() => json(200, []));
    await request({
      path: "/backtests/compare",
      schema: z.array(z.unknown()),
      query: { ids: ["a", "b"], limit: 5, skip: undefined, empty: "" },
    });
    expect((calls[0] as Call).url).toContain("ids=a&ids=b&limit=5");
    expect((calls[0] as Call).url).not.toContain("skip");
    expect((calls[0] as Call).url).not.toContain("empty");
  });

  it("refreshes once for several parallel 401s and retries each request", async () => {
    setSession("old", 900, USER);
    stubFetch((call) => {
      if (call.url.endsWith("/auth/refresh")) return json(200, token("new"));
      return bearer(call) === "Bearer new" ? json(200, { ok: true }) : json(401, { detail: "no" });
    });
    const schema = z.object({ ok: z.boolean() });
    const results = await Promise.all([
      request({ path: "/a", schema }),
      request({ path: "/b", schema }),
      request({ path: "/c", schema }),
    ]);
    expect(results).toHaveLength(3);
    expect(refreshCalls()).toHaveLength(1);
    expect(getAccessToken()).toBe("new");
  });

  it("clears the session and fails with 401 when the refresh is refused", async () => {
    setSession("old", 900, USER);
    stubFetch(() => json(401, { detail: "expired" }));
    await expect(request({ path: "/a", schema: z.unknown() })).rejects.toMatchObject({
      status: 401,
    });
    expect(getAccessToken()).toBeNull();
  });

  it("does not retry a request that was not unauthorized", async () => {
    stubFetch(() => json(409, { detail: "bot is not stopped" }));
    await expect(
      request({ method: HttpMethod.Post, path: "/bots/1/start", schema: z.unknown(), body: {} }),
    ).rejects.toMatchObject({ status: 409, detail: "bot is not stopped" });
    expect(calls).toHaveLength(1);
  });

  it("maps a validation array to field errors", async () => {
    stubFetch(() =>
      json(422, {
        detail: [
          { loc: ["body", "initial_capital"], msg: "must be positive", type: "x" },
          { loc: ["body", "name"], msg: "too short", type: "x" },
        ],
      }),
    );
    const error = await request({ path: "/bots", schema: z.unknown() }).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).fieldErrors).toEqual({
      initial_capital: "must be positive",
      name: "too short",
    });
  });

  it("reports an invalid response and a network failure as such", async () => {
    stubFetch(() => json(200, { name: 3 }));
    await expect(
      request({ path: "/ping", schema: z.object({ name: z.string() }) }),
    ).rejects.toMatchObject({ kind: ApiErrorKind.InvalidResponse });

    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("down")));
    await expect(request({ path: "/ping", schema: z.unknown() })).rejects.toMatchObject({
      kind: ApiErrorKind.Network,
    });
  });
});

describe("requestPaged", () => {
  it("returns the total from the X-Total-Count header", async () => {
    stubFetch(() => json(200, [1, 2], { "X-Total-Count": "57" }));
    const page = await requestPaged({ path: "/audit-events", schema: z.array(z.number()) });
    expect(page).toEqual({ data: [1, 2], total: 57 });
  });
});

describe("session", () => {
  it("signs in, keeps the token in memory and sends the cookie only to auth endpoints", async () => {
    stubFetch(() => json(200, token("tok")));
    const user = await login("ana", "secret-passphrase");
    expect(user.username).toBe("ana");
    expect(getAccessToken()).toBe("tok");
    expect((calls[0] as Call).init.credentials).toBe("include");

    stubFetch(() => json(200, { ok: true }));
    await request({ path: "/ping", schema: z.unknown() });
    expect((calls[0] as Call).init.credentials).toBeUndefined();
  });

  it("restores a session from the refresh cookie and shares one refresh between callers", async () => {
    stubFetch(() => json(200, token("restored")));
    const [first, second] = await Promise.all([ensureSession(), ensureSession()]);
    expect(first?.username).toBe("ana");
    expect(second?.username).toBe("ana");
    expect(refreshCalls()).toHaveLength(1);
    await ensureSession();
    expect(refreshCalls()).toHaveLength(1);
  });

  it("answers null when there is no cookie and does not retry after an explicit logout", async () => {
    stubFetch(() => json(401, { detail: "no session" }));
    expect(await ensureSession()).toBeNull();

    setSession("tok", 900, USER);
    stubFetch(() => new Response(null, { status: 204 }));
    await logout();
    expect(getAccessToken()).toBeNull();
    stubFetch(() => json(200, token("again")));
    expect(await ensureSession()).toBeNull();
    expect(calls).toHaveLength(0);
  });

  it("clears the local session even when the logout request fails", async () => {
    setSession("tok", 900, USER);
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("down")));
    await logout();
    expect(getAccessToken()).toBeNull();
  });
});
