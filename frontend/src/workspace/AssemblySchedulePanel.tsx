/**
 * The assembly schedule (UI-004 §10; artifacts.md §7A): the definition in use with its declared values
 * and their provenance, the thermal figures with their method and notes, the walls, openings, framing
 * takeoff, layer quantities, pieces, and assumptions, all as served. The client sums and derives
 * nothing; thermal figures follow the units switch (D089), and an unknown figure reads "Not computed".
 */

import { useEffect, useRef } from "react";

import type { AssemblyScheduleEnvelope } from "../api/types";
import { familyLabel, LAYER_FUNCTION_LABEL, openingKindLabel, pieceKindLabel } from "../display/labels";
import { formatArea, formatLength, formatVolume, type UnitSystem } from "../units/length";
import { conductivity, formatThermal, permeance, rValue, uaValue, uValue, type Thermal } from "../units/thermal";
import type { Highlight } from "../views/highlight";
import type { OnSelect } from "./panels";
import { scheduleLabels } from "./wallLabels";

type Payload = NonNullable<AssemblyScheduleEnvelope["payload"]>;
type Definition = Payload["definitions"][number];
type Declared = Definition["layers"][number]["thermal_conductivity_w_m_k"];
type Missing = Payload["thermal"]["all_walls"]["missing_inputs"][number];

const shortId = (id: string) => id.slice(0, 8);
const dash = "—";

/** A declared value with its unit, source, date, and note; "Not declared" when null (D071). */
function DeclaredCell({ value, show }: { value: Declared; show: (v: number) => Thermal }) {
  if (!value) return <span className="not-declared">Not declared</span>;
  return (
    <span>
      {formatThermal(show(value.value))}
      <span className="declared">
        {" "}
        ({value.source}, {value.date}
        {value.note ? `; ${value.note}` : ""})
      </span>
    </span>
  );
}

const FIELD_TEXT: Record<string, string> = {
  thermal_conductivity_w_m_k: "conductivity",
  thermal_resistance_m2_k_w: "resistance",
  "framing.framing_thermal_conductivity_w_m_k": "conductivity",
};

/** "Lime plaster (conductivity or resistance)", "Spruce-pine-fir framing (conductivity)" (UI-004 §10 item 3). */
export function missingText(missing: Missing, definitions: readonly Definition[]): string {
  const layer = definitions.find((d) => d.label === missing.assembly_label)?.layers.find((l) => l.name === missing.layer);
  const framing = missing.fields.some((f) => f.startsWith("framing."));
  const name = framing ? `${layer?.framing?.framing_material_name ?? missing.layer} framing` : (layer?.material_name ?? missing.layer);
  return `${name} (${missing.fields.map((f) => FIELD_TEXT[f] ?? f).join(" or ")})`;
}

/** Every figure's missing inputs, once each, in order of first appearance. */
export function allMissing(payload: Payload): Missing[] {
  const seen = new Map<string, Missing>();
  const figures = [...payload.thermal.definitions.flatMap((d) => [d.center_of_cavity, d.framing_path, d.parallel_path]), payload.thermal.all_walls];
  for (const figure of figures) for (const m of figure.missing_inputs) seen.set(JSON.stringify([m.assembly_label, m.layer, m.fields]), m);
  return [...seen.values()];
}

const u = (v: number | null, units: UnitSystem) => formatThermal(v === null ? null : uValue(v, units));
const r = (v: number | null, units: UnitSystem) => formatThermal(v === null ? null : rValue(v, units));
const ua = (v: number | null, units: UnitSystem) => formatThermal(v === null ? null : uaValue(v, units));
const orDash = (text: string) => (text === "Not computed" ? dash : text);

