/** Per-browser display preferences (UI-001 §7). Storage failures fall back to the default. */

import type { UnitSystem } from "../units/length";

const KEY = "homedesign.units";

export function readUnits(): UnitSystem {
  try {
    return localStorage.getItem(KEY) === "metric" ? "metric" : "imperial";
  } catch {
    return "imperial";
  }
}

export function writeUnits(units: UnitSystem): void {
  try {
    localStorage.setItem(KEY, units);
  } catch {
    // ignore: the preference is a convenience only
  }
}
