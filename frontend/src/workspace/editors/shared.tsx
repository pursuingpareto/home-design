/** Shared editor plumbing (UI-002 §4, §7). */

import { ApiError } from "../../api/client";
import type { Command, CommitResponse, ErrorDetail, Snapshot } from "../../api/types";
import type { UnitSystem } from "../../units/length";
import { describeDetail } from "../commands";
import type { FlowState } from "../useCommandFlow";

export interface Flow {
  state: FlowState;
  preview: (command: Command) => Promise<void>;
  apply: (command: Command) => Promise<CommitResponse | null>;
}

export interface EditorProps {
  projectId: string;
  snapshot: Snapshot | null;
  units: UnitSystem;
  flow: Flow;
  /** A routine command was committed; `summary` describes the change for the notice (UI-002 §5). */
  onApplied: (result: CommitResponse, summary: string, baseRevisionId: string) => void;
}

export function isBusy(state: FlowState): boolean {
  return state.step === "previewing" || state.step === "committing" || state.step === "applying";
}

/** Server details of the last failed command, when it was one of `types`; kept after its dialog closes. */
export function detailsFor(state: FlowState, types: readonly Command["type"][]): ErrorDetail[] {
  const failure = state.step === "error" ? state : state.step === "idle" ? state.failed : undefined;
  if (!failure || !(failure.error instanceof ApiError)) return [];
  return types.includes(failure.command.type) ? failure.error.details : [];
}

export function FieldProblems({ id, problems }: { id: string; problems: (string | ErrorDetail | undefined)[] }) {
  const texts = problems.filter((p): p is string | ErrorDetail => p !== undefined).map((p) => (typeof p === "string" ? p : describeDetail(p)));
  if (texts.length === 0) return null;
  return (
    <p className="field-error" id={id} role="alert">
      {texts.join("; ")}
    </p>
  );
}

export function TextField({
  id,
  label,
  value,
  disabled,
  problems,
  onChange,
  hint,
}: {
  id: string;
  label: string;
  value: string;
  disabled?: boolean;
  problems: (string | ErrorDetail | undefined)[];
  onChange: (text: string) => void;
  hint?: string;
}) {
  const invalid = problems.some((p) => p !== undefined);
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input id={id} value={value} disabled={disabled} aria-invalid={invalid} aria-describedby={invalid ? `${id}-error` : undefined} onChange={(e) => onChange(e.target.value)} />
      {hint && <span className="hint">{hint}</span>}
      <FieldProblems id={`${id}-error`} problems={problems} />
    </div>
  );
}
