/**
 * What the views draw as selected, and what they report back (UI-003 §6). The workspace computes the
 * highlighted IDs; the views read only their payloads and report picks (UI-001 §6).
 */

export type Pick = { kind: "member"; id: string } | { kind: "connections"; ids: string[] };

export interface Highlight {
  /** The selected member, drawn in the selection color. */
  member: string | null;
  /** The members of the selected connections, drawn in the secondary color. */
  related: ReadonlySet<string>;
  /** The selected connections. */
  connections: ReadonlySet<string>;
}

export const NO_HIGHLIGHT: Highlight = { member: null, related: new Set(), connections: new Set() };
