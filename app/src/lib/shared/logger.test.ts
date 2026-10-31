import { describe, expect, it } from "vitest";
import { redact } from "@/lib/shared/logger";

describe("redact", () => {
  it("hides tokens, secrets and passwords at any depth", () => {
    const result = redact({
      status: 401,
      body: { access_token: "abc", nested: [{ api_secret: "x", label: "ok" }] },
      password: "p",
    });
    expect(result).toEqual({
      status: 401,
      body: { access_token: "[redacted]", nested: [{ api_secret: "[redacted]", label: "ok" }] },
      password: "[redacted]",
    });
  });

  it("leaves primitives alone", () => {
    expect(redact("text")).toBe("text");
    expect(redact(3)).toBe(3);
    expect(redact(null)).toBeNull();
  });
});
