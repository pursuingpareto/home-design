/**
 * Timber grid (`SetTimberGrid`; UI-002 §6.3). Lines are edited as positions from the origin; the
 * model stores fractions of the footprint (D042). Untouched lines keep their stored fraction exactly,
 * end lines are fixed, and "divide into N equal bays" reuses interior line IDs in order.
 */

import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";

import type { ErrorDetail } from "../../api/types";
import { formatLength, lengthInputText, parseLength, type UnitSystem } from "../../units/length";
import { describeDetail } from "../commands";
import { axisArgs, envelope, equalBays, gridDetails, insertMidpoint, one, rowsFromLines, type Axis, type GridRow } from "./model";
import { detailsFor, FieldProblems, isBusy, type EditorProps } from "./shared";

const AXIS_LABEL: Record<Axis, string> = { x: "X lines (along the width, east–west)", y: "Y lines (along the depth, north–south)" };

function positionOf(row: GridRow, dimension: number, units: UnitSystem): number | null {
  if (row.end || !row.dirty) return row.fraction * dimension;
  const parsed = parseLength(row.text, units);
  return parsed.ok ? parsed.meters : null;
}

/** A to-scale strip of the editor's own values. Labeled as not being the plan (UI-002 §6.3). */
function Strip({ axis, rows, dimension, units }: { axis: Axis; rows: GridRow[]; dimension: number; units: UnitSystem }) {
  const positions = rows.map((r) => ({ row: r, at: positionOf(r, dimension, units) }));
  const label = `Grid lines (not the plan), ${axis.toUpperCase()}: ${positions
    .map(({ row, at }) => `${row.id ?? "new"} at ${at === null ? "?" : formatLength(at, units)}`)
    .join(", ")}.`;
  return (
    <svg className="grid-strip" role="img" aria-label={label} viewBox={`${-dimension * 0.03} -1 ${dimension * 1.06} 2.2`} preserveAspectRatio="none">
      <title>{label}</title>
      <line x1={0} y1={0} x2={dimension} y2={0} className="axis" />
      {positions.map(({ row, at }) =>
        at === null ? null : <line key={row.key} x1={at} y1={-0.8} x2={at} y2={0.8} className={row.id ? "line" : "line new"} />,
      )}
    </svg>
  );
}

