/** Footprint width and depth (`SetFootprintDimensions`; UI-001 §5). Moved into the UI-002 tabs. */

import { useCallback, useState, type FormEvent } from "react";

import { lengthInputText, parseLength } from "../../units/length";
import { footprintCommand, placeDetails } from "../commands";
import { one } from "./model";
import { detailsFor, isBusy, TextField, type EditorProps } from "./shared";
import { useStoredFields, type Parsed } from "./useStoredFields";

const KEYS = ["width", "depth"] as const;
const PATHS = { width: "args.width_m", depth: "args.depth_m" };

export function FootprintEditor({ projectId, snapshot, units, flow }: EditorProps) {
  const footprint = snapshot ? one(snapshot, "Footprint") : null;
  const format = useCallback((_: string, v: number) => lengthInputText(v, units), [units]);
  const stored = footprint ? { width: footprint.width_m, depth: footprint.depth_m } : null;
  const { fields, setText, reset, resolve } = useStoredFields(KEYS, stored, format);
  const [parseErrors, setParseErrors] = useState<Partial<Record<(typeof KEYS)[number], string>>>({});
  const { byField } = placeDetails(detailsFor(flow.state, ["SetFootprintDimensions"]), PATHS);

  const parse = (text: string): Parsed => {
    const r = parseLength(text, units);
    return r.ok ? { ok: true, value: r.meters } : r;
  };

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!snapshot) return;
    const width = resolve("width", parse);
    const depth = resolve("depth", parse);
    setParseErrors({ width: width.ok ? undefined : width.error, depth: depth.ok ? undefined : depth.error });
    if (!width.ok || !depth.ok) return;
    void flow.preview(footprintCommand(projectId, snapshot.revision_id, width.value, depth.value));
  }

  return (
    <form className="editor" onSubmit={submit} aria-label="Footprint editor">
      <TextField id="footprint-width" label="Width (east–west)" value={fields.width.text} disabled={!footprint} problems={[parseErrors.width, ...(byField.width ?? [])]} onChange={(t) => setText("width", t)} />
      <TextField id="footprint-depth" label="Depth (north–south)" value={fields.depth.text} disabled={!footprint} problems={[parseErrors.depth, ...(byField.depth ?? [])]} onChange={(t) => setText("depth", t)} />
      <p className="hint">Examples: 40', 36' 6 1/2", 438.5", 12.192 m.</p>
      <div className="actions">
        <button type="submit" disabled={!footprint || isBusy(flow.state)}>
          Preview
        </button>
        <button type="button" onClick={() => (reset(), setParseErrors({}))}>
          Reset
        </button>
      </div>
    </form>
  );
}
