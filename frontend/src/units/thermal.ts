/**
 * Thermal figures for display (UI-004 §10; D089). Payloads serve SI. Metric shows them as served;
 * imperial converts with the IT Btu: 1 m²·K/W = 5.678263 h·ft²·°F/Btu (so 1 W/(m²·K) = 0.17611
 * Btu/(h·ft²·°F)) and 1 W/(m·K) = 6.933472 Btu·in/(h·ft²·°F). Every figure carries its unit; display only,
 * like lengths. Vapor permeances stay in SI in both systems (D071: recorded only).
 */

import { SQUARE_METERS_PER_SQUARE_FOOT, type UnitSystem } from "./length";

export const R_IP_PER_SI = 5.678263; // h·ft²·°F/Btu per m²·K/W
export const CONDUCTIVITY_IP_PER_SI = 6.933472; // Btu·in/(h·ft²·°F) per W/(m·K)

export type Thermal = { value: number; unit: string };

/** U-value: W/(m²·K), or Btu/(h·ft²·°F). */
export function uValue(wPerM2K: number, system: UnitSystem): Thermal {
  return system === "metric" ? { value: wPerM2K, unit: "W/(m²·K)" } : { value: wPerM2K / R_IP_PER_SI, unit: "Btu/(h·ft²·°F)" };
}

/** R-value (or a declared layer resistance): m²·K/W, or h·ft²·°F/Btu. */
export function rValue(m2KPerW: number, system: UnitSystem): Thermal {
  return system === "metric" ? { value: m2KPerW, unit: "m²·K/W" } : { value: m2KPerW * R_IP_PER_SI, unit: "h·ft²·°F/Btu" };
}

/** Area-weighted heat flow UA: W/K, or Btu/(h·°F). */
export function uaValue(wPerK: number, system: UnitSystem): Thermal {
  return system === "metric" ? { value: wPerK, unit: "W/K" } : { value: wPerK / R_IP_PER_SI / SQUARE_METERS_PER_SQUARE_FOOT, unit: "Btu/(h·°F)" };
}

/** Declared conductivity: W/(m·K), or Btu·in/(h·ft²·°F). */
export function conductivity(wPerMK: number, system: UnitSystem): Thermal {
  return system === "metric" ? { value: wPerMK, unit: "W/(m·K)" } : { value: wPerMK * CONDUCTIVITY_IP_PER_SI, unit: "Btu·in/(h·ft²·°F)" };
}

/** Declared vapor permeance, as served in both systems. */
export function permeance(kgPerPaSM2: number): Thermal {
  return { value: kgPerPaSM2, unit: "kg/(Pa·s·m²)" };
}

/** Display rounding (a display choice, UI-004 §20): U and conductivity to 3 decimals, R to 2, UA to 1. */
const DECIMALS: Record<string, number> = {
  "W/(m²·K)": 3,
  "Btu/(h·ft²·°F)": 3,
  "m²·K/W": 2,
  "h·ft²·°F/Btu": 2,
  "W/K": 1,
  "Btu/(h·°F)": 1,
  "W/(m·K)": 3,
  "Btu·in/(h·ft²·°F)": 3,
};

/** "3.52 m²·K/W"; permeances in exponent notation. A null figure is "Not computed", never 0 (D071). */
export function formatThermal(figure: Thermal | null): string {
  if (!figure) return "Not computed";
  const decimals = DECIMALS[figure.unit];
  const text = decimals === undefined ? figure.value.toExponential(2) : figure.value.toFixed(decimals);
  return `${text} ${figure.unit}`;
}
