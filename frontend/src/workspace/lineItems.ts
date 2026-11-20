/**
 * Estimate line items of either kind (artifacts.md §8; ART-002 §7.1, §9). Timber lines are priced per
 * meter of reference-axis length; connection lines per piece ("each").
 */

import type { EstimatePayload, TimberSchedulePayload } from "../api/types";

export type LineItem = EstimatePayload["line_items"][number];
export type ConnectionCatalog = TimberSchedulePayload["connection_catalog"];

/** "BEAM 8x12" for timber; the catalog's description for a connection type, or the type when it is not at hand. */
export function lineLabel(line: LineItem, catalog: ConnectionCatalog | null): string {
  if (line.kind === "timber") return `${line.role} ${line.nominal_section}`;
  return catalog?.types.find((t) => t.connection_type === line.connection_type)?.description ?? line.connection_type;
}
