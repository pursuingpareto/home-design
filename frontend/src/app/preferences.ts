/** Per-browser display preferences (UI-001 §7, UI-003 §5.3). Storage failures fall back to the default. */

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

const CONNECTIONS_KEY = "homedesign.connections";

/** The "Connections" switch for both views (D062, UI-003 §5.3): on by default. */
export function readShowConnections(): boolean {
  try {
    return localStorage.getItem(CONNECTIONS_KEY) !== "off";
  } catch {
    return true;
  }
}

export function writeShowConnections(show: boolean): void {
  try {
    localStorage.setItem(CONNECTIONS_KEY, show ? "on" : "off");
  } catch {
    // ignore: the preference is a convenience only
  }
}
