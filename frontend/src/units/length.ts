/**
 * Length display and input (UI-001 §7; D026: 1 ft = 0.3048 m exactly, meters are canonical).
 *
 * Imperial input is converted through whole 1/64-inch steps: 1/64 in = 0.000396875 m exactly, so
 * `n × 396875` is an exact integer number of nanometers and the result is the double nearest the
 * exact length. Re-entering a stored imperial dimension therefore reproduces it bit for bit.
 */

import { add, decimalToNumber, parseRational, scale, toInteger, type Rational } from "./decimal";

export type UnitSystem = "imperial" | "metric";

export type LengthResult = { ok: true; meters: number } | { ok: false; error: string };

const NM_PER_STEP = 396875n; // 1/64 inch in nanometers
const STEPS_PER_INCH = 64n;
const INCHES_PER_FOOT = 12n;

const NUMBER = String.raw`\d+(?:\.\d+)?`;
const FEET = new RegExp(String.raw`^(${NUMBER})\s*(?:'|ft|feet|foot)$`);
const INCH_UNIT = String.raw`\s*(?:"|in|inch|inches)`;
// 6", 6.5", 6 1/2", 6-1/2", 1/2"
const INCHES = new RegExp(String.raw`^(?:(${NUMBER})(?:\s+|-)?)?(\d+/\d+)?${INCH_UNIT}$`);
const METRIC = new RegExp(String.raw`^(${NUMBER})\s*(m|cm|mm)$`);
const BARE = new RegExp(String.raw`^${NUMBER}$`);

function inchesToMeters(inches: Rational): LengthResult {
  const steps = toInteger(scale(inches, STEPS_PER_INCH));
  if (steps === null) return { ok: false, error: "Use at most 1/64-inch precision." };
  return { ok: true, meters: decimalToNumber(steps * NM_PER_STEP, 9) };
}

function parseInchesPart(text: string): Rational | null {
  const match = INCHES.exec(text);
  if (!match || (match[1] === undefined && match[2] === undefined)) return null;
  let total: Rational = { num: 0n, den: 1n };
  for (const part of [match[1], match[2]]) {
    if (part === undefined) continue;
    const value = parseRational(part);
    if (value === null) return null;
    total = add(total, value);
  }
  return total;
}

function parseImperial(text: string): Rational | null {
  // Split "36' 6 1/2"" into a feet part and an optional inches part.
  const feetMatch = /^(.*?(?:'|ft|feet|foot))\s*(.*)$/.exec(text);
  if (feetMatch) {
    const feet = FEET.exec((feetMatch[1] ?? "").trim());
    const feetValue = feet ? parseRational(feet[1] ?? "") : null;
    if (feetValue === null) return null;
    const rest = (feetMatch[2] ?? "").trim();
    const inches = rest === "" ? { num: 0n, den: 1n } : parseInchesPart(rest);
    return inches === null ? null : add(scale(feetValue, INCHES_PER_FOOT), inches);
  }
  return parseInchesPart(text);
}

function parseMetric(value: string, unit: string): LengthResult {
  const rational = parseRational(value);
  if (rational === null) return { ok: false, error: "Not a number." };
  const [whole, frac = ""] = value.split(".");
  const shift = unit === "m" ? 0 : unit === "cm" ? 2 : 3;
  return { ok: true, meters: decimalToNumber(BigInt((whole ?? "0") + frac), frac.length + shift) };
}

/**
 * Parse a length typed by the user. Either system is accepted in any field; a bare number is read in
 * the display system's main unit (feet or meters).
 */
export function parseLength(input: string, system: UnitSystem): LengthResult {
  const text = input.trim().toLowerCase().replace(/[’′]/g, "'").replace(/[”″]/g, '"').replace(/\s+/g, " ");
  if (text === "") return { ok: false, error: "Enter a length." };
  if (text.startsWith("-")) return { ok: false, error: "Lengths cannot be negative." };
  const metric = METRIC.exec(text);
  if (metric) return parseMetric(metric[1] ?? "", metric[2] ?? "m");
  if (BARE.test(text)) {
    return system === "metric" ? parseMetric(text, "m") : parseLength(`${text}'`, "imperial");
  }
  const inches = parseImperial(text);
  if (inches === null) {
    return { ok: false, error: `Not a length. Examples: 36' 6 1/2", 438.5", 10.9728 m, 10972.8 mm.` };
  }
  return inchesToMeters(inches);
}

function gcd(a: number, b: number): number {
  return b === 0 ? a : gcd(b, a % b);
}

/** Display a length: feet-inches to 1/16 inch, or meters to the millimeter. Display only. */
export function formatLength(meters: number, system: UnitSystem): string {
  if (system === "metric") return `${meters.toFixed(3)} m`;
  const sixteenths = Math.round((Math.abs(meters) / 0.0254) * 16);
  const sign = meters < 0 && sixteenths > 0 ? "−" : "";
  const feet = Math.floor(sixteenths / 192);
  const remainder = sixteenths - feet * 192;
  const inches = Math.floor(remainder / 16);
  const fraction = remainder % 16;
  let inchText = `${inches}`;
  if (fraction !== 0) {
    const divisor = gcd(fraction, 16);
    inchText += ` ${fraction / divisor}/${16 / divisor}`;
  }
  return `${sign}${feet}' ${inchText}"`;
}

export const SQUARE_METERS_PER_SQUARE_FOOT = 0.09290304; // 0.3048², exact (D026)

/** Display an area: square feet to 0.1 sf, or square meters to 0.01 m². Display only (ART-003 §10). */
export function formatArea(squareMeters: number, system: UnitSystem): string {
  const value = system === "metric" ? squareMeters : squareMeters / SQUARE_METERS_PER_SQUARE_FOOT;
  const [whole = "0", frac = "0"] = value.toFixed(system === "metric" ? 2 : 1).split(".");
  return `${whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",")}.${frac} ${system === "metric" ? "m²" : "sf"}`;
}

/** Text for an input field: the same as display, so editing starts from a readable value. */
export function lengthInputText(meters: number, system: UnitSystem): string {
  if (system === "metric") return `${meters} m`;
  return formatLength(meters, system);
}

/** Roof pitch as rise per 12 next to degrees, e.g. "9/12 (36.87°)". */
export function formatPitch(radians: number): string {
  const rise = Math.round(Math.tan(radians) * 12 * 8) / 8;
  const degrees = (radians * 180) / Math.PI;
  return `${rise}/12 (${degrees.toFixed(2)}°)`;
}

export const CUBIC_METERS_PER_CUBIC_FOOT = 0.028316846592; // 0.3048³, exact (D026)

/** Display a volume: cubic feet to 0.1 ft³, or cubic meters to 0.01 m³. Display only (UI-004 §10). */
export function formatVolume(cubicMeters: number, system: UnitSystem): string {
  const value = system === "metric" ? cubicMeters : cubicMeters / CUBIC_METERS_PER_CUBIC_FOOT;
  const [whole = "0", frac = "0"] = value.toFixed(system === "metric" ? 2 : 1).split(".");
  return `${whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",")}.${frac} ${system === "metric" ? "m³" : "ft³"}`;
}