function DefinitionPart({ d, units }: { d: Definition; units: UnitSystem }) {
  const framingLayer = d.layers.find((l) => l.framing);
  const framing = framingLayer?.framing ?? null;
  return (
    <div data-testid="assembly-definition" data-family={d.family}>
      <h3>
        {familyLabel(d.family)} <code>{d.label}</code>
      </h3>
      <p>
        Total thickness {formatLength(d.total_thickness_m, units)}. {d.installation_note}
      </p>
      <table data-testid="assembly-layers">
        <caption>Layers, exterior to interior</caption>
        <thead>
          <tr>
            <th scope="col">Layer</th>
            <th scope="col">Function</th>
            <th scope="col">Thickness</th>
            <th scope="col">Thermal conductivity or resistance</th>
            <th scope="col">Vapor permeance</th>
          </tr>
        </thead>
        <tbody>
          {d.layers.map((l) => (
            <tr key={l.name} data-layer={l.name}>
              <td title={l.name}>{l.material_name}</td>
              <td>{LAYER_FUNCTION_LABEL[l.function]}</td>
              <td>{formatLength(l.thickness_m, units)}</td>
              <td>
                {l.thermal_resistance_m2_k_w && !l.thermal_conductivity_w_m_k ? (
                  <DeclaredCell value={l.thermal_resistance_m2_k_w} show={(v) => rValue(v, units)} />
                ) : (
                  <DeclaredCell value={l.thermal_conductivity_w_m_k} show={(v) => conductivity(v, units)} />
                )}
                {l.framing && (
                  <div data-testid="framing-material">
                    Framing, {l.framing.framing_material_name}: <DeclaredCell value={l.framing.framing_thermal_conductivity_w_m_k} show={(v) => conductivity(v, units)} />
                  </div>
                )}
              </td>
              <td>
                <DeclaredCell value={l.vapor_permeance_kg_pa_s_m2} show={permeance} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {framing && (
        <p data-testid="assembly-framing-parameters">
          {framing.type === "STUD"
            ? `Framing: ${framing.stud_section} studs at ${formatLength(framing.stud_spacing_m, units)} on center; ${framing.girt_count} ${framing.girt_count === 1 ? "girt" : "girts"}${framing.girt_section ? ` (${framing.girt_section})` : ""}; ${framing.header_section} headers; jack studs at openings wider than ${formatLength(framing.jack_threshold_width_m, units)}.`
            : `Framing: ${framing.buck_section} bucks at every opening${framing.girt_count > 0 ? `; ${framing.girt_count} girts` : ""}.`}
        </p>
      )}
    </div>
  );
}

export function AssemblySchedulePanel({
  assemblies,
  units,
  highlight,
  onSelect,
}: {
  assemblies: AssemblyScheduleEnvelope | null;
  units: UnitSystem;
  highlight: Highlight;
  onSelect: OnSelect;
}) {
  const payload = assemblies?.status === "CURRENT" ? assemblies.payload : null;
  const list = useRef<HTMLDivElement>(null);
  const firstPiece = payload?.wall_framing.find((p) => highlight.pieces.has(p.piece_id) || highlight.relatedPieces.has(p.piece_id))?.piece_id ?? null;
  // Scroll the piece list (not the page) to the first highlighted row, as the connection list does.
  useEffect(() => {
    const container = list.current;
    const row = firstPiece ? container?.querySelector<HTMLElement>(`tr[data-piece-id="${firstPiece}"]`) : null;
    if (!container || !row) return;
    const header = container.querySelector("thead")?.getBoundingClientRect().height ?? 0;
    container.scrollTop += row.getBoundingClientRect().top - container.getBoundingClientRect().top - header;
  }, [firstPiece]);
  const climate = assemblies?.warnings.find((w) => w.code === "CLIMATE_DETAILS_UNVERIFIED");
  const labels = payload ? scheduleLabels(payload, units) : null;
  const family = (label: string) => {
    const d = payload?.definitions.find((x) => x.label === label);
    return d ? familyLabel(d.family) : label;
  };
  const rowClass = (selected: boolean, related = false) => (selected ? "selected" : related ? "related" : undefined);

  return (
    <section className="schedule assembly-schedule" aria-labelledby="assembly-heading" data-testid="assembly-schedule">
      <h2 id="assembly-heading">Assembly schedule</h2>
      {!payload ? (
        <p>{assemblies ? `Not available (${assemblies.status}).` : "Updating…"}</p>
      ) : (
        <>
          {/* 1. The envelope's warning, never hard-coded (as PreliminaryBanner reads its own), and the details. */}
          <div className="notice" role="note" data-testid="climate-warning">
            <p>{climate?.message}</p>
            {payload.definitions.map((d) => (
              <ul key={d.assembly_definition_id} data-testid="climate-details">
                {d.unverified_climate_details.map((text) => (
                  <li key={text}>{text}</li>
                ))}
              </ul>
            ))}
          </div>
          <p className="source">
            Revision <code>{shortId(assemblies!.source_revision_id)}</code>. Lengths in {units === "imperial" ? "feet-inches" : "meters"}, areas in{" "}
            {units === "imperial" ? "square feet" : "square meters"} (stored in {payload.units.length}, {payload.units.area}, {payload.units.volume},{" "}
            {payload.units.thermal_transmittance}, {payload.units.thermal_resistance}, {payload.units.heat_flow}).
          </p>

          {/* 2. The definition in use. */}
          {payload.definitions.map((d) => (
            <DefinitionPart key={d.assembly_definition_id} d={d} units={units} />
          ))}

          {/* 3. Thermal figures, with their method. */}
          <div data-testid="thermal">
            <h3>Thermal figures</h3>
            <p>
              Method <code>{payload.thermal.method.id}</code>
            </p>
            <ul data-testid="thermal-notes">
              {payload.thermal.method.notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
            <table data-testid="thermal-figures">
              <thead>
                <tr>
                  <th scope="col">Figure</th>
                  <th scope="col">U-value</th>
                  <th scope="col">R-value</th>
                  <th scope="col">UA</th>
                </tr>
              </thead>
              <tbody>
                {payload.thermal.definitions.flatMap((t) => [
                  <tr key={`${t.assembly_label}/cavity`} data-figure="center_of_cavity">
                    <th scope="row">{family(t.assembly_label)}: center of cavity</th>
                    <td>{u(t.center_of_cavity.u_value_w_m2_k, units)}</td>
                    <td>{r(t.center_of_cavity.r_value_m2_k_w, units)}</td>
                    <td>{dash}</td>
                  </tr>,
                  <tr key={`${t.assembly_label}/framing`} data-figure="framing_path">
                    <th scope="row">{family(t.assembly_label)}: framing path</th>
                    <td>{u(t.framing_path.u_value_w_m2_k, units)}</td>
                    <td>{r(t.framing_path.r_value_m2_k_w, units)}</td>
                    <td>{dash}</td>
                  </tr>,
                  <tr key={`${t.assembly_label}/parallel`} data-figure="parallel_path">
                    <th scope="row">{family(t.assembly_label)}: parallel path, area-weighted</th>
                    <td>{u(t.parallel_path.u_value_w_m2_k, units)}</td>
                    <td>{r(t.parallel_path.r_value_m2_k_w, units)}</td>
                    <td>{ua(t.parallel_path.ua_w_k, units)}</td>
                  </tr>,
                ])}
                <tr data-figure="all_walls">
                  <th scope="row">All walls, area-weighted</th>
                  <td>{u(payload.thermal.all_walls.u_value_w_m2_k, units)}</td>
                  <td>{r(payload.thermal.all_walls.r_value_m2_k_w, units)}</td>
                  <td>{ua(payload.thermal.all_walls.ua_w_k, units)}</td>
                </tr>
              </tbody>
            </table>
            {allMissing(payload).length > 0 && (
              <div data-testid="missing-inputs">
                Missing declared values:
                <ul>
                  {allMissing(payload).map((m) => (
                    <li key={JSON.stringify([m.assembly_label, m.layer, m.fields])}>{missingText(m, payload.definitions)}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* 4. Walls. */}
          <div className="scroll">
            <table data-testid="assembly-walls">
              <caption>Walls ({payload.walls.length})</caption>
              <thead>
                <tr>
                  <th scope="col">Wall</th>
                  <th scope="col">Length</th>
                  <th scope="col">Height</th>
                  <th scope="col">Gross area</th>
                  <th scope="col">Opening area</th>
                  <th scope="col">Net area</th>
                  <th scope="col">Framing fraction</th>
                  <th scope="col">U</th>
                  <th scope="col">R</th>
                  <th scope="col">UA</th>
                </tr>
              </thead>
              <tbody>
                {payload.walls.map((w) => (
                  <tr
                    key={w.wall_id}
                    data-wall-id={w.wall_id}
                    title={w.generation_key}
                    aria-selected={highlight.walls.has(w.wall_id)}
                    className={rowClass(highlight.walls.has(w.wall_id))}
                    onClick={() => onSelect({ kind: "wall", id: w.wall_id })}
                  >
                    <td>{labels!.walls.get(w.wall_id)}</td>
                    <td>{formatLength(w.length_m, units)}</td>
                    <td>{formatLength(w.height_m, units)}</td>
                    <td>{formatArea(w.gross_area_m2, units)}</td>
                    <td>{formatArea(w.opening_area_m2, units)}</td>
                    <td>{formatArea(w.net_area_m2, units)}</td>
                    <td>{(w.framing_fraction * 100).toFixed(2)}%</td>
                    <td>{orDash(u(w.u_value_w_m2_k, units))}</td>
                    <td>{orDash(r(w.r_value_m2_k_w, units))}</td>
                    <td>{orDash(ua(w.ua_w_k, units))}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr data-testid="assembly-totals">
                  <th scope="row">Totals: {payload.totals.wall_count} walls</th>
                  <td />
                  <td />
                  <td>{formatArea(payload.totals.gross_area_m2, units)}</td>
                  <td>{formatArea(payload.totals.opening_area_m2, units)}</td>
                  <td>{formatArea(payload.totals.net_area_m2, units)}</td>
                  <td>{dash}</td>
                  <td>{orDash(u(payload.thermal.all_walls.u_value_w_m2_k, units))}</td>
                  <td>{orDash(r(payload.thermal.all_walls.r_value_m2_k_w, units))}</td>
                  <td>{orDash(ua(payload.thermal.all_walls.ua_w_k, units))}</td>
                </tr>
              </tfoot>
            </table>
          </div>

          {/* 5. Openings. */}
          <table data-testid="assembly-openings">
            <caption>Openings ({payload.openings.length})</caption>
            <thead>
              <tr>
                <th scope="col">Opening</th>
                <th scope="col">Kind</th>
                <th scope="col">Rough opening</th>
                <th scope="col">Area</th>
                <th scope="col">With jacks</th>
              </tr>
            </thead>
            <tbody>
              {payload.openings.map((o) => (
                <tr
                  key={o.opening_id}
                  data-opening-id={o.opening_id}
                  aria-selected={highlight.openings.has(o.opening_id)}
                  className={rowClass(highlight.openings.has(o.opening_id))}
                  onClick={() => onSelect({ kind: "opening", id: o.opening_id })}
                >
                  <td>{labels!.openings.get(o.opening_id)}</td>
                  <td>{openingKindLabel(o.opening_kind)}</td>
                  <td>
                    {formatLength(o.width_m, units)} × {formatLength(o.height_m, units)}
                  </td>
                  <td>{formatArea(o.area_m2, units)}</td>
                  <td>{o.has_jacks ? "Yes" : "No"}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* 6. Framing takeoff. */}
          <table data-testid="assembly-framing-aggregates">
            <caption>Wall framing takeoff</caption>
            <thead>
              <tr>
                <th scope="col">Kind</th>
                <th scope="col">Section</th>
                <th scope="col">Count</th>
                <th scope="col">Total length</th>
              </tr>
            </thead>
            <tbody>
              {payload.framing_aggregates.map((a) => (
                <tr key={`${a.piece_kind}/${a.nominal_section}`} data-piece-kind={a.piece_kind}>
                  <td>{pieceKindLabel(a.piece_kind)}</td>
                  <td>{a.nominal_section}</td>
                  <td>{a.count}</td>
                  <td>{formatLength(a.total_length_m, units)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* 7. Layer quantities. */}
          <table data-testid="assembly-layer-aggregates">
            <caption>Layer quantities</caption>
            <thead>
              <tr>
                <th scope="col">Assembly</th>
                <th scope="col">Layer</th>
                <th scope="col">Function</th>
                <th scope="col">Thickness</th>
                <th scope="col">Area</th>
                <th scope="col">Volume</th>
              </tr>
            </thead>
            <tbody>
              {payload.layer_aggregates.map((a) => (
                <tr
                  key={`${a.assembly_label}/${a.layer}`}
                  data-layer={a.layer}
                  title={a.function === "FRAMING" ? "The framing layer's fill, net of the wall framing's face area (D082)." : undefined}
                >
                  <td>{a.assembly_label}</td>
                  <td title={a.layer}>{a.material_name}</td>
                  <td>{LAYER_FUNCTION_LABEL[a.function]}</td>
                  <td>{formatLength(a.thickness_m, units)}</td>
                  <td>{formatArea(a.area_m2, units)}</td>
                  <td>{formatVolume(a.volume_m3, units)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* 8. Pieces. */}
          <div className="scroll" ref={list}>
            <table data-testid="assembly-pieces">
              <caption>Wall framing pieces ({payload.wall_framing.length})</caption>
              <thead>
                <tr>
                  <th scope="col">Generation key</th>
                  <th scope="col">Kind</th>
                  <th scope="col">Section</th>
                  <th scope="col">Species</th>
                  <th scope="col">Length</th>
                  <th scope="col">Opening</th>
                </tr>
              </thead>
              <tbody>
                {payload.wall_framing.map((p) => {
                  const selected = highlight.pieces.has(p.piece_id);
                  return (
                    <tr
                      key={p.piece_id}
                      data-piece-id={p.piece_id}
                      aria-selected={selected}
                      className={rowClass(selected, highlight.relatedPieces.has(p.piece_id))}
                      onClick={() => onSelect({ kind: "pieces", ids: [p.piece_id] })}
                    >
                      <td>{p.generation_key}</td>
                      <td>{pieceKindLabel(p.piece_kind)}</td>
                      <td>{p.nominal_section}</td>
                      <td>{p.species ?? dash}</td>
                      <td>{formatLength(p.length_m, units)}</td>
                      <td>{p.opening_id ? (labels!.openings.get(p.opening_id) ?? dash) : dash}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* 9. Assumptions, verbatim and in order. */}
          <ul className="assumptions" data-testid="assembly-assumptions">
            {payload.assumptions.map((a) => (
              <li key={a.code}>{a.message}</li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
