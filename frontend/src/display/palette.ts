/**
 * One palette for the plan, the 3D view, and the schedule's swatches (UI-003 §4, §5.1). Posts and
 * beams keep their VS-01 colors. Traditional connection types use warm tones and engineered types
 * cool or grey tones. Values are display choices only; a test keeps them pairwise distinct.
 */

import type { ConnectionType, FramingGroup, LayerFunction, Role } from "./labels";

export const ROLE_COLOR: Record<Role, number> = {
  POST: 0x8a5a2b,
  BEAM: 0xb07a3f,
  SILL: 0x4d3319,
  FLOOR_JOIST: 0xc9a77c,
  PRINCIPAL_RAFTER: 0x3b7a57,
  PURLIN: 0x6c8ebf,
  KNEE_BRACE: 0x7a3e9d,
};

export const TYPE_COLOR: Record<ConnectionType, number> = {
  PEGGED_MORTISE_TENON: 0xe8590c,
  BRIDLE: 0xc2255c,
  HOUSED_DOVETAIL: 0xf59f00,
  STEEL_KNIFE_PLATE: 0x868e96,
  JOIST_HANGER: 0x15aabf,
};

/** A glyph whose connections have more than one type (D062). */
export const MIXED_COLOR = 0x212529;

/** The selection (primary) and a selected connection's members (secondary, UI-003 §6). */
export const SELECTION_COLOR = { selected: 0x1f6feb, related: 0xff6b9d } as const;

export const css = (hex: number) => `#${hex.toString(16).padStart(6, "0")}`;

export type GlyphStyle = ConnectionType | "mixed";
export const glyphColor = (style: GlyphStyle) => (style === "mixed" ? MIXED_COLOR : TYPE_COLOR[style]);

// --- VS-02b walls (UI-004 §12, item 15): display choices, kept distinct from the colors above by a test.

/** 3D wall layers, by function. */
export const LAYER_COLOR: Record<LayerFunction, number> = {
  FINISH: 0xe6dfd0,
  SHEATHING: 0xb39b7d,
  INSULATION: 0xf1e3a6,
  FRAMING: 0xd6c08a,
};

/** Wall framing marks (plan) and boxes (3D), by group. */
export const FRAMING_COLOR: Record<FramingGroup, number> = {
  layout: 0x5c940d,
  opening: 0x0b7285,
  buck: 0xe03131,
};

/** The plan's wall bands, and the outline of an opening (plan and 3D). */
export const WALL_BAND_COLOR = 0xddd5c4;
export const OPENING_COLOR = 0x495057;
