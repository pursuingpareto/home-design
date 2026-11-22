/**
 * A view's legend (UI-003 §4, §5.1; UI-004 §6): the roles, connection types, wall layers (or "Walls" in
 * the plan), and framing groups present, read from the payload. What a switch hides is omitted.
 */

import {
  CONNECTION_TYPE_LABEL,
  familyOf,
  FRAMING_GROUP_LABEL,
  FRAMING_GROUPS,
  LAYER_FUNCTION_LABEL,
  LAYER_FUNCTIONS,
  ROLE_LABEL,
  ROLES,
  type ConnectionType,
  type FramingGroup,
  type LayerFunction,
  type Role,
} from "../display/labels";
import { css, FRAMING_COLOR, LAYER_COLOR, MIXED_COLOR, ROLE_COLOR, TYPE_COLOR, WALL_BAND_COLOR } from "../display/palette";

export function Legend({
  testId,
  roles,
  types,
  mixed,
  walls = false,
  layers = new Set(),
  framing = new Set(),
}: {
  testId: string;
  roles: ReadonlySet<Role>;
  types: readonly ConnectionType[];
  mixed: boolean;
  /** The plan's wall bands are shown. */
  walls?: boolean;
  /** The 3D view's layer functions shown. */
  layers?: ReadonlySet<LayerFunction>;
  /** The framing groups shown. */
  framing?: ReadonlySet<FramingGroup>;
}) {
  return (
    <ul className="legend" data-testid={testId} aria-label="Legend">
      {ROLES.filter((r) => roles.has(r)).map((role) => (
        <li key={role} data-role={role}>
          <span className="swatch" style={{ background: css(ROLE_COLOR[role]) }} aria-hidden="true" />
          {ROLE_LABEL[role]}
        </li>
      ))}
      {types.map((type) => (
        <li key={type} data-connection-type={type}>
          <span className="swatch marker" style={{ background: css(TYPE_COLOR[type]) }} aria-hidden="true" />
          {CONNECTION_TYPE_LABEL[type]} ({familyOf(type)})
        </li>
      ))}
      {mixed && (
        <li data-connection-type="mixed">
          <span className="swatch marker mixed" style={{ borderColor: css(MIXED_COLOR) }} aria-hidden="true" />
          Several types at one point
        </li>
      )}
      {walls && (
        <li data-wall-legend="walls">
          <span className="swatch" style={{ background: css(WALL_BAND_COLOR) }} aria-hidden="true" />
          Walls
        </li>
      )}
      {LAYER_FUNCTIONS.filter((f) => layers.has(f)).map((f) => (
        <li key={f} data-layer-function={f}>
          <span className="swatch" style={{ background: css(LAYER_COLOR[f]) }} aria-hidden="true" />
          {LAYER_FUNCTION_LABEL[f]}
        </li>
      ))}
      {FRAMING_GROUPS.filter((g) => framing.has(g)).map((g) => (
        <li key={g} data-framing-group={g}>
          <span className="swatch" style={{ background: css(FRAMING_COLOR[g]) }} aria-hidden="true" />
          {FRAMING_GROUP_LABEL[g]}
        </li>
      ))}
    </ul>
  );
}

/** Types in first-appearance order. */
export function typesOf(markers: readonly { connection_type: ConnectionType }[]): ConnectionType[] {
  return [...new Set(markers.map((m) => m.connection_type))];
}
