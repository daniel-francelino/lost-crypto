import { describe, expect, it } from "vitest";
import { AppEnv, parseEnv } from "@/lib/shared/env";

describe("parseEnv", () => {
  it("uses the local API and environment when nothing is set", () => {
    expect(parseEnv({})).toEqual({
      apiBaseUrl: "http://localhost:8000/api/v1",
      appEnv: AppEnv.Local,
    });
  });

  it("strips trailing slashes from the API address", () => {
    const parsed = parseEnv({ VITE_API_BASE_URL: "https://api.example.com/api/v1//" });
    expect(parsed.apiBaseUrl).toBe("https://api.example.com/api/v1");
  });

  it("refuses an address that is not a URL and an unknown environment", () => {
    expect(() => parseEnv({ VITE_API_BASE_URL: "not a url" })).toThrow();
    expect(() => parseEnv({ VITE_APP_ENV: "staging" })).toThrow();
  });
});
