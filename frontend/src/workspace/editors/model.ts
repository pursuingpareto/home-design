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

export type TabId = "footprint" | "stories" | "roof" | "grid" | "frame" | "sections" | "connections" | "walls";

/** The tabs, in order (UI-003 §7; D062: a Connections tab; D087: a Walls tab). */
export const TAB_LABEL: Record<TabId, string> = {
  footprint: "Footprint",
  stories: "Stories",
  roof: "Roof",
  grid: "Grid",
  frame: "Frame",
  sections: "Sections",
  connections: "Connections",
  walls: "Walls",
};

export const TAB_OF_COMMAND: Record<string, TabId | undefined> = {
  SetFootprintDimensions: "footprint",
  SetStoryHeights: "stories",
  SetGableRoofParameters: "roof",
  SetTimberGrid: "grid",
  SetFrameParameters: "frame",
  AddSection: "sections",
  SetMemberSection: "sections",
  SetConnectionType: "connections",
  SetWallAssembly: "walls",
  AddOpening: "walls",
  SetOpening: "walls",
  RemoveOpening: "walls",
};

const TAB_OF_KIND: Partial<Record<Entity["kind"], TabId>> = {
  Footprint: "footprint",
  TimberGrid: "grid",
  Level: "stories",
  GableRoof: "roof",
  Section: "sections",
  FrameSystem: "sections",
  // UI-004 §8.3: wall records point to the Walls tab.
  Opening: "walls",
  WallSystem: "walls",
  AssemblyDefinition: "walls",
  Wall: "walls",
  WallFramingPiece: "walls",
};

/** A `FrameSystem` path maps to a tab by its field (UI-003 §7.3); anything else stays on Sections. */
function frameTab(rest: string): TabId {
  if (/^\.parameters\b/.test(rest)) return "frame";
  if (/^\.connection_defaults\b/.test(rest)) return "connections";
  return "sections"; // member_defaults, and anything else on FrameSystem
}

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
      const match = /^entities\[([0-9a-f-]{36})\](.*)$/.exec(path);
      const kind = match ? kinds.get(match[1]!) : undefined;
      const tab = kind === "FrameSystem" ? frameTab(match![2]!) : kind ? TAB_OF_KIND[kind] : undefined;
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

// --- frame (UI-003 §7.1) -------------------------------------------------------------------------------

/** A purlin count is a whole number; its range is the server's to check (D028). */
export function parseWholeNumber(text: string): { ok: true; value: number } | { ok: false; error: string } {
  const trimmed = text.trim();
  return /^-?\d+$/.test(trimmed) ? { ok: true, value: Number(trimmed) } : { ok: false, error: "Enter a whole number" };
}

// --- connections (UI-003 §7.2) --------------------------------------------------------------------------

/** The head snapshot's connection count per junction class. */
export function connectionCounts(snapshot: Snapshot): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const c of entitiesOf(snapshot, "Connection")) counts[c.junction_class] = (counts[c.junction_class] ?? 0) + 1;
  return counts;
}

// --- walls (UI-004 §8) --------------------------------------------------------------------------------

type Opening = Of<"Opening">;
type Wall = Of<"Wall">;

/** Walls in key order (code-unit order, D030), each with its openings by offset, then ID. */
export function openingsByWall(snapshot: Snapshot): { wall: Wall; openings: Opening[] }[] {
  const walls = entitiesOf(snapshot, "Wall").sort((a, b) => (a.generation_key < b.generation_key ? -1 : a.generation_key > b.generation_key ? 1 : 0));
  const openings = entitiesOf(snapshot, "Opening");
  return walls.map((wall) => ({
    wall,
    openings: openings.filter((o) => o.wall_id === wall.id).sort((a, b) => a.offset_m - b.offset_m || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0)),
  }));
}

/** A wall's length between its post axes, from the snapshot's `start_m` and `end_m`. */
export function wallLength(wall: Wall): number {
  return Math.hypot((wall.end_m[0] ?? 0) - (wall.start_m[0] ?? 0), (wall.end_m[1] ?? 0) - (wall.start_m[1] ?? 0));
}

/** "Center in wall" (UI-004 §8.2): an input helper, sent as computed and checked by the server. */
export function centeredOffset(wallLengthM: number, widthM: number): number {
  return (wallLengthM - widthM) / 2;
}

/** The post an offset is measured from (D080): a wall along X starts at its west post, along Y at its south post. */
export function offsetOrigin(generationKey: string): "west" | "south" {
  return generationKey.startsWith("wall/axis-y/") ? "south" : "west";
}

export interface OpeningValues {
  width_m: number;
  height_m: number;
  sill_height_m: number;
  offset_m: number;
}

export function setOpeningArgs(openingId: string, v: OpeningValues) {
  return { opening_id: openingId, width_m: v.width_m, height_m: v.height_m, sill_height_m: v.sill_height_m, offset_m: v.offset_m };
}

export function addOpeningArgs(wallId: string, kind: Opening["opening_kind"], v: OpeningValues) {
  return { wall_id: wallId, opening_kind: kind, width_m: v.width_m, height_m: v.height_m, sill_height_m: kind === "DOOR" ? 0 : v.sill_height_m, offset_m: v.offset_m };
}

/** The opening on `wallId` that is new since `before` (after an add commits, it becomes current). */
export function newOpeningOn(snapshot: Snapshot, wallId: string, before: ReadonlySet<string>): string | null {
  return entitiesOf(snapshot, "Opening").find((o) => o.wall_id === wallId && !before.has(o.id))?.id ?? null;
}
