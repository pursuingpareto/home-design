/**
 * The workspace's selection (UI-003 §6): one member, or a set of connections. A connection's members
 * come from the same revision's schedule rows (`member_ids`); without a CURRENT schedule for the
 * views' revision, only the connections themselves are highlighted.
 */

import type { ScheduleEnvelope } from "../api/types";
import type { Highlight, Pick } from "../views/highlight";

export type Selection = Pick | null;

export function sameSelection(a: Selection, b: Selection): boolean {
  if (!a || !b) return a === b;
  if (a.kind === "member" && b.kind === "member") return a.id === b.id;
  if (a.kind === "connections" && b.kind === "connections") return a.ids.length === b.ids.length && a.ids.every((id, i) => id === b.ids[i]);
  return false;
}

/** The highlighted IDs for the views and the schedule. `viewsRevision` is the paired views' revision. */
export function highlightOf(selection: Selection, schedule: ScheduleEnvelope | null, viewsRevision: string | null): Highlight {
  if (!selection) return { member: null, related: new Set(), connections: new Set() };
  if (selection.kind === "member") return { member: selection.id, related: new Set(), connections: new Set() };
  const connections = new Set(selection.ids);
  const rows = schedule?.status === "CURRENT" && schedule.source_revision_id === viewsRevision ? (schedule.payload?.connections ?? []) : [];
  const related = new Set(rows.filter((c) => connections.has(c.connection_id)).flatMap((c) => c.member_ids));
  return { member: null, related, connections };
}
