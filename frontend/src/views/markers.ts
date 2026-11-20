/**
 * Connection markers at the same point (D062, UI-003 §5.2): one glyph per distinct position. The
 * plan groups a plane's markers by `xy_m`, and the 3D view groups the mesh's by `location_m`. Grouping
 * is by exact coordinate equality; positions stay as served and nothing else is computed.
 */

import { junctionLabel, typeLabel, type ConnectionType } from "../display/labels";
import type { GlyphStyle } from "../display/palette";

export interface Marker {
  connection_id: string;
  connection_type: ConnectionType;
  junction_class: string;
  generation_key: string;
}

export interface Glyph<M extends Marker> {
  /** The exact coordinates, joined; unique per glyph. */
  key: string;
  position: readonly number[];
  markers: M[];
  /** The shared type, or "mixed" when the markers have more than one. */
  style: GlyphStyle;
}

/** Group markers by exact position, in order of first appearance. */
export function groupMarkers<M extends Marker>(markers: readonly M[], position: (marker: M) => readonly number[]): Glyph<M>[] {
  const glyphs = new Map<string, Glyph<M>>();
  for (const marker of markers) {
    const at = position(marker);
    const key = at.join(","); // Number → string round-trips exactly, so equal strings mean equal coordinates
    const glyph = glyphs.get(key);
    if (glyph) {
      glyph.markers.push(marker);
      if (glyph.style !== marker.connection_type) glyph.style = "mixed";
    } else {
      glyphs.set(key, { key, position: at, markers: [marker], style: marker.connection_type });
    }
  }
  return [...glyphs.values()];
}

/** A glyph's tooltip: each connection's junction and type labels and its generation key (UI-003 §5.1). */
export function glyphTitle(glyph: Glyph<Marker>): string {
  return glyph.markers.map((m) => `${junctionLabel(m.junction_class)} · ${typeLabel(m.connection_type)} · ${m.generation_key}`).join("\n");
}
