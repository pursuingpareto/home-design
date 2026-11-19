/**
 * Pure helpers for the UI-002 editors: stored values from the head snapshot, command arguments, and
 * error placement across tabs. Nothing here duplicates server validation (D028).
 */

import type { ErrorDetail, Snapshot } from "../../api/types";
import { newCommandId } from "../commands";

type Entity = Snapshot["entities"][number];
type Of<K extends Entity["kind"]> = Extract<Entity, { kind: K }>;

export function entitiesOf<K extends Entity["kind"]>(snapshot: Snapshot, kind: K): Of<K>[] {
  return snapshot.entities.filter((e): e is Of<K> => e.kind === kind);
}

export function one<K extends Entity["kind"]>(snapshot: Snapshot, kind: K): Of<K> | null {
  return entitiesOf(snapshot, kind)[0] ?? null;
}

export function envelope<T extends string, A>(projectId: string, baseRevisionId: string, type: T, args: A) {
  return { command_id: newCommandId(), project_id: projectId, base_revision_id: baseRevisionId, type, args };
}

// --- tabs -------------------------------------------------------------------------------------------

export type TabId = "footprint" | "stories" | "roof" | "grid" | "sections";

export const TAB_LABEL: Record<TabId, string> = { footprint: "Footprint", stories: "Stories", roof: "Roof", grid: "Grid", sections: "Sections" };

export const TAB_OF_COMMAND: Record<string, TabId | undefined> = {
  SetFootprintDimensions: "footprint",
  SetStoryHeights: "stories",
  SetGableRoofParameters: "roof",
  SetTimberGrid: "grid",
  AddSection: "sections",
  SetMemberSection: "sections",
};

const TAB_OF_KIND: Partial<Record<Entity["kind"], TabId>> = {
  Footprint: "footprint",
  TimberGrid: "grid",
  Level: "stories",
  GableRoof: "roof",
  Section: "sections",
  FrameSystem: "sections",
};

/**
 * Tabs other than the submitted one whose stored fields appear in the details (UI-002 §7). The entity
 * kind of each `entities[<id>]` path is looked up in the head snapshot; argument paths belong to the
 * submitted command.
 */
export function otherTabs(details: readonly ErrorDetail[], snapshot: Snapshot | null, submitted: TabId | undefined): TabId[] {
  if (!snapshot) return [];
  const kinds = new Map(snapshot.entities.map((e) => [e.id, e.kind]));
  const tabs = new Set<TabId>();
  for (const detail of details) {
    for (const path of [detail.path, ...(detail.related_paths ?? [])]) {
      const id = /^entities\[([0-9a-f-]{36})\]/.exec(path)?.[1];
      const kind = id ? kinds.get(id) : undefined;
      const tab = kind ? TAB_OF_KIND[kind] : undefined;
      if (tab && tab !== submitted) tabs.add(tab);
    }
  }
  return (Object.keys(TAB_LABEL) as TabId[]).filter((t) => tabs.has(t));
}

// --- stories ----------------------------------------------------------------------------------------

export function levels(snapshot: Snapshot) {
  return entitiesOf(snapshot, "Level").sort((a, b) => a.index - b.index);
}

// --- grid ---------------------------------------------------------------------------------------------

export type Axis = "x" | "y";

/** One editable grid line. `fraction` is the stored (or generated) value used while untouched. */
export interface GridRow {
  key: string; // React key, stable across edits
  id?: string; // existing line ID; absent for a new line (the server assigns one, interfaces.md §2.1)
  fraction: number;
  text: string;
  dirty: boolean;
  end: boolean; // the 0 and 1 lines are fixed
}

let rowCounter = 0;
export const rowKey = () => `row-${++rowCounter}`;

export type GridLineArg = { id?: string; fraction: number };

/**
 * Arguments for one axis. Untouched rows send their fraction exactly; edited rows send position /
 * dimension; end rows always send exactly 0 and 1. Rows are sorted by fraction so the arguments are
 * ascending; equal or out-of-range values are left for the server to report (D032).
 */
