/**
 * Footprint width and depth (D043 `SetFootprintDimensions`; UI-001 §5, §7). An untouched field sends
 * the stored value unchanged, so display rounding never feeds back into a command.
 */

import { useEffect, useState, type FormEvent } from "react";

import { ApiError } from "../api/client";
import type { ErrorDetail, Snapshot } from "../api/types";
import { lengthInputText, parseLength, type UnitSystem } from "../units/length";
import { describeDetail, footprintCommand, placeDetails } from "./commands";
import type { FlowState } from "./useCommandFlow";

type Field = "width" | "depth";
const ARG_PATHS: Record<Field, string> = { width: "args.width_m", depth: "args.depth_m" };

interface FieldState {
  text: string;
  dirty: boolean;
}

export function footprintOf(snapshot: Snapshot) {
  const footprint = snapshot.entities.find((e) => e.kind === "Footprint");
  return footprint && footprint.kind === "Footprint" ? footprint : null;
}

export function EditPanel({
  projectId,
  snapshot,
  units,
  flow,
  onPreview,
}: {
  projectId: string;
  snapshot: Snapshot | null;
  units: UnitSystem;
  flow: FlowState;
  onPreview: (command: ReturnType<typeof footprintCommand>) => void;
}) {
  const footprint = snapshot ? footprintOf(snapshot) : null;
  const [fields, setFields] = useState<Record<Field, FieldState>>({ width: { text: "", dirty: false }, depth: { text: "", dirty: false } });
  const [parseErrors, setParseErrors] = useState<Partial<Record<Field, string>>>({});

  // Refill untouched fields when the head or the units change; keep what the user typed (UI-001 §5).
  useEffect(() => {
    if (!footprint) return;
    setFields((f) => ({
      width: f.width.dirty ? f.width : { text: lengthInputText(footprint.width_m, units), dirty: false },
      depth: f.depth.dirty ? f.depth : { text: lengthInputText(footprint.depth_m, units), dirty: false },
    }));
  }, [footprint?.width_m, footprint?.depth_m, units]); // eslint-disable-line react-hooks/exhaustive-deps

  const serverDetails: ErrorDetail[] =
    flow.step === "error" && flow.error instanceof ApiError && flow.command.type === "SetFootprintDimensions" ? flow.error.details : [];
  const { byField } = placeDetails(serverDetails, ARG_PATHS);

  function value(field: Field): number | null {
    const state = fields[field];
    if (!footprint) return null;
    if (!state.dirty) return field === "width" ? footprint.width_m : footprint.depth_m;
    const parsed = parseLength(state.text, units);
    return parsed.ok ? parsed.meters : null;
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!snapshot || !footprint) return;
    const errors: Partial<Record<Field, string>> = {};
    for (const field of ["width", "depth"] as const) {
      if (!fields[field].dirty) continue;
      const parsed = parseLength(fields[field].text, units);
      if (!parsed.ok) errors[field] = parsed.error;
    }
    setParseErrors(errors);
    const width = value("width");
    const depth = value("depth");
    if (Object.keys(errors).length > 0 || width === null || depth === null) return;
    onPreview(footprintCommand(projectId, snapshot.revision_id, width, depth));
  }

  const busy = flow.step === "previewing" || flow.step === "committing";
  return (
    <form className="edit-panel" onSubmit={submit} aria-labelledby="edit-heading">
      <h2 id="edit-heading">Footprint</h2>
      {(["width", "depth"] as const).map((field) => {
        const id = `footprint-${field}`;
        const problems = [parseErrors[field], ...(byField[field] ?? []).map(describeDetail)].filter(Boolean);
        return (
          <div className="field" key={field}>
            <label htmlFor={id}>{field === "width" ? "Width (east–west)" : "Depth (north–south)"}</label>
            <input
              id={id}
              value={fields[field].text}
              disabled={!footprint}
              aria-invalid={problems.length > 0}
              aria-describedby={problems.length > 0 ? `${id}-error` : undefined}
              onChange={(e) => setFields((f) => ({ ...f, [field]: { text: e.target.value, dirty: true } }))}
            />
            {problems.length > 0 && (
              <p className="field-error" id={`${id}-error`} role="alert">
                {problems.join("; ")}
              </p>
            )}
          </div>
        );
      })}
      <p className="hint">Examples: 40', 36' 6 1/2", 438.5", 12.192 m.</p>
      <button type="submit" disabled={!footprint || busy}>
        Preview
      </button>
    </form>
  );
}
