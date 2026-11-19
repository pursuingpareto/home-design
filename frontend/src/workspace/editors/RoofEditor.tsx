/** Roof pitch and overhang (`SetGableRoofParameters`, routine: applied directly; UI-002 §5, §6.2). */

import { useCallback, useState, type FormEvent } from "react";

import { formatLength, formatPitch, lengthInputText, parseLength } from "../../units/length";
import { parsePitch, pitchInputText } from "../../units/pitch";
import { placeDetails } from "../commands";
import { envelope, one } from "./model";
import { detailsFor, isBusy, TextField, type EditorProps } from "./shared";
import { useStoredFields, type Parsed } from "./useStoredFields";

const KEYS = ["pitch", "overhang"] as const;
const PATHS = { pitch: "args.pitch_rad", overhang: "args.eave_overhang_m" };

export function RoofEditor({ projectId, snapshot, units, flow, onApplied }: EditorProps) {
  const roof = snapshot ? one(snapshot, "GableRoof") : null;
  const format = useCallback((key: string, v: number) => (key === "pitch" ? pitchInputText(v) : lengthInputText(v, units)), [units]);
  const stored = roof ? { pitch: roof.pitch_rad, overhang: roof.eave_overhang_m } : null;
  const { fields, setText, reset, resolve } = useStoredFields(KEYS, stored, format);
  const [parseErrors, setParseErrors] = useState<Partial<Record<(typeof KEYS)[number], string>>>({});
  const { byField } = placeDetails(detailsFor(flow.state, ["SetGableRoofParameters"]), PATHS);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!snapshot || !roof) return;
    const pitch = resolve("pitch", (text): Parsed => {
      const r = parsePitch(text);
      return r.ok ? { ok: true, value: r.radians } : r;
    });
    const overhang = resolve("overhang", (text): Parsed => {
      const r = parseLength(text, units);
      return r.ok ? { ok: true, value: r.meters } : r;
    });
    setParseErrors({ pitch: pitch.ok ? undefined : pitch.error, overhang: overhang.ok ? undefined : overhang.error });
    if (!pitch.ok || !overhang.ok) return;
    const base = snapshot.revision_id;
    const result = await flow.apply(envelope(projectId, base, "SetGableRoofParameters", { pitch_rad: pitch.value, eave_overhang_m: overhang.value }));
    if (result) {
      const summary = `Roof pitch ${formatPitch(roof.pitch_rad)} → ${formatPitch(pitch.value)}; overhang ${formatLength(roof.eave_overhang_m, units)} → ${formatLength(overhang.value, units)}.`;
      onApplied(result, summary, base);
    }
  }

  return (
    <form className="editor" onSubmit={submit} aria-label="Roof editor">
      <TextField
        id="roof-pitch"
        label="Pitch"
        value={fields.pitch.text}
        disabled={!roof}
        hint={roof ? `Current: ${formatPitch(roof.pitch_rad)}. Enter rise per 12 (10/12) or degrees (39.81°). Supported: 3/12 to 12/12.` : undefined}
        problems={[parseErrors.pitch, ...(byField.pitch ?? [])]}
        onChange={(t) => setText("pitch", t)}
      />
      <TextField
        id="roof-overhang"
        label="Eave overhang"
        value={fields.overhang.text}
        disabled={!roof}
        hint="North and south eaves. Supported: 0' to 3'."
        problems={[parseErrors.overhang, ...(byField.overhang ?? [])]}
        onChange={(t) => setText("overhang", t)}
      />
      <p className="hint">Roof changes are routine: they are applied without a preview, and can be undone.</p>
      <div className="actions">
        <button type="submit" disabled={!roof || isBusy(flow.state)}>
          Apply
        </button>
        <button type="button" onClick={() => (reset(), setParseErrors({}))}>
          Reset
        </button>
      </div>
    </form>
  );
}
