import { describe, expect, it } from "vitest";

import { parseLength } from "../src/units/length";
import { parsePitch, pitchInputText } from "../src/units/pitch";
import { axisArgs, equalBays, gridDetails, insertMidpoint, otherTabs, rowsFromLines, type GridRow } from "../src/workspace/editors/model";
import { fixture } from "./fixtures";

const grid = fixture.snapshot.entities.find((e) => e.kind === "TimberGrid")!;
if (grid.kind !== "TimberGrid") throw new Error("fixture grid");
const footprint = fixture.snapshot.entities.find((e) => e.kind === "Footprint")!;
if (footprint.kind !== "Footprint") throw new Error("fixture footprint");
const parse = (text: string) => parseLength(text, "imperial");
const ok = <T,>(r: { ok: true } & T | { ok: false }) => {
  if (!r.ok) throw new Error("expected ok");
  return r as T;
};

describe("pitch input (UI-002 §6.2)", () => {
  it("accepts rise per 12 and degrees", () => {
    const rad = (t: string) => {
      const r = parsePitch(t);
      if (!r.ok) throw new Error(r.error);
      return r.radians;
    };
    expect(rad("9/12")).toBe(Math.atan(0.75));
    expect(rad("9:12")).toBe(Math.atan(0.75));
    expect(rad("9")).toBe(Math.atan(0.75));
    expect(rad("9.5 / 12")).toBe(Math.atan(9.5 / 12));
    expect(rad("45°")).toBeCloseTo(Math.PI / 4, 15);
    expect(rad("36.87 deg")).toBeCloseTo((36.87 * Math.PI) / 180, 15);
    for (const bad of ["", "9/10", "steep", "0", "-3/12", "90°", "0 deg"]) expect(parsePitch(bad).ok, bad).toBe(false);
    expect(pitchInputText(Math.atan(0.75))).toBe("9/12");
  });
});

describe("grid arguments (UI-002 §6.3)", () => {
  const stored = rowsFromLines(grid.x_lines);

  it("sends untouched lines exactly, with their IDs", () => {
    const { args } = ok<{ args: unknown }>(axisArgs(stored, footprint.width_m, parse));
    expect(args).toEqual(grid.x_lines.map((l) => ({ id: l.id, fraction: l.fraction })));
    expect(12 * 0.3048 / footprint.width_m).not.toBe(grid.x_lines[1]!.fraction); // why untouched lines must not be recomputed
  });

  it("converts a moved line from its position and keeps it ascending", () => {
    const moved = stored.map((r, i) => (i === 1 ? { ...r, text: "30'", dirty: true } : r));
    const { args, order } = ok<{ args: { id?: string; fraction: number }[]; order: string[] }>(axisArgs(moved, footprint.width_m, parse));
    expect(args.map((a) => a.id)).toEqual(["x0", "x2", "x1", "x3"]);
    expect(args[2]!.fraction).toBe(9.144 / 10.9728);
    expect(order[2]).toBe(moved[1]!.key);
  });

  it("never moves the end lines and reports unparsable positions by row", () => {
    const edited = stored.map((r, i) => (i === 0 ? { ...r, text: "5'", dirty: true } : i === 2 ? { ...r, text: "far", dirty: true } : r));
    const result = axisArgs(edited, footprint.width_m, parse);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(Object.keys(result.errors)).toEqual([edited[2]!.key]);
    const fixed = axisArgs(edited.map((r, i) => (i === 2 ? stored[2]! : r)), footprint.width_m, parse);
    expect(ok<{ args: { fraction: number }[] }>(fixed).args[0]).toEqual({ id: "x0", fraction: 0 });
  });

  it("sends new lines without an ID", () => {
    const withNew = insertMidpoint(stored, 0, (r) => r.fraction);
    const { args } = ok<{ args: { id?: string; fraction: number }[] }>(axisArgs(withNew, footprint.width_m, parse));
    expect(args[1]).toEqual({ fraction: grid.x_lines[1]!.fraction / 2 });
    expect("id" in args[1]!).toBe(false);
  });

  it("divides into equal bays, reusing interior IDs in order", () => {
    const four = equalBays(stored, 4);
    expect(four.map((r) => [r.id, r.fraction])).toEqual([["x0", 0], ["x1", 0.25], ["x2", 0.5], [undefined, 0.75], ["x3", 1]]);
    const two = equalBays(stored, 2);
    expect(two.map((r) => [r.id, r.fraction])).toEqual([["x0", 0], ["x1", 0.5], ["x3", 1]]);
    expect(equalBays(stored, 1).map((r) => r.id)).toEqual(["x0", "x3"]);
    expect(four[0]).toBe(stored[0]); // the ends are the same rows
  });

  it("places server details on rows by submitted index, or on the axis", () => {
    const order = { x: stored.map((r: GridRow) => r.key), y: [] as string[] };
    const placed = gridDetails(
      [
        { path: "entities[g].x_lines[2].fraction", code: "NOT_STRICTLY_ASCENDING", related_paths: ["args.x_lines[2].fraction"] },
        { path: "entities[g].x_lines", code: "OUT_OF_SUPPORTED_RANGE", related_paths: ["args.x_lines", "entities[f].width_m"] },
        { path: "project_id", code: "DANGLING_REFERENCE" },
      ],
      order,
    );
    expect(placed.rows[stored[2]!.key]?.map((d) => d.code)).toEqual(["NOT_STRICTLY_ASCENDING"]);
    expect(placed.axes.x.map((d) => d.code)).toEqual(["OUT_OF_SUPPORTED_RANGE"]);
    expect(placed.other.map((d) => d.code)).toEqual(["DANGLING_REFERENCE"]);
  });
});

describe("cross-tab pointers (UI-002 §7)", () => {
  it("names other tabs from entity kinds in paths", () => {
    const detail = { path: `entities[${grid.id}].x_lines`, code: "OUT_OF_SUPPORTED_RANGE", related_paths: ["args.width_m", `entities[${footprint.id}].width_m`] };
    expect(otherTabs([detail], fixture.snapshot, "footprint")).toEqual(["grid"]);
    expect(otherTabs([detail], fixture.snapshot, "grid")).toEqual(["footprint"]);
    expect(otherTabs([{ path: "args.pitch_rad", code: "X" }], fixture.snapshot, "roof")).toEqual([]);
    expect(otherTabs([detail], null, "footprint")).toEqual([]);
  });
});
