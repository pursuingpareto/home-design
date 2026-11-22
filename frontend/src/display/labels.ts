/**
 * Display labels (UI-003 §8.3, item 8): the one module every view, table, editor, and the dialog use.
 * Labels are display text only. Commands, price-book keys, and payload values keep their codes.
 */

import { CONNECTION_CATALOG } from "../api/connectionCatalog";
import type { ArtifactType, ScheduleRow } from "../api/types";
import type { components } from "../api/schema";

export type Role = ScheduleRow["role"];
export type JunctionClass = components["schemas"]["ConnectionTypeArgs"]["junction_class"];
export type ConnectionType = components["schemas"]["ConnectionTypeArgs"]["connection_type"];
export type Family = "traditional" | "engineered";

/** Today's `TYPE_LABEL` of panels.tsx, moved (UI-003 §8.3). */
export const ARTIFACT_LABEL: Record<ArtifactType, string> = {
  plan2d: "2D plan",
  mesh3d: "3D model",
  timber_schedule: "Timber schedule",
  assembly_schedule: "Assembly schedule",
  preliminary_estimate: "Estimate",
};

export type PieceKind = components["schemas"]["WallFramingRow"]["piece_kind"];

/** Wall framing kinds (D066), for estimate lines and, later, the wall views (UI-004). */
export const PIECE_KIND_LABEL: Record<PieceKind, string> = {
  STUD: "Stud",
  GIRT: "Girt",
  KING: "King stud",
  JACK: "Jack stud",
  HEADER: "Header",
  ROUGH_SILL: "Rough sill",
  CRIPPLE: "Cripple",
  BUCK_JAMB: "Buck jamb",
  BUCK_HEAD: "Buck head",
  BUCK_SILL: "Buck sill",
};

export const ROLE_LABEL: Record<Role, string> = {
  POST: "Post",
  BEAM: "Beam",
  SILL: "Sill",
  FLOOR_JOIST: "Floor joist",
  PRINCIPAL_RAFTER: "Principal rafter",
  PURLIN: "Purlin",
  KNEE_BRACE: "Knee brace",
};

/** The display order of roles in legends (UI-003 §8.3's table order). */
export const ROLES: readonly Role[] = ["POST", "BEAM", "SILL", "FLOOR_JOIST", "PRINCIPAL_RAFTER", "PURLIN", "KNEE_BRACE"];

export const JUNCTION_LABEL: Record<JunctionClass, string> = {
  "post-beam": "Post–beam",
  "post-sill": "Post–sill",
  brace: "Knee brace ends",
  "joist-beam": "Joist–beam",
  "rafter-peak": "Rafter peak",
  "rafter-foot": "Rafter foot",
  "purlin-rafter": "Purlin–rafter",
};

/** The members each class joins, as D054 and vs-02.md §9.3 describe them. */
export const JUNCTION_MEMBERS: Record<JunctionClass, string> = {
  "post-beam": "Beam end into post (Level 1 and eave planes)",
  "post-sill": "Post foot into sill (Level 0)",
  brace: "Each brace end, into post or beam",
  "joist-beam": "Each joist end into a beam",
  "rafter-peak": "Principal rafter pair at the ridge",
  "rafter-foot": "Principal rafter foot onto the eave beam or post",
  "purlin-rafter": "Each purlin end into a principal rafter",
};

export const CONNECTION_TYPE_LABEL: Record<ConnectionType, string> = {
  PEGGED_MORTISE_TENON: "Pegged mortise and tenon",
  BRIDLE: "Bridle joint",
  HOUSED_DOVETAIL: "Housed dovetail",
  STEEL_KNIFE_PLATE: "Steel knife plate",
  JOIST_HANGER: "Joist hanger",
};

/** The class order of the D054 table, from the generated catalog (D062). */
export const JUNCTION_CLASSES: readonly JunctionClass[] = CONNECTION_CATALOG.junction_classes.map((c) => c.junction_class);

export function familyOf(type: ConnectionType): Family {
  return CONNECTION_CATALOG.connection_types.find((t) => t.connection_type === type)?.family ?? "traditional";
}

/** The full catalog description ("… Representational only: no capacity, sizes, or fasteners."). */
export function descriptionOf(type: ConnectionType): string {
  return CONNECTION_CATALOG.connection_types.find((t) => t.connection_type === type)?.description ?? type;
}

/** The two types a class allows, default first (D054). */
export function allowedTypes(junctionClass: JunctionClass): ConnectionType[] {
  const row = CONNECTION_CATALOG.junction_classes.find((c) => c.junction_class === junctionClass);
  return row ? [row.default, row.alternative] : [];
}

/** "Pegged mortise and tenon (traditional)", as the type select shows it (UI-003 §7.2). */
export function typeOptionLabel(type: ConnectionType): string {
  return `${CONNECTION_TYPE_LABEL[type]} (${familyOf(type)})`;
}

