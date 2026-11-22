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

/** A display switch remembered per browser: on unless stored "off" (D062, D066). */
function readSwitch(key: string): boolean {
  try {
    return localStorage.getItem(key) !== "off";
  } catch {
    return true;
  }
}

function writeSwitch(key: string, show: boolean): void {
  try {
    localStorage.setItem(key, show ? "on" : "off");
  } catch {
    // ignore: the preference is a convenience only
  }
}

export const WALL_LAYERS_KEY = "homedesign.wallLayers";
export const WALL_FRAMING_KEY = "homedesign.wallFraming";

/** The "Wall layers" switch for both views (D066, UI-004 §6): on by default. */
export const readShowWallLayers = () => readSwitch(WALL_LAYERS_KEY);
export const writeShowWallLayers = (show: boolean) => writeSwitch(WALL_LAYERS_KEY, show);
/** The "Wall framing" switch for both views (D066, UI-004 §6): on by default. */
export const readShowWallFraming = () => readSwitch(WALL_FRAMING_KEY);
export const writeShowWallFraming = (show: boolean) => writeSwitch(WALL_FRAMING_KEY, show);