export function axisArgs(
  rows: readonly GridRow[],
  dimensionM: number,
  parse: (text: string) => { ok: true; meters: number } | { ok: false; error: string },
): { ok: true; args: GridLineArg[]; order: string[] } | { ok: false; errors: Record<string, string> } {
  const errors: Record<string, string> = {};
  const resolved: { row: GridRow; fraction: number }[] = [];
  for (const row of rows) {
    if (row.end || !row.dirty) {
      resolved.push({ row, fraction: row.fraction });
      continue;
    }
    const parsed = parse(row.text);
    if (!parsed.ok) errors[row.key] = parsed.error;
    else resolved.push({ row, fraction: parsed.meters / dimensionM });
  }
  if (Object.keys(errors).length > 0) return { ok: false, errors };
  resolved.sort((a, b) => a.fraction - b.fraction);
  return {
    ok: true,
    args: resolved.map(({ row, fraction }) => (row.id ? { id: row.id, fraction } : { fraction })),
    order: resolved.map(({ row }) => row.key),
  };
}

/** Rows for a stored axis. */
export function rowsFromLines(lines: readonly { id: string; fraction: number }[]): GridRow[] {
  return lines.map((line, k) => ({ key: rowKey(), id: line.id, fraction: line.fraction, text: "", dirty: false, end: k === 0 || k === lines.length - 1 }));
}

/**
 * "Divide into N equal bays" (UI-002 §6.3): interior lines at k/N, reusing existing interior line IDs
 * in order so their members keep their IDs (D042). Extra interior lines are removed.
 */
export function equalBays(rows: readonly GridRow[], bays: number): GridRow[] {
  const first = rows[0];
  const last = rows[rows.length - 1];
  if (!first || !last || bays < 1) return [...rows];
  const interiorIds = rows.filter((r) => !r.end && r.id).map((r) => r.id!);
  const interior: GridRow[] = [];
  for (let k = 1; k < bays; k++) {
    interior.push({ key: rowKey(), id: interiorIds[k - 1], fraction: k / bays, text: "", dirty: false, end: false });
  }
  return [first, ...interior, last];
}

/** A new line at the middle of the bay after `index` (UI-002 §6.3). */
export function insertMidpoint(rows: readonly GridRow[], index: number, valueOf: (row: GridRow) => number | null): GridRow[] {
  const a = rows[index];
  const b = rows[index + 1];
  if (!a || !b) return [...rows];
  const fa = valueOf(a);
  const fb = valueOf(b);
  if (fa === null || fb === null) return [...rows];
  const row: GridRow = { key: rowKey(), fraction: (fa + fb) / 2, text: "", dirty: false, end: false };
  return [...rows.slice(0, index + 1), row, ...rows.slice(index + 1)];
}

/** Place grid details on rows (by argument index at submission) or on the axis. */
export function gridDetails(details: readonly ErrorDetail[], submittedOrder: Record<Axis, string[]>) {
  const rows: Record<string, ErrorDetail[]> = {};
  const axes: Record<Axis, ErrorDetail[]> = { x: [], y: [] };
  const other: ErrorDetail[] = [];
  for (const detail of details) {
    let placed = false;
    for (const path of [detail.path, ...(detail.related_paths ?? [])]) {
      const row = /^args\.([xy])_lines\[(\d+)\]/.exec(path);
      if (row) {
        const key = submittedOrder[row[1] as Axis][Number(row[2])];
        if (key) (rows[key] ??= []).push(detail);
        placed = true;
        break;
      }
      const axis = /^args\.([xy])_lines$/.exec(path);
      if (axis) {
        axes[axis[1] as Axis].push(detail);
        placed = true;
        break;
      }
    }
    if (!placed) other.push(detail);
  }
  return { rows, axes, other };
}