const label = <K extends string>(table: Record<K, string>, code: string): string => (table as Record<string, string>)[code] ?? code;
export const roleLabel = (code: string) => label(ROLE_LABEL, code);
export const junctionLabel = (code: string) => label(JUNCTION_LABEL, code);
export const typeLabel = (code: string) => label(CONNECTION_TYPE_LABEL, code);
export const pieceKindLabel = (code: string) => label(PIECE_KIND_LABEL, code);

// --- VS-02b walls (UI-004 §12, item 15) ---------------------------------------------------------------

export type AssemblyFamily = components["schemas"]["AssemblyDefinition"]["family"];
export type LayerFunction = components["schemas"]["Layer"]["function"];
export type OpeningKind = components["schemas"]["Opening"]["opening_kind"];
export type ElevationSide = components["schemas"]["AssemblyWallRow"]["elevation_side"];
export type FramingGroup = "layout" | "opening" | "buck";

export const FAMILY_LABEL: Record<AssemblyFamily, string> = { STRAW_BALE: "Straw bale", STUD_INFILL: "Stud infill" };

export const LAYER_FUNCTION_LABEL: Record<LayerFunction, string> = {
  FINISH: "Finish",
  SHEATHING: "Sheathing",
  INSULATION: "Insulation",
  FRAMING: "Framing layer",
};

/** The display order of layer functions in legends. */
export const LAYER_FUNCTIONS: readonly LayerFunction[] = ["FINISH", "SHEATHING", "INSULATION", "FRAMING"];

export const OPENING_KIND_LABEL: Record<OpeningKind, string> = { WINDOW: "Window", DOOR: "Door" };

export const SIDE_LABEL: Record<ElevationSide, string> = { south: "South", north: "North", east: "East", west: "West" };

export const FRAMING_GROUP_LABEL: Record<FramingGroup, string> = {
  layout: "Layout framing (studs, girts)",
  opening: "Opening framing (kings, jacks, headers, rough sills, cripples)",
  buck: "Bucks",
};

export const FRAMING_GROUPS: readonly FramingGroup[] = ["layout", "opening", "buck"];

const GROUP_OF_KIND: Record<PieceKind, FramingGroup> = {
  STUD: "layout",
  GIRT: "layout",
  KING: "opening",
  JACK: "opening",
  HEADER: "opening",
  ROUGH_SILL: "opening",
  CRIPPLE: "opening",
  BUCK_JAMB: "buck",
  BUCK_HEAD: "buck",
  BUCK_SILL: "buck",
};

export const framingGroupOf = (kind: PieceKind): FramingGroup => GROUP_OF_KIND[kind];
export const familyLabel = (code: string) => label(FAMILY_LABEL, code);
export const layerFunctionLabel = (code: string) => label(LAYER_FUNCTION_LABEL, code);
export const openingKindLabel = (code: string) => label(OPENING_KIND_LABEL, code);

/** The bay of a D080 wall key (`wall/axis-x/{y}/{xa}-{xb}/level-{i}`), as its two grid-line IDs. */
export function wallBay(generationKey: string): { axis: "x" | "y"; line: string; a: string; b: string; level: number } | null {
  const match = /^wall\/axis-([xy])\/([^/]+)\/([^/-]+)-([^/]+)\/level-(\d+)$/.exec(generationKey);
  if (!match) return null;
  return { axis: match[1] as "x" | "y", line: match[2]!, a: match[3]!, b: match[4]!, level: Number(match[5]) };
}

/**
 * The side of a wall from its key and the grid's line order, as the assembly schedule computes
 * `elevation_side`: a wall along X on the first Y line faces south, on the last north; a wall along Y on
 * the first X line faces west, on the last east. For labels where only the snapshot is at hand.
 */
export function sideOfKey(generationKey: string, xLineIds: readonly string[], yLineIds: readonly string[]): ElevationSide | null {
  const bay = wallBay(generationKey);
  if (!bay) return null;
  const lines = bay.axis === "x" ? yLineIds : xLineIds;
  if (bay.line === lines[0]) return bay.axis === "x" ? "south" : "west";
  if (bay.line === lines[lines.length - 1]) return bay.axis === "x" ? "north" : "east";
  return null;
}

/** "South wall, Level 0, x0–x1" (UI-004 §12). Falls back to the key when it is not a D080 wall key. */
export function wallLabel(side: ElevationSide | null, levelIndex: number | null, generationKey: string): string {
  const bay = wallBay(generationKey);
  if (!bay || !side) return generationKey;
  return `${SIDE_LABEL[side]} wall, Level ${levelIndex ?? bay.level}, ${bay.a}–${bay.b}`;
}

/** "Window 3' 0" × 4' 0", south wall, Level 0, x1–x2" (UI-004 §12); sizes are already formatted. */
export function openingLabel(kind: string, width: string, height: string, wall: string | null): string {
  const lowered = wall ? `${wall.charAt(0).toLowerCase()}${wall.slice(1)}` : null;
  return `${openingKindLabel(kind)} ${width} × ${height}${lowered ? `, ${lowered}` : ""}`;
}
