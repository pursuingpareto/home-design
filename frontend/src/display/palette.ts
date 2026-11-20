/**
 * One palette for the plan, the 3D view, and the schedule's swatches (UI-003 §4, §5.1). Posts and
 * beams keep their VS-01 colors. Traditional connection types use warm tones and engineered types
 * cool or grey tones. Values are display choices only; a test keeps them pairwise distinct.
 */

import type { ConnectionType, Role } from "./labels";

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
