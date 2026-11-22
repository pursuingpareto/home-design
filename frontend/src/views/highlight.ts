/**
 * What the views draw as selected, and what they report back (UI-003 §6, UI-004 §7). The workspace
 * computes the highlighted IDs; the views read only their payloads and report picks (UI-001 §6).
 */

export type Pick =
  | { kind: "member"; id: string }
  | { kind: "connections"; ids: string[] }
  | { kind: "wall"; id: string }
  | { kind: "opening"; id: string }
  | { kind: "pieces"; ids: string[] };

export interface Highlight {
  /** The selected member, drawn in the selection color. */
  member: string | null;
  /** The members of the selected connections, drawn in the secondary color. */
  related: ReadonlySet<string>;
  /** The selected connections. */
  connections: ReadonlySet<string>;
  /** The selected wall (its band and layers). */
  walls: ReadonlySet<string>;
  /** The selected opening (its mark and outline). */
  openings: ReadonlySet<string>;
  /** The selected wall framing pieces. */
  pieces: ReadonlySet<string>;
  /** A selected opening's framing pieces, drawn in the secondary color. */
  relatedPieces: ReadonlySet<string>;
}

const EMPTY: ReadonlySet<string> = new Set();

export const NO_HIGHLIGHT: Highlight = {
  member: null,
  related: EMPTY,
  connections: EMPTY,
  walls: EMPTY,
  openings: EMPTY,
  pieces: EMPTY,
  relatedPieces: EMPTY,
};
