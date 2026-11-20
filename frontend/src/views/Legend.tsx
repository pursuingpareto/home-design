/** A view's legend (UI-003 §4, §5.1): the roles and connection types present, read from the payload. */

import { CONNECTION_TYPE_LABEL, familyOf, ROLE_LABEL, ROLES, type ConnectionType, type Role } from "../display/labels";
import { css, MIXED_COLOR, ROLE_COLOR, TYPE_COLOR } from "../display/palette";

export function Legend({ testId, roles, types, mixed }: { testId: string; roles: ReadonlySet<Role>; types: readonly ConnectionType[]; mixed: boolean }) {
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
    </ul>
  );
}

/** Types in first-appearance order. */
export function typesOf(markers: readonly { connection_type: ConnectionType }[]): ConnectionType[] {
  return [...new Set(markers.map((m) => m.connection_type))];
}
