import { describe, it, expect } from "vitest";
import { substringMatch } from "./scoring.js";

describe("substringMatch", () => {
  it("matches case-insensitive substring", () => {
    expect(substringMatch("The answer is 23.5 degrees", "23.5")).toBe(1.0);
  });

  it("returns 0 for no match", () => {
    expect(substringMatch("no match here", "42")).toBe(0.0);
  });

  it("matches any alternative in array", () => {
    expect(substringMatch("result is mA", ["milliampere", "mA"])).toBe(1.0);
  });

  it("handles case differences", () => {
    expect(substringMatch("SOSA:OBSERVATION found", "sosa:observation")).toBe(1.0);
  });

  it("returns 0 for empty prediction", () => {
    expect(substringMatch("", "something")).toBe(0.0);
  });
});
