/**
 * Estimate line items of every kind (artifacts.md §8; ART-002 §7.1, §9; ART-003 §7.1, §10). Timber and wall
 * framing lines are priced per meter of reference-axis length; connection lines per piece ("each");
 * assembly lines per square meter of reference area ("m2").
 */

import type { EstimatePayload, TimberSchedulePayload } from "../api/types";
import { pieceKindLabel, roleLabel } from "../display/labels";
import { formatArea, formatLength, type UnitSystem } from "../units/length";

export type LineItem = EstimatePayload["line_items"][number];
export type ConnectionCatalog = TimberSchedulePayload["connection_catalog"];

/**
 * "Beam 8x12" for timber (UI-003 §8.3); the catalog's description for a connection type, or the type when it
 * is not at hand; "Straw (straw-bale, bales)" for an assembly layer; "Buck jamb 1.5x18" for wall framing (D085).
 */
export function lineLabel(line: LineItem, catalog: ConnectionCatalog | null): string {
  switch (line.kind) {
    case "timber":
      return `${roleLabel(line.role)} ${line.nominal_section}`;
    case "assembly":
      return `${line.material_name} (${line.assembly_label}, ${line.layer})`;
    case "wallframing":
      return `${pieceKindLabel(line.piece_kind)} ${line.nominal_section}`;
    case "connection":
      return catalog?.types.find((t) => t.connection_type === line.connection_type)?.description ?? line.connection_type;
  }
}

/** The quantity cell: pieces, an area, or a length, with the piece count beside wall framing lengths (D070). */
export function lineQuantity(line: LineItem, units: UnitSystem): string {
  switch (line.kind) {
    case "connection":
      return `${line.quantity_value} each`;
    case "assembly":
      return formatArea(line.quantity_value, units);
    case "wallframing":
      return `${formatLength(line.quantity_value, units)} · ${line.count} pcs`;
    case "timber":
      return formatLength(line.quantity_value, units);
  }
}
