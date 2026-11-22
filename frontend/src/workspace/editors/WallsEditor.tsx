/**
 * Walls (UI-004 §8; D087): the wall assembly for the whole house (`SetWallAssembly`, consequential, so
 * previewed, D068), then the openings: a list grouped by wall and a form for the current opening or a new
 * one (`AddOpening`, `SetOpening`, `RemoveOpening`, routine, so applied directly with Undo, D069).
 *
 * The tab follows the selection (D087): picking an opening makes it current, and picking a wall makes it
 * the wall for a new opening. The server validates every command, including the opening fit (D028).
 */

import { useCallback, useRef, useState, type FormEvent } from "react";

import type { Command, ErrorDetail, Snapshot } from "../../api/types";
import { familyLabel, LAYER_FUNCTION_LABEL, OPENING_KIND_LABEL, type OpeningKind } from "../../display/labels";
import { formatLength, lengthInputText, parseLength, type UnitSystem } from "../../units/length";
import { placeDetails } from "../commands";
import type { FlowState } from "../useCommandFlow";
import { DetailLine, namedText } from "../DetailLine";
import { pathLabel, snapshotLabels, type SnapshotLabels } from "../wallLabels";
import { addOpeningArgs, centeredOffset, entitiesOf, envelope, offsetOrigin, one, openingsByWall, setOpeningArgs, wallLength, type OpeningValues } from "./model";
import { detailsFor, FieldProblems, isBusy, TextField, type EditorProps } from "./shared";
import { useStoredFields, type Parsed } from "./useStoredFields";

type Entity = Snapshot["entities"][number];
type Definition = Extract<Entity, { kind: "AssemblyDefinition" }>;
type Opening = Extract<Entity, { kind: "Opening" }>;

/** What the tab shows: an existing opening, or a new one in `wall`; `pendingAdd` adopts an added opening. */
export interface WallsFocus {
  opening: string | null;
  wall: string | null;
  pendingAdd?: { wall: string; before: ReadonlySet<string> } | null;
}

const KEYS = ["width", "height", "sill", "offset"] as const;
type Key = (typeof KEYS)[number];
const PATHS: Record<Key, string> = { width: "args.width_m", height: "args.height_m", sill: "args.sill_height_m", offset: "args.offset_m" };
const OPENING_COMMANDS: Command["type"][] = ["AddOpening", "SetOpening", "RemoveOpening"];

/** Details of the last failed opening command, when it was for this opening (or for a new one). */
function openingFailure(state: FlowState, openingId: string | null): ErrorDetail[] {
  const failure = state.step === "error" ? state : state.step === "idle" ? state.failed : undefined;
  const command = failure?.command;
  if (!command || !OPENING_COMMANDS.includes(command.type)) return [];
  const target = command.type === "AddOpening" ? null : (command.args as { opening_id: string }).opening_id;
  return target === openingId ? detailsFor(state, OPENING_COMMANDS) : [];
}

