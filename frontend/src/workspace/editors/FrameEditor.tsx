/**
 * Frame parameters (`SetFrameParameters`; UI-003 §7.1, D057). Consequential, so changes go through the
 * preview. All five arguments are sent: untouched lengths send their stored values exactly, and the
 * switches their state. Ranges and brace fit are the server's to check (D028); the hints state them.
 */

import { useCallback, useState, type FormEvent } from "react";

import { lengthInputText, parseLength } from "../../units/length";
import { placeDetails } from "../commands";
import { envelope, one, parseWholeNumber } from "./model";
import { detailsFor, FieldProblems, isBusy, TextField, type EditorProps } from "./shared";
import { useStoredFields, type Parsed } from "./useStoredFields";

const KEYS = ["joist", "purlins", "leg"] as const;
const PATHS = {
  joist: "args.joist_spacing_m",
  purlins: "args.purlins_per_slope",
  leg: "args.knee_brace_leg_m",
  level1: "args.knee_braces_level_1",
  eave: "args.knee_braces_eave",
};

export function FrameEditor({ projectId, snapshot, units, flow }: EditorProps) {
  const frame = snapshot ? one(snapshot, "FrameSystem") : null;
  const parameters = frame?.parameters ?? null;
  const format = useCallback((key: string, v: number) => (key === "purlins" ? String(v) : lengthInputText(v, units)), [units]);
  const stored = parameters ? { joist: parameters.joist_spacing_m, purlins: parameters.purlins_per_slope, leg: parameters.knee_brace_leg_m } : null;
  const { fields, setText, reset, resolve } = useStoredFields(KEYS, stored, format);
  // A switch the user has not touched follows the stored value.
  const [switches, setSwitches] = useState<{ level1?: boolean; eave?: boolean }>({});
  const [parseErrors, setParseErrors] = useState<Partial<Record<(typeof KEYS)[number], string>>>({});
  const { byField } = placeDetails(detailsFor(flow.state, ["SetFrameParameters"]), PATHS);
  const level1 = switches.level1 ?? parameters?.knee_braces_level_1 ?? false;
  const eave = switches.eave ?? parameters?.knee_braces_eave ?? false;

  const length = (text: string): Parsed => {
    const r = parseLength(text, units);
    return r.ok ? { ok: true, value: r.meters } : r;
  };

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!snapshot || !parameters) return;
    const joist = resolve("joist", length);
    const purlins = resolve("purlins", parseWholeNumber);
    const leg = resolve("leg", length);
    setParseErrors({ joist: joist.ok ? undefined : joist.error, purlins: purlins.ok ? undefined : purlins.error, leg: leg.ok ? undefined : leg.error });
    if (!joist.ok || !purlins.ok || !leg.ok) return;
    void flow.preview(
      envelope(projectId, snapshot.revision_id, "SetFrameParameters", {
        joist_spacing_m: joist.value,
        purlins_per_slope: purlins.value,
        knee_brace_leg_m: leg.value,
        knee_braces_level_1: level1,
        knee_braces_eave: eave,
      }),
    );
  }

  return (
    <form className="editor" onSubmit={submit} aria-label="Frame editor">
      <TextField
        id="frame-joist-spacing"
        label="Joist spacing"
        value={fields.joist.text}
        disabled={!parameters}
        hint={`Measured from each bay's west beam line. Supported: 12" to 48".`}
        problems={[parseErrors.joist, ...(byField.joist ?? [])]}
        onChange={(t) => setText("joist", t)}
      />
      <TextField
        id="frame-purlins"
        label="Purlins per slope"
        value={fields.purlins.text}
        disabled={!parameters}
        hint="Evenly divided between eave and ridge. Supported: 0 to 4."
        problems={[parseErrors.purlins, ...(byField.purlins ?? [])]}
        onChange={(t) => setText("purlins", t)}
      />
      <TextField
        id="frame-brace-leg"
        label="Knee brace leg"
        value={fields.leg.text}
        disabled={!parameters}
        hint={`Each leg, at 45°. Supported: 1'-6" to 4'-0", and twice the leg must fit the shortest bay while braces are on.`}
        problems={[parseErrors.leg, ...(byField.leg ?? [])]}
        onChange={(t) => setText("leg", t)}
      />
      <div className="field">
        <label>
          <input type="checkbox" checked={level1} disabled={!parameters} onChange={(e) => setSwitches((s) => ({ ...s, level1: e.target.checked }))} /> Knee braces on Level 1
        </label>
        <FieldProblems id="frame-braces-level-1-error" problems={byField.level1 ?? []} />
      </div>
      <div className="field">
        <label>
          <input type="checkbox" checked={eave} disabled={!parameters} onChange={(e) => setSwitches((s) => ({ ...s, eave: e.target.checked }))} /> Knee braces at the eave
        </label>
        <FieldProblems id="frame-braces-eave-error" problems={byField.eave ?? []} />
      </div>
      <p className="hint">Ranges are what the generator supports, not structural limits. Members regenerate; members on surviving positions keep their IDs.</p>
      <div className="actions">
        <button type="submit" disabled={!parameters || isBusy(flow.state)}>
          Preview
        </button>
        <button type="button" onClick={() => (reset(), setSwitches({}), setParseErrors({}))}>
          Reset
        </button>
      </div>
    </form>
  );
}
