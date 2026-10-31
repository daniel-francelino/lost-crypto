import { describe, expect, it } from "vitest";
import { safeRedirect } from "@/lib/auth/redirect";

describe("safeRedirect", () => {
  it("keeps same-origin paths", () => {
    expect(safeRedirect("/bots/1?tab=ordens")).toBe("/bots/1?tab=ordens");
  });

  it("falls back to the home page for anything that could leave the app", () => {
    expect(safeRedirect(undefined)).toBe("/");
    expect(safeRedirect("https://evil.example")).toBe("/");
    expect(safeRedirect("//evil.example")).toBe("/");
    expect(safeRedirect("/\\evil.example")).toBe("/");
    expect(safeRedirect("/login?redirect=/x")).toBe("/");
  });
});
