/** Story heights (`SetStoryHeights`; UI-002 §6.1). Level 1's elevation follows Level 0's height (D033, D034). */

import { useCallback, useState, type FormEvent } from "react";

import { formatLength, lengthInputText, parseLength } from "../../units/length";
import { placeDetails } from "../commands";
import { envelope, levels } from "./model";
import { detailsFor, isBusy, TextField, type EditorProps } from "./shared";
import { useStoredFields, type Parsed } from "./useStoredFields";

const KEYS = ["h0", "h1"] as const;
const PATHS = { h0: "args.story_heights_m[0]", h1: "args.story_heights_m[1]" };

export function StoriesEditor({ projectId, snapshot, units, flow }: EditorProps) {
  const levelList = snapshot ? levels(snapshot) : [];
  const [l0, l1] = levelList;
  const format = useCallback((_: string, v: number) => lengthInputText(v, units), [units]);
  const stored = l0 && l1 ? { h0: l0.story_height_m, h1: l1.story_height_m } : null;
  const { fields, setText, reset, resolve } = useStoredFields(KEYS, stored, format);
  const [parseErrors, setParseErrors] = useState<Partial<Record<(typeof KEYS)[number], string>>>({});
  const { byField } = placeDetails(detailsFor(flow.state, ["SetStoryHeights"]), PATHS);

  const parse = (text: string): Parsed => {
    const r = parseLength(text, units);
    return r.ok ? { ok: true, value: r.meters } : r;
  };

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!snapshot || !stored) return;
    const h0 = resolve("h0", parse);
    const h1 = resolve("h1", parse);
    setParseErrors({ h0: h0.ok ? undefined : h0.error, h1: h1.ok ? undefined : h1.error });
    if (!h0.ok || !h1.ok) return;
    void flow.preview(envelope(projectId, snapshot.revision_id, "SetStoryHeights", { story_heights_m: [h0.value, h1.value] }));
  }

  return (
    <form className="editor" onSubmit={submit} aria-label="Stories editor">
      <TextField id="story-0" label="Level 0 story height" value={fields.h0.text} disabled={!stored} problems={[parseErrors.h0, ...(byField.h0 ?? [])]} onChange={(t) => setText("h0", t)} />
      <TextField id="story-1" label="Level 1 story height" value={fields.h1.text} disabled={!stored} problems={[parseErrors.h1, ...(byField.h1 ?? [])]} onChange={(t) => setText("h1", t)} />
      {l1 && (
        <p className="hint" data-testid="level-1-elevation">
          Level 1 elevation: {formatLength(l1.elevation_m, units)}. Level 1 sits on top of Level 0's story height. Supported story heights: 8' to 14'.
        </p>
      )}
      <div className="actions">
        <button type="submit" disabled={!stored || isBusy(flow.state)}>
          Preview
        </button>
        <button type="button" onClick={() => (reset(), setParseErrors({}))}>
          Reset
        </button>
      </div>
    </form>
  );
}
