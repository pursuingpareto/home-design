/**
 * Wall, opening, and definition labels (UI-004 §8.3, §12), from the assembly schedule (views and the
 * schedule panel) or from the head snapshot (editors and the dialog). Display text only.
 */

import type { AssemblyScheduleEnvelope, Snapshot } from "../api/types";
import { familyLabel, openingKindLabel, openingLabel, sideOfKey, wallLabel } from "../display/labels";
import { formatLength, type UnitSystem } from "../units/length";
import { NO_DETAILS, type WallDetails } from "../views/walls";
import { entitiesOf, one } from "./editors/model";

type Payload = NonNullable<AssemblyScheduleEnvelope["payload"]>;

/** Labels of the schedule's walls and openings, by ID. */
export function scheduleLabels(payload: Payload, units: UnitSystem): { walls: Map<string, string>; openings: Map<string, string> } {
  const walls = new Map(payload.walls.map((w) => [w.wall_id, wallLabel(w.elevation_side, w.level_index, w.generation_key)]));
  const openings = new Map(
    payload.openings.map((o) => [o.opening_id, openingLabel(o.opening_kind, formatLength(o.width_m, units), formatLength(o.height_m, units), walls.get(o.wall_id) ?? o.wall_key)]),
  );
  return { walls, openings };
}

/**
 * The views' joins (D086): labels, piece sections and keys, and layer materials from the assembly
 * schedule, only when it is CURRENT for the views' revision.
 */
export function wallDetails(assemblies: AssemblyScheduleEnvelope | null, viewsRevision: string | null, units: UnitSystem): WallDetails {
  const payload = assemblies?.status === "CURRENT" && assemblies.source_revision_id === viewsRevision ? assemblies.payload : null;
  if (!payload) return NO_DETAILS;
  const { walls, openings } = scheduleLabels(payload, units);
  return {
    walls,
    openings,
    pieces: new Map(payload.wall_framing.map((p) => [p.piece_id, { section: p.nominal_section, key: p.generation_key }])),
    layerMaterials: new Map(payload.definitions.flatMap((d) => d.layers.map((l) => [l.name, l.material_name] as const))),
  };
}

export interface SnapshotLabels {
  wall: (id: string) => string | undefined;
  opening: (id: string) => string | undefined;
  definition: (id: string) => string | undefined;
}

/** Labels from the head snapshot: walls by their key, side, and level; openings by kind, size, and wall. */
export function snapshotLabels(snapshot: Snapshot | null, units: UnitSystem): SnapshotLabels {
  if (!snapshot) return { wall: () => undefined, opening: () => undefined, definition: () => undefined };
  const grid = one(snapshot, "TimberGrid");
  const xs = grid?.x_lines.map((l) => l.id) ?? [];
  const ys = grid?.y_lines.map((l) => l.id) ?? [];
  const levels = new Map(entitiesOf(snapshot, "Level").map((l) => [l.id, l.index]));
  const walls = new Map(entitiesOf(snapshot, "Wall").map((w) => [w.id, wallLabel(sideOfKey(w.generation_key, xs, ys), levels.get(w.level_id) ?? null, w.generation_key)]));
  const openings = new Map(entitiesOf(snapshot, "Opening").map((o) => [o.id, o]));
  const definitions = new Map(entitiesOf(snapshot, "AssemblyDefinition").map((d) => [d.id, familyLabel(d.family)]));
  return {
    wall: (id) => walls.get(id),
    opening: (id) => {
      const o = openings.get(id);
      return o ? openingLabel(o.opening_kind, formatLength(o.width_m, units), formatLength(o.height_m, units), walls.get(o.wall_id) ?? null) : undefined;
    },
    definition: (id) => definitions.get(id),
  };
}

/** An opening record as a preview serves it (added or removed), labeled from its own fields. */
export function recordLabel(record: unknown, labels: SnapshotLabels, units: UnitSystem): string | null {
  if (typeof record !== "object" || record === null) return null;
  const r = record as Record<string, unknown>;
  if (r.kind !== "Opening" || typeof r.width_m !== "number" || typeof r.height_m !== "number") return null;
  const wall = typeof r.wall_id === "string" ? (labels.wall(r.wall_id) ?? null) : null;
  return openingLabel(String(r.opening_kind ?? ""), formatLength(r.width_m, units), formatLength(r.height_m, units), wall) || openingKindLabel(String(r.opening_kind));
}

/** "offset" for "offset_m", "girt count" for "girt_count". */
const fieldText = (rest: string) =>
  rest
    .replace(/^\./, "")
    .replace(/_m\b/g, "")
    .replace(/_/g, " ");

/**
 * A path into an opening, a wall, or a definition, with its label before the field (UI-004 §8.3), for
 * example "Window 3' 0" × 4' 0", south wall, Level 0, x0–x1: offset"; null for any other path.
 */
export function pathLabel(path: string, labels: SnapshotLabels): string | null {
  const match = /^entities\[([0-9a-f-]{36})\](.*)$/.exec(path);
  if (!match) return null;
  const id = match[1]!;
  const name = labels.opening(id) ?? labels.wall(id) ?? labels.definition(id);
  if (!name) return null;
  const field = fieldText(match[2]!);
  return field ? `${name}: ${field}` : name;
}
