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
  preliminary_estimate: "Estimate",
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