function BuildUp({ definition, snapshot, units }: { definition: Definition; snapshot: Snapshot; units: UnitSystem }) {
  const names = new Map(entitiesOf(snapshot, "Material").map((m) => [m.id, m.name]));
  const sections = new Map(entitiesOf(snapshot, "Section").map((s) => [s.id, s.nominal_label]));
  const framing = definition.layers.find((l) => l.framing)?.framing ?? null;
  // A display sum of the record's layer thicknesses (UI-004 §8.1; noted in §20).
  const total = definition.layers.reduce((t, l) => t + l.thickness_m, 0);
  return (
    <div className="buildup" data-testid="wall-buildup" data-family={definition.family}>
      <table>
        <caption>
          {familyLabel(definition.family)} build-up, exterior to interior. Total thickness {formatLength(total, units)}.
        </caption>
        <thead>
          <tr>
            <th scope="col">Layer</th>
            <th scope="col">Function</th>
            <th scope="col">Thickness</th>
          </tr>
        </thead>
        <tbody>
          {definition.layers.map((l) => (
            <tr key={l.name} data-layer={l.name}>
              <td title={l.name}>{names.get(l.material_id) ?? l.name}</td>
              <td>{LAYER_FUNCTION_LABEL[l.function]}</td>
              <td>{formatLength(l.thickness_m, units)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {framing && (
        <ul className="hint" data-testid="wall-framing-parameters">
          <li>Framing: {names.get(framing.framing_material_id) ?? framing.framing_material_id}</li>
          {framing.type === "STUD" ? (
            <>
              <li>
                {sections.get(framing.stud_section_id)} studs at {formatLength(framing.stud_spacing_m, units)} on center
              </li>
              <li>
                {framing.girt_count} {framing.girt_count === 1 ? "girt" : "girts"}
                {framing.girt_section_id ? ` (${sections.get(framing.girt_section_id) ?? ""})` : ""}
              </li>
              <li>{sections.get(framing.header_section_id)} headers, with king studs at every opening</li>
              <li>Jack studs at openings wider than {formatLength(framing.jack_threshold_width_m, units)}</li>
            </>
          ) : (
            <>
              <li>{sections.get(framing.buck_section_id)} bucks at every opening</li>
              {framing.girt_count > 0 && <li>{framing.girt_count} girts</li>}
            </>
          )}
        </ul>
      )}
    </div>
  );
}

function AssemblySelector({ projectId, snapshot, units, flow, onOpenPrices, labels }: EditorProps & { snapshot: Snapshot; onOpenPrices: (() => void) | null; labels: SnapshotLabels }) {
  const definitions = entitiesOf(snapshot, "AssemblyDefinition");
  const stored = one(snapshot, "WallSystem")?.default_assembly_definition_id ?? "";
  const [choice, setChoice] = useState<string | null>(null);
  const chosen = choice ?? stored;
  const definition = definitions.find((d) => d.id === chosen);
  const details = detailsFor(flow.state, ["SetWallAssembly"]);
  return (
    <section aria-labelledby="wall-assembly-heading">
      <h3 id="wall-assembly-heading">Wall assembly</h3>
      <div className="field">
        <label htmlFor="wall-assembly">Assembly for every wall</label>
        <select id="wall-assembly" value={chosen} aria-invalid={details.length > 0} onChange={(e) => setChoice(e.target.value)}>
          {definitions.map((d) => (
            <option key={d.id} value={d.id}>
              {familyLabel(d.family)}
            </option>
          ))}
        </select>
        <button type="button" disabled={isBusy(flow.state) || chosen === stored} onClick={() => void flow.preview(envelope(projectId, snapshot.revision_id, "SetWallAssembly", { assembly_definition_id: chosen }))}>
          Preview
        </button>
        {details.length > 0 && (
          <ul className="field-error" role="alert" data-testid="wall-assembly-error">
            {details.map((d, i) => (
              <li key={i}>
                <DetailLine detail={d} labels={labels} />
              </li>
            ))}
          </ul>
        )}
      </div>
      {definition && <BuildUp definition={definition} snapshot={snapshot} units={units} />}
      <p className="hint">Every wall uses this assembly. Switching regenerates all wall framing; timber members and connections do not change.</p>
      <p className="hint" data-testid="wall-pricing-note">
        Wall layers are priced per square foot or meter (<code>assembly.&lt;label&gt;.&lt;layer&gt;</code>) and wall framing per foot or meter (
        <code>wallframing.&lt;kind&gt;.&lt;section&gt;</code>). After switching, the new assembly's lines are unpriced until you price them, and the old assembly's rows become
        unused.{" "}
        {onOpenPrices && (
          <button type="button" className="link" onClick={onOpenPrices}>
            Set unit prices
          </button>
        )}
      </p>
    </section>
  );
}

function OpeningForm({
  projectId,
  snapshot,
  units,
  flow,
  onApplied,
  opening,
  defaultWall,
  labels,
  onFocus,
}: EditorProps & { snapshot: Snapshot; opening: Opening | null; defaultWall: string | null; labels: SnapshotLabels; onFocus: (focus: WallsFocus) => void }) {
  const groups = openingsByWall(snapshot);
  const [wallId, setWallId] = useState(opening?.wall_id ?? defaultWall ?? groups[0]?.wall.id ?? "");
  const [kind, setKind] = useState<OpeningKind>(opening?.opening_kind ?? "WINDOW");
  const wall = groups.find((g) => g.wall.id === wallId)?.wall ?? null;
  const door = kind === "DOOR";
  const format = useCallback((_key: string, v: number) => lengthInputText(v, units), [units]);
  const stored = opening ? { width: opening.width_m, height: opening.height_m, sill: opening.sill_height_m, offset: opening.offset_m } : null;
  const { fields, setText, reset, resolve } = useStoredFields(KEYS, stored, format);
  const [parseErrors, setParseErrors] = useState<Partial<Record<Key, string>>>({});
  // "Center in wall" sends the computed value exactly while its text is untouched (UI-004 §8.2).
  const centered = useRef<{ text: string; value: number } | null>(null);
  const details = openingFailure(flow.state, opening?.id ?? null);
  const { byField, other } = placeDetails(details, PATHS);
  const busy = isBusy(flow.state);
  const studInfill = entitiesOf(snapshot, "AssemblyDefinition").find((d) => d.family === "STUD_INFILL");
  const threshold = studInfill?.layers.find((l) => l.framing?.type === "STUD")?.framing;
  const thresholdText = threshold?.type === "STUD" ? formatLength(threshold.jack_threshold_width_m, units) : "the threshold";
  const label = opening ? (labels.opening(opening.id) ?? "the opening") : null;
  const named = (key: Key) => (byField[key] ?? []).map((d) => namedText(d, labels, opening?.id ?? null));

  const length = (text: string): Parsed => {
    const r = parseLength(text, units);
    return r.ok ? { ok: true, value: r.meters } : r;
  };

  function values(): OpeningValues | null {
    const width = resolve("width", length);
    const height = resolve("height", length);
    const sill: Parsed = door && !opening ? { ok: true, value: 0 } : resolve("sill", length);
    const offset: Parsed = centered.current && fields.offset.text === centered.current.text ? { ok: true, value: centered.current.value } : resolve("offset", length);
    const error = (p: Parsed) => (p.ok ? undefined : p.error);
    setParseErrors({ width: error(width), height: error(height), sill: error(sill), offset: error(offset) });
    if (!width.ok || !height.ok || !sill.ok || !offset.ok) return null;
    return { width_m: width.value, height_m: height.value, sill_height_m: sill.value, offset_m: offset.value };
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const v = values();
    if (!v) return;
    const base = snapshot.revision_id;
    if (opening) {
      const result = await flow.apply(envelope(projectId, base, "SetOpening", setOpeningArgs(opening.id, v)));
      if (result) onApplied(result, `Changed ${label}.`, base);
    } else if (wall) {
      const before = new Set(entitiesOf(snapshot, "Opening").map((o) => o.id));
      const result = await flow.apply(envelope(projectId, base, "AddOpening", addOpeningArgs(wall.id, kind, v)));
      if (result) {
        onApplied(result, `Added a ${OPENING_KIND_LABEL[kind].toLowerCase()} to the ${(labels.wall(wall.id) ?? "wall").replace(/^./, (c) => c.toLowerCase())}.`, base);
        onFocus({ opening: null, wall: wall.id, pendingAdd: { wall: wall.id, before } });
      }
    }
  }

  async function remove() {
    if (!opening) return;
    const base = snapshot.revision_id;
    const result = await flow.apply(envelope(projectId, base, "RemoveOpening", { opening_id: opening.id }));
    if (result) {
      onApplied(result, `Removed ${label}.`, base);
      onFocus({ opening: null, wall: opening.wall_id });
    }
  }

  function center() {
    if (!wall) return;
    const width = resolve("width", length);
    if (!width.ok) {
      setParseErrors((e) => ({ ...e, width: width.error }));
      return;
    }
    const value = centeredOffset(wallLength(wall), width.value);
    const text = lengthInputText(value, units);
    centered.current = { text, value };
    setText("offset", text);
  }

  const origin = wall ? offsetOrigin(wall.generation_key) : "west";
  return (
    <form onSubmit={submit} aria-label={opening ? "Change the opening" : "Add an opening"} data-testid="opening-form" data-opening-id={opening?.id ?? "new"}>
      <h4>{opening ? label : "New opening"}</h4>
      <div className="field">
        <label htmlFor="opening-wall">Wall</label>
        {opening ? (
          <span id="opening-wall">{labels.wall(opening.wall_id)}</span>
        ) : (
          <select id="opening-wall" value={wallId} onChange={(e) => setWallId(e.target.value)}>
            {groups.map(({ wall: w }) => (
              <option key={w.id} value={w.id}>
                {labels.wall(w.id) ?? w.generation_key}
              </option>
            ))}
          </select>
        )}
      </div>
      <div className="field">
        <label htmlFor="opening-kind">Kind</label>
        {opening ? (
          <span id="opening-kind">{OPENING_KIND_LABEL[opening.opening_kind]}</span>
        ) : (
          <select id="opening-kind" value={kind} onChange={(e) => setKind(e.target.value as OpeningKind)}>
            {(Object.keys(OPENING_KIND_LABEL) as OpeningKind[]).map((k) => (
              <option key={k} value={k}>
                {OPENING_KIND_LABEL[k]}
              </option>
            ))}
          </select>
        )}
      </div>
      <TextField id="opening-width" label="Width" value={fields.width.text} hint="Rough opening" problems={[parseErrors.width, ...named("width")]} onChange={(t) => setText("width", t)} />
      <TextField id="opening-height" label="Height" value={fields.height.text} hint="Rough opening" problems={[parseErrors.height, ...named("height")]} onChange={(t) => setText("height", t)} />
      <TextField
        id="opening-sill"
        label="Sill height"
        value={door ? lengthInputText(0, units) : fields.sill.text}
        disabled={door}
        hint={door ? "A door's sill is at the wall's lower datum." : "Above the wall's lower datum."}
        problems={[parseErrors.sill, ...named("sill")]}
        onChange={(t) => setText("sill", t)}
      />
      <TextField
        id="opening-offset"
        label="Offset"
        value={fields.offset.text}
        hint={`From the ${origin} post axis to the rough opening's start.`}
        problems={[parseErrors.offset, ...named("offset")]}
        onChange={(t) => setText("offset", t)}
      />
      <button type="button" onClick={center} disabled={!wall}>
        Center in wall
      </button>
      <p className="hint">
        Sizes are rough openings. The framing around it (bucks; or king studs, jack studs above {thresholdText}, and a header) must fit inside the wall, clear of the knee
        braces, and apart from the wall's other openings. The server checks this.
      </p>
      <FieldProblems id="opening-error" problems={other.map((d) => `${pathLabel(d.path, labels) ?? d.path}: ${namedText(d, labels, opening?.id ?? null)}`)} />
      <div className="actions">
        <button type="submit" disabled={busy || !wall}>
          {opening ? "Apply" : "Add opening"}
        </button>
        {opening && (
          <button type="button" disabled={busy} onClick={() => void remove()}>
            Remove
          </button>
        )}
        <button
          type="button"
          onClick={() => {
            reset();
            centered.current = null;
            setParseErrors({});
          }}
        >
          Reset
        </button>
      </div>
    </form>
  );
}

export function WallsEditor(props: EditorProps & { onOpenPrices: (() => void) | null; focus: WallsFocus; onFocus: (focus: WallsFocus) => void }) {
  const { snapshot, units, focus, onFocus } = props;
  if (!snapshot) return <p>Loading walls…</p>;
  const labels = snapshotLabels(snapshot, units);
  const groups = openingsByWall(snapshot);
  const current = focus.opening ? (entitiesOf(snapshot, "Opening").find((o) => o.id === focus.opening) ?? null) : null;
  const count = groups.reduce((n, g) => n + g.openings.length, 0);
  return (
    <div className="editor walls-editor" aria-label="Walls editor" role="group">
      <AssemblySelector {...props} snapshot={snapshot} labels={labels} />
      <section aria-labelledby="openings-heading">
        <h3 id="openings-heading">Openings ({count})</h3>
        <div className="opening-list" data-testid="opening-list">
          {groups.map(({ wall, openings }) => (
            <div key={wall.id} data-testid="opening-group" data-wall-id={wall.id}>
              <h4>{labels.wall(wall.id)}</h4>
              <ul>
                {openings.length === 0 && <li className="hint">No openings</li>}
                {openings.map((o) => (
                  <li key={o.id}>
                    <button type="button" className="link" data-opening-id={o.id} aria-pressed={o.id === current?.id} onClick={() => onFocus({ opening: o.id, wall: null })}>
                      {labels.opening(o.id)}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <button type="button" onClick={() => onFocus({ opening: null, wall: current?.wall_id ?? focus.wall })} disabled={!current}>
          New opening
        </button>
        <OpeningForm key={current?.id ?? `new-${focus.wall ?? ""}`} {...props} snapshot={snapshot} opening={current} defaultWall={focus.wall} labels={labels} onFocus={onFocus} />
      </section>
    </div>
  );
}
