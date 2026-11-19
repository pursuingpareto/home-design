import { describe, expect, it } from "vitest";

import { roundHalfEven } from "../src/units/decimal";
import { formatLength, formatPitch, lengthInputText, parseLength } from "../src/units/length";
import { centsPerMeter, formatCents, parseMoney, perFootToPerMeter } from "../src/units/money";
import { fixture } from "./fixtures";

const meters = (text: string, system: "imperial" | "metric" = "imperial") => {
  const result = parseLength(text, system);
  if (!result.ok) throw new Error(result.error);
  return result.meters;
};

describe("length input (UI-001 §7)", () => {
  it("converts D025 dimensions to exactly the stored values", () => {
    const footprint = fixture.snapshot.entities.find((e) => e.kind === "Footprint");
    expect(footprint?.kind).toBe("Footprint");
    if (footprint?.kind !== "Footprint") return;
    expect(meters("36'")).toBe(footprint.width_m); // naive 36 * 0.3048 is 10.972800000000001
    expect(meters("24'")).toBe(footprint.depth_m);
    expect(36 * 0.3048).not.toBe(footprint.width_m);
    expect(meters("40'")).toBe(12.192);
    expect(meters("10'")).toBe(3.048);
    expect(meters("9'")).toBe(2.7432);
  });

  it("accepts the documented forms", () => {
    expect(meters(`36' 6"`)).toBe(meters(`438"`));
    expect(meters(`36' 6 1/2"`)).toBe(11.1379);
    expect(meters(`36'6-1/2"`)).toBe(11.1379);
    expect(meters(`438.5"`)).toBe(11.1379);
    expect(meters("36 ft 6 in")).toBe(meters(`36' 6"`));
    expect(meters("36.5 ft")).toBe(meters(`36' 6"`));
    expect(meters(`1/2"`)).toBe(0.0127);
    expect(meters("10.9728 m")).toBe(10.9728);
    expect(meters("10972.8 mm")).toBe(10.9728);
    expect(meters("1097.28 cm")).toBe(10.9728);
    expect(meters("36")).toBe(10.9728); // bare number: feet in imperial
    expect(meters("10.9728", "metric")).toBe(10.9728); // meters in metric
    expect(meters("36'", "metric")).toBe(10.9728); // either system in any field
    expect(meters(`36’ 6”`)).toBe(meters(`36' 6"`)); // typographic quotes
  });

  it("rejects malformed and over-precise input", () => {
    for (const bad of ["", "abc", "-36'", `36' 6 1/128"`, "36.1'", "1/0\"", "36' 6", "12 furlongs", "1e3 m"]) {
      expect(parseLength(bad, "imperial").ok, bad).toBe(false);
    }
    const tooFine = parseLength(`1/128"`, "imperial");
    expect(tooFine.ok ? "" : tooFine.error).toMatch(/1\/64/);
  });

  it("formats to 1/16 inch or the millimeter", () => {
    expect(formatLength(10.9728, "imperial")).toBe(`36' 0"`);
    expect(formatLength(11.1379, "imperial")).toBe(`36' 6 1/2"`);
    expect(formatLength(3.6576, "imperial")).toBe(`12' 0"`);
    expect(formatLength(0.0015875, "imperial")).toBe(`0' 0 1/16"`);
    expect(formatLength(10.9728, "metric")).toBe("10.973 m");
    expect(formatPitch(Math.atan(9 / 12))).toBe("9/12 (36.87°)");
  });

  it("round-trips the input text of stored values", () => {
    for (const m of [10.9728, 7.3152, 12.192, 11.1379]) {
      expect(meters(lengthInputText(m, "imperial"))).toBe(m);
      expect(meters(lengthInputText(m, "metric"), "metric")).toBe(m);
    }
  });
});

describe("money input (UI-001 §5.1)", () => {
  it("parses exact cents", () => {
    const cents = (t: string) => {
      const r = parseMoney(t);
      if (!r.ok) throw new Error(r.error);
      return r.cents;
    };
    expect(cents("31.50")).toBe(3150n);
    expect(cents("31.5")).toBe(3150n);
    expect(cents("$1,234.56")).toBe(123456n);
    expect(cents("12")).toBe(1200n);
    expect(cents("0.07")).toBe(7n); // 0.07 is not exact in binary; BigInt parsing is
    for (const bad of ["", "-1", "1.234", "abc", "1,23", "99999999999999999"]) expect(parseMoney(bad).ok, bad).toBe(false);
  });

  it("converts per-foot prices to whole cents per meter, half-even", () => {
    expect(perFootToPerMeter(1000n)).toBe(3281n); // $10.00/ft = 3280.84 c/m
    expect(perFootToPerMeter(333n)).toBe(1093n); // 1092.52
    expect(perFootToPerMeter(0n)).toBe(0n);
    expect(centsPerMeter(3150n, "metric")).toBe(3150n);
    expect(roundHalfEven(5n, 2n)).toBe(2n);
    expect(roundHalfEven(7n, 2n)).toBe(4n);
    expect(roundHalfEven(3n, 2n)).toBe(2n);
    expect(roundHalfEven(4n, 3n)).toBe(1n);
    expect(roundHalfEven(5n, 3n)).toBe(2n);
  });

  it("formats cents", () => {
    expect(formatCents(123456)).toBe("$1,234.56");
    expect(formatCents(5n)).toBe("$0.05");
  });
});
