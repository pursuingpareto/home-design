/**
 * Money input and display (UI-001 §5.1). Price books store whole cents per meter (artifacts.md §8.2).
 * Parsing and conversion use BigInt only, never binary floating point.
 */

import { roundHalfEven } from "./decimal";
import type { UnitSystem } from "./length";

export type MoneyResult = { ok: true; cents: bigint } | { ok: false; error: string };

const MONEY = /^\$?\s*(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{1,2}))?$/;
const MAX_SAFE = BigInt(Number.MAX_SAFE_INTEGER);

/** Parse "31.50", "$1,234.5", or "12" into whole cents. At most two decimal places; never negative. */
export function parseMoney(input: string): MoneyResult {
  const text = input.trim();
  if (text.startsWith("-")) return { ok: false, error: "Prices cannot be negative." };
  const match = MONEY.exec(text);
  if (!match) return { ok: false, error: "Enter an amount such as 31.50 (at most two decimal places)." };
  const cents = BigInt((match[1] ?? "0").replace(/,/g, "")) * 100n + BigInt((match[2] ?? "").padEnd(2, "0") || "0");
  if (cents > MAX_SAFE) return { ok: false, error: "Amount is too large." };
  return { ok: true, cents };
}

/** Cents per linear foot → whole cents per meter: × 1/0.3048 = × 1250/381, rounded half-even. */
export function perFootToPerMeter(centsPerFoot: bigint): bigint {
  return roundHalfEven(centsPerFoot * 1250n, 381n);
}

/** Cents per meter for a price typed in the display system (per foot in imperial, per meter in metric). */
export function centsPerMeter(cents: bigint, system: UnitSystem): bigint {
  return system === "imperial" ? perFootToPerMeter(cents) : cents;
}

/** Cents per square foot → whole cents per square meter: × 1/0.09290304 = × 1562500/145161, rounded half-even (ART-003 §10). */
export function perSquareFootToPerSquareMeter(centsPerSquareFoot: bigint): bigint {
  return roundHalfEven(centsPerSquareFoot * 1562500n, 145161n);
}

/** Cents per square meter for a price typed in the display system (per sf in imperial, per m² in metric). */
export function centsPerSquareMeter(cents: bigint, system: UnitSystem): bigint {
  return system === "imperial" ? perSquareFootToPerSquareMeter(cents) : cents;
}

/** "$1,234.56" from whole cents (number or bigint). */
export function formatCents(cents: number | bigint): string {
  const value = BigInt(cents);
  const negative = value < 0n;
  const abs = negative ? -value : value;
  const whole = (abs / 100n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const frac = (abs % 100n).toString().padStart(2, "0");
  return `${negative ? "−" : ""}$${whole}.${frac}`;
}

/** Approximate per-foot equivalent of a stored per-meter price, for display only (4 decimals). */
export function approxPerFoot(centsPerMeterValue: number): string {
  return `≈ $${((centsPerMeterValue * 0.3048) / 100).toFixed(4)}/ft`;
}

/** Approximate per-square-foot equivalent of a stored per-square-meter price, for display only (4 decimals). */
export function approxPerSquareFoot(centsPerSquareMeterValue: number): string {
  return `≈ $${((centsPerSquareMeterValue * 0.09290304) / 100).toFixed(4)}/sf`;
}

/** Text for a price input field in the display system, from a stored per-square-meter price. */
export function areaPriceInputText(centsPerSquareMeterValue: number, system: UnitSystem): string {
  if (system === "metric") return (centsPerSquareMeterValue / 100).toFixed(2);
  return ((centsPerSquareMeterValue * 0.09290304) / 100).toFixed(2);
}

/** Text for a price input field in the display system, from a stored per-meter price. */
export function priceInputText(centsPerMeterValue: number, system: UnitSystem): string {
  if (system === "metric") return (centsPerMeterValue / 100).toFixed(2);
  return ((centsPerMeterValue * 0.3048) / 100).toFixed(2);
}
