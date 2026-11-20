/** The impact preview for a consequential command (interfaces.md §3; UI-001 §5). Display translation only. */

import { useEffect, useRef } from "react";

import { ApiError } from "../api/client";
import { ErrorNotice } from "../app/ErrorNotice";
import { formatLength, type UnitSystem } from "../units/length";
import { ARTIFACT_TYPES, type PreviewResponse, type Snapshot } from "../api/types";
import { ARTIFACT_LABEL, typeLabel } from "../display/labels";
import { describeDetail } from "./commands";
import { otherTabs, TAB_LABEL, TAB_OF_COMMAND } from "./editors/model";
import type { FlowState } from "./useCommandFlow";

type Change = PreviewResponse["changes"][number];

function displayValue(field: string, value: unknown, units: UnitSystem): string {
  if (typeof value === "number" && field.endsWith("_m")) return formatLength(value, units);
  if (typeof value === "string" && field.startsWith("connection_defaults[")) return typeLabel(value);
  if (value === null || value === undefined) return "—";
  const text = JSON.stringify(value);
  return text.length > 80 ? `${text.slice(0, 77)}…` : text;
}

const isRecord = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null && !Array.isArray(v);

/**
 * Display rows for a change. A change to `parameters` or `connection_defaults` is served as the whole
 * object, so it is shown per key that differs, as `parameters.<field>` and `connection_defaults["…"]`
 * (UI-003 §9). Other changes are one row each, as before.
 */
export function changeRows(change: Change): { key: string; kind: string; field: string; before: unknown; after: unknown }[] {
  const { before, after } = change;
  if ((change.field === "parameters" || change.field === "connection_defaults") && isRecord(before) && isRecord(after)) {
    const keys = [...new Set([...Object.keys(before), ...Object.keys(after)])].filter((k) => JSON.stringify(before[k]) !== JSON.stringify(after[k]));
    return keys.map((k) => {
      const field = change.field === "parameters" ? `parameters.${k}` : `connection_defaults["${k}"]`;
      return { key: `${change.entity_id}/${field}`, kind: change.entity_kind, field, before: before[k], after: after[k] };
    });
  }
  return [{ key: `${change.entity_id}/${change.field}`, kind: change.entity_kind, field: change.field, before, after }];
}

/** "Updates: … Unchanged: …" in the revision bar's order, or none (UI-003 §9; DEP-001 §9.2). */
export function artifactsText(impacted: readonly string[]): string {
  if (impacted.length === 0) return "No derived views or reports change.";
  const updates = ARTIFACT_TYPES.filter((t) => impacted.includes(t)).map((t) => ARTIFACT_LABEL[t]);
  const unchanged = ARTIFACT_TYPES.filter((t) => !impacted.includes(t)).map((t) => ARTIFACT_LABEL[t]);
  return `Updates: ${updates.join(", ")}.${unchanged.length > 0 ? ` Unchanged: ${unchanged.join(", ")}.` : ""}`;
}

export function ImpactDialog({
  state,
  units,
  snapshot,
  onConfirm,
  onCancel,
}: {
  state: FlowState;
  units: UnitSystem;
  snapshot?: Snapshot | null;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => heading.current?.focus(), [state.step]);
  if (state.step === "idle") return null;

  if (state.step === "applying") {
    return (
      <p className="saving" role="status">
        Saving…
      </p>
    );
  }

  if (state.step === "previewing") {
    return (
      <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="impact-heading">
        <h2 id="impact-heading" ref={heading} tabIndex={-1}>
          Previewing…
        </h2>
      </div>
    );
  }

  if (state.step === "error") {
    const details = state.error instanceof ApiError ? state.error.details : [];
    const pointers = otherTabs(details, snapshot ?? null, TAB_OF_COMMAND[state.command.type]);
    return (
      <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="impact-heading">
        <h2 id="impact-heading" ref={heading} tabIndex={-1}>
          The change was not applied
        </h2>
        {state.notice && <p className="notice">{state.notice}</p>}
        <ErrorNotice error={state.error} />
        {details.length > 0 && (
          <ul data-testid="dialog-details">
            {details.map((d, i) => (
              <li key={i}>
                <code>{d.path || "(document)"}</code>: {describeDetail(d)}
              </li>
            ))}
          </ul>
        )}
        {pointers.map((tab) => (
          <p key={tab} className="notice" data-testid="tab-pointer">
            Also see the {TAB_LABEL[tab]} tab: its values are part of this problem.
          </p>
        ))}
        <button type="button" onClick={onCancel}>
          Close
        </button>
      </div>
    );
  }

  const { preview } = state;
  const committing = state.step === "committing";
  return (
    <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="impact-heading" data-testid="impact-dialog">
      <h2 id="impact-heading" ref={heading} tabIndex={-1}>
        {preview.is_noop ? "No changes" : "Review the impact"}
      </h2>
      {state.step === "review" && state.notice && <p className="notice">{state.notice}</p>}
      {preview.is_noop ? (
        <p>This change matches the current revision, so nothing will be saved.</p>
      ) : (
        <>
          <p>
            Classification: <strong>{preview.classification}</strong> ({preview.classification_version})
          </p>
          <table data-testid="impact-changes">
            <caption>Field changes</caption>
            <thead>
              <tr>
                <th scope="col">Record</th>
                <th scope="col">Field</th>
                <th scope="col">Before</th>
                <th scope="col">After</th>
              </tr>
            </thead>
            <tbody>
              {preview.changes.flatMap(changeRows).map((c) => (
                <tr key={c.key}>
                  <td>{c.kind}</td>
                  <td>{c.field || "(record)"}</td>
                  <td>{displayValue(c.field, c.before, units)}</td>
                  <td>{displayValue(c.field, c.after, units)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p data-testid="impact-members">
            Timber members: {preview.members.added.length} added, {preview.members.removed.length} removed, {preview.members.updated.length} updated.
          </p>
          <p data-testid="impact-connections">
            Connections: {preview.connections.added.length} added, {preview.connections.removed.length} removed, {preview.connections.updated.length} updated.
          </p>
          {/* DEP-001 §9.2: exactly the artifacts whose payload changes; the others are reused unchanged. */}
          <p data-testid="impact-artifacts">{artifactsText(preview.impacted_artifacts)}</p>
        </>
      )}
      <ul className="warnings">
        {preview.warnings.map((w) => (
          <li key={w.code}>{w.message}</li>
        ))}
      </ul>
      <div className="actions">
        {!preview.is_noop && (
          <button type="button" onClick={onConfirm} disabled={committing}>
            {committing ? "Saving…" : "Confirm"}
          </button>
        )}
        <button type="button" onClick={onCancel} disabled={committing}>
          {preview.is_noop ? "Close" : "Cancel"}
        </button>
      </div>
    </div>
  );
}
