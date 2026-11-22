/**
 * The workspace's selection (UI-003 §6, UI-004 §7): one member, a set of connections, a wall, an
 * opening, or a set of wall framing pieces. A connection's members come from the same revision's
 * timber schedule rows (`member_ids`), and an opening's framing from the same revision's assembly
 * schedule rows (`opening_id`); without a CURRENT schedule for the views' revision, only the picked
 * objects themselves are highlighted.
 */

import type { AssemblyScheduleEnvelope, ScheduleEnvelope } from "../api/types";
import { NO_HIGHLIGHT, type Highlight, type Pick } from "../views/highlight";

export type Selection = Pick | null;

const sameIds = (a: readonly string[], b: readonly string[]) => a.length === b.length && a.every((id, i) => id === b[i]);

export function sameSelection(a: Selection, b: Selection): boolean {
  if (!a || !b) return a === b;
  if (a.kind !== b.kind) return false;
  if ((a.kind === "connections" || a.kind === "pieces") && (b.kind === "connections" || b.kind === "pieces")) return sameIds(a.ids, b.ids);
  if ("id" in a && "id" in b) return a.id === b.id;
  return false;
}

/**
 * The highlighted IDs for the views and the schedules. `viewsRevision` is the paired views' revision;
 * `assemblies` is the same revision's assembly schedule, for an opening's framing (UI-004 §7).
 */
export function highlightOf(
  selection: Selection,
  schedule: ScheduleEnvelope | null,
  viewsRevision: string | null,
  assemblies: AssemblyScheduleEnvelope | null = null,
): Highlight {
  if (!selection) return NO_HIGHLIGHT;
  switch (selection.kind) {
    case "member":
      return { ...NO_HIGHLIGHT, member: selection.id };
    case "wall":
      return { ...NO_HIGHLIGHT, walls: new Set([selection.id]) };
    case "pieces":
      return { ...NO_HIGHLIGHT, pieces: new Set(selection.ids) };
    case "opening": {
      const rows = assemblies?.status === "CURRENT" && assemblies.source_revision_id === viewsRevision ? (assemblies.payload?.wall_framing ?? []) : [];
      return { ...NO_HIGHLIGHT, openings: new Set([selection.id]), relatedPieces: new Set(rows.filter((p) => p.opening_id === selection.id).map((p) => p.piece_id)) };
    }
    case "connections": {
      const connections = new Set(selection.ids);
      const rows = schedule?.status === "CURRENT" && schedule.source_revision_id === viewsRevision ? (schedule.payload?.connections ?? []) : [];
      const related = new Set(rows.filter((c) => connections.has(c.connection_id)).flatMap((c) => c.member_ids));
      return { ...NO_HIGHLIGHT, related, connections };
    }
  }
}
