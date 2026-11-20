/**
 * Connection types per junction class (`SetConnectionType`; UI-003 §7.2, D059, D062). Consequential,
 * so each row previews. A select offers exactly the class's two catalog types, from the generated
 * catalog (D062); the server still validates every command (D028).
 */

import { useState } from "react";

import type { Command } from "../../api/types";
import {
  allowedTypes,
  descriptionOf,
  JUNCTION_CLASSES,
  JUNCTION_LABEL,
  JUNCTION_MEMBERS,
  typeOptionLabel,
  type ConnectionType,
  type JunctionClass,
} from "../../display/labels";
import { describeDetail } from "../commands";
import type { FlowState } from "../useCommandFlow";
import { connectionCounts, envelope, one } from "./model";
import { detailsFor, isBusy, type EditorProps } from "./shared";

/** The class of the last failed `SetConnectionType`, so its details show on that row. */
function failedClass(state: FlowState): string | null {
  const failure = state.step === "error" ? state : state.step === "idle" ? state.failed : undefined;
  const command = failure?.command as Command | undefined;
  return command?.type === "SetConnectionType" ? command.args.junction_class : null;
}

export function ConnectionsEditor({ projectId, snapshot, flow, onOpenPrices }: EditorProps & { onOpenPrices: (() => void) | null }) {
  const frame = snapshot ? one(snapshot, "FrameSystem") : null;
  const defaults = (frame?.connection_defaults ?? {}) as Partial<Record<JunctionClass, ConnectionType>>;
  const classes = JUNCTION_CLASSES.filter((c) => defaults[c] !== undefined);
  const counts = snapshot ? connectionCounts(snapshot) : {};
  const [choice, setChoice] = useState<Partial<Record<JunctionClass, ConnectionType>>>({});
  const details = detailsFor(flow.state, ["SetConnectionType"]);
  const errorClass = details.length > 0 ? failedClass(flow.state) : null;
  const busy = isBusy(flow.state);
  const chosen = classes.map((c) => choice[c] ?? defaults[c]!);

  function preview(junctionClass: JunctionClass) {
    const type = choice[junctionClass];
    if (!snapshot || !type) return;
    void flow.preview(envelope(projectId, snapshot.revision_id, "SetConnectionType", { junction_class: junctionClass, connection_type: type }));
  }

  return (
    <div className="editor connections-editor" aria-label="Connections editor" role="group">
      <p className="hint">One type per junction class, for every connection of that class. Types are representational only.</p>
      <table data-testid="connection-types">
        <thead>
          <tr>
            <th scope="col">Junction</th>
            <th scope="col">Connections</th>
            <th scope="col">Type</th>
          </tr>
        </thead>
        <tbody>
          {classes.map((junctionClass, i) => {
            const stored = defaults[junctionClass]!;
            const selected = chosen[i]!;
            const count = counts[junctionClass] ?? 0;
            const id = `connection-type-${junctionClass}`;
            const rowDetails = errorClass === junctionClass ? details : [];
            return (
              <tr key={junctionClass} data-junction-class={junctionClass}>
                <td>
                  <label htmlFor={id}>{JUNCTION_LABEL[junctionClass]}</label>
                  <div className="hint">{JUNCTION_MEMBERS[junctionClass]}</div>
                </td>
                <td data-testid={`connection-count-${junctionClass}`}>
                  {count > 0 ? (
                    count
                  ) : (
                    <>
                      None in the current frame
                      <div className="hint">The type applies when the frame generates connections of this class.</div>
                    </>
                  )}
                </td>
                <td>
                  <select id={id} value={selected} onChange={(e) => setChoice((c) => ({ ...c, [junctionClass]: e.target.value as ConnectionType }))}>
                    {allowedTypes(junctionClass).map((type) => (
                      <option key={type} value={type}>
                        {typeOptionLabel(type)}
                      </option>
                    ))}
                  </select>
                  <button type="button" aria-label={`Preview ${JUNCTION_LABEL[junctionClass]} change`} disabled={busy || selected === stored} onClick={() => preview(junctionClass)}>
                    Preview
                  </button>
                  {rowDetails.length > 0 && (
                    <p className="field-error" role="alert">
                      The type change was rejected: {rowDetails.map(describeDetail).join("; ")}
                    </p>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <ul className="hint" data-testid="connection-type-descriptions">
        {[...new Set(chosen)].map((type) => (
          <li key={type} data-connection-type={type}>
            {descriptionOf(type)}
          </li>
        ))}
      </ul>
      <p className="hint" data-testid="connection-pricing-note">
        Connections are priced by type (for example <code>connection.PEGGED_MORTISE_TENON</code>). After a class changes type, the new type's line is unpriced until you price it, and
        the old type's row may become unused.{" "}
        {onOpenPrices && (
          <button type="button" className="link" onClick={onOpenPrices}>
            Set unit prices
          </button>
        )}
      </p>
    </div>
  );
}