function AxisTable({
  axis,
  rows,
  dimension,
  units,
  errors,
  rowDetails,
  axisDetails,
  onRows,
}: {
  axis: Axis;
  rows: GridRow[];
  dimension: number;
  units: UnitSystem;
  errors: Record<string, string>;
  rowDetails: Record<string, ErrorDetail[]>;
  axisDetails: ErrorDetail[];
  onRows: (rows: GridRow[]) => void;
}) {
  const [bays, setBays] = useState(String(Math.max(1, rows.length - 1)));
  const positions = rows.map((r) => positionOf(r, dimension, units));
  const setRow = (key: string, patch: Partial<GridRow>) => onRows(rows.map((r) => (r.key === key ? { ...r, ...patch } : r)));
  return (
    <fieldset className="grid-axis" data-testid={`grid-${axis}`}>
      <legend>{AXIS_LABEL[axis]}</legend>
      <Strip axis={axis} rows={rows} dimension={dimension} units={units} />
      <table>
        <thead>
          <tr>
            <th scope="col">Line</th>
            <th scope="col">Position from origin</th>
            <th scope="col">Bay to next</th>
            <th scope="col">
              <span className="visually-hidden">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => {
            const next = positions[index + 1];
            const here = positions[index];
            const bay = next !== undefined && next !== null && here !== null && here !== undefined ? formatLength(next - here, units) : "";
            const id = `grid-${axis}-${index}`;
            const problems = [errors[row.key], ...(rowDetails[row.key] ?? []).map(describeDetail)].filter(Boolean);
            return (
              <tr key={row.key} data-line-id={row.id ?? "new"}>
                <td>
                  <label htmlFor={id}>{row.id ?? "new line"}</label>
                </td>
                <td>
                  {row.end ? (
                    <span id={id}>{formatLength(row.fraction * dimension, units)} (fixed)</span>
                  ) : (
                    <input
                      id={id}
                      value={row.dirty ? row.text : lengthInputText(row.fraction * dimension, units)}
                      aria-invalid={problems.length > 0}
                      onChange={(e) => setRow(row.key, { text: e.target.value, dirty: true })}
                    />
                  )}
                  {problems.length > 0 && (
                    <p className="field-error" role="alert">
                      {problems.join("; ")}
                    </p>
                  )}
                </td>
                <td>{bay}</td>
                <td className="row-actions">
                  {!row.end && (
                    <button type="button" aria-label={`Remove line ${row.id ?? "new"}`} onClick={() => onRows(rows.filter((r) => r.key !== row.key))}>
                      Remove
                    </button>
                  )}
                  {index < rows.length - 1 && (
                    <button
                      type="button"
                      aria-label={`Add a line after ${row.id ?? "new line"} on ${axis.toUpperCase()}`}
                      onClick={() => onRows(insertMidpoint(rows, index, (r) => (positionOf(r, dimension, units) ?? NaN) / dimension))}
                    >
                      Add after
                    </button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="equal-bays">
        <label htmlFor={`bays-${axis}`}>Divide {axis.toUpperCase()} into</label>
        <input id={`bays-${axis}`} type="number" min={1} max={6} value={bays} onChange={(e) => setBays(e.target.value)} />
        <span>equal bays</span>
        <button type="button" onClick={() => Number.isInteger(Number(bays)) && Number(bays) >= 1 && onRows(equalBays(rows, Number(bays)))}>
          Divide
        </button>
      </div>
      <FieldProblems id={`grid-${axis}-axis-error`} problems={axisDetails} />
    </fieldset>
  );
}

export function GridEditor({ projectId, snapshot, units, flow }: EditorProps) {
  const grid = snapshot ? one(snapshot, "TimberGrid") : null;
  const footprint = snapshot ? one(snapshot, "Footprint") : null;
  const [rows, setRows] = useState<Record<Axis, GridRow[]> | null>(null);
  const [touched, setTouched] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const submittedOrder = useRef<Record<Axis, string[]>>({ x: [], y: [] });
  const signature = grid ? JSON.stringify([grid.x_lines, grid.y_lines]) : "";

  const fromStored = useMemo(
    () => (grid ? { x: rowsFromLines(grid.x_lines), y: rowsFromLines(grid.y_lines) } : null),
    [signature], // eslint-disable-line react-hooks/exhaustive-deps
  );
  // Follow the stored grid until the user edits; keep edits across reloads (UI-002 §4).
  useEffect(() => {
    if (!touched && fromStored) setRows(fromStored);
  }, [fromStored, touched]);

  const details = detailsFor(flow.state, ["SetTimberGrid"]);
  const placed = gridDetails(details, submittedOrder.current);

  function update(axis: Axis, next: GridRow[]) {
    setTouched(true);
    setRows((r) => (r ? { ...r, [axis]: next } : r));
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!snapshot || !rows || !footprint) return;
    const parse = (text: string) => parseLength(text, units);
    const x = axisArgs(rows.x, footprint.width_m, parse);
    const y = axisArgs(rows.y, footprint.depth_m, parse);
    const nextErrors = { ...(x.ok ? {} : x.errors), ...(y.ok ? {} : y.errors) };
    setErrors(nextErrors);
    if (!x.ok || !y.ok) return;
    // Keep the table in the submitted (ascending) order, so error indexes match the rows.
    const sortBy = (axis: Axis, order: string[]) => order.map((key) => rows[axis].find((r) => r.key === key)!);
    setRows({ x: sortBy("x", x.order), y: sortBy("y", y.order) });
    submittedOrder.current = { x: x.order, y: y.order };
    void flow.preview(envelope(projectId, snapshot.revision_id, "SetTimberGrid", { x_lines: x.args, y_lines: y.args }));
  }

  if (!rows || !footprint) return <p>Loading grid…</p>;
  return (
    <form className="editor" onSubmit={submit} aria-label="Grid editor">
      <p className="hint">
        Lines are stored as fractions of the footprint, so widening the footprint stretches every bay. Bays must stay between 4' and 24'; 1 to 6 bays per axis.
      </p>
      <AxisTable axis="x" rows={rows.x} dimension={footprint.width_m} units={units} errors={errors} rowDetails={placed.rows} axisDetails={placed.axes.x} onRows={(r) => update("x", r)} />
      <AxisTable axis="y" rows={rows.y} dimension={footprint.depth_m} units={units} errors={errors} rowDetails={placed.rows} axisDetails={placed.axes.y} onRows={(r) => update("y", r)} />
      <div className="actions">
        <button type="submit" disabled={isBusy(flow.state)}>
          Preview
        </button>
        <button
          type="button"
          onClick={() => {
            setTouched(false);
            setErrors({});
            setRows(fromStored);
          }}
        >
          Reset
        </button>
      </div>
    </form>
  );
}
