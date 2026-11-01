import { describe, expect, it } from "vitest";
import { NOTE_MAX_LENGTH, canSubmitNote, remainingCharacters } from "@/lib/shared/notes";

describe("analysis notes", () => {
  it("refuses an empty or whitespace-only note", () => {
    expect(canSubmitNote("")).toBe(false);
    expect(canSubmitNote("   \n ")).toBe(false);
    expect(canSubmitNote("pausado: o regime mudou")).toBe(true);
  });

  it("allows exactly the maximum length and no more", () => {
    expect(canSubmitNote("x".repeat(NOTE_MAX_LENGTH))).toBe(true);
    expect(canSubmitNote("x".repeat(NOTE_MAX_LENGTH + 1))).toBe(false);
  });

  it("counts the characters left", () => {
    expect(remainingCharacters("abc")).toBe(NOTE_MAX_LENGTH - 3);
  });
});
