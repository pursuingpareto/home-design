/**
 * UI-004 §16, Vitest tests 1–8 and 11, against the captured Reference House 001 v3 fixture: walls,
 * openings, and wall framing in the plan and 3D, the two switches, selection, the Walls tab, paths and
 * messages, the dialog, and the assembly schedule panel. One `describe` per test number (§13).
 */

import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import * as THREE from "three";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../src/api/client";
import type { AssemblyScheduleEnvelope, Command, ErrorDetail, Snapshot } from "../src/api/types";
import { AppContext } from "../src/app/context";
import { readShowWallFraming, readShowWallLayers, writeShowWallFraming, writeShowWallLayers } from "../src/app/preferences";
import {
  FAMILY_LABEL,
  FRAMING_GROUP_LABEL,
  LAYER_FUNCTION_LABEL,
  OPENING_KIND_LABEL,
  SIDE_LABEL,
  framingGroupOf,
  openingLabel,
  sideOfKey,
  wallLabel,
} from "../src/display/labels";
import { FRAMING_COLOR, LAYER_COLOR, MIXED_COLOR, OPENING_COLOR, ROLE_COLOR, SELECTION_COLOR, TYPE_COLOR, WALL_BAND_COLOR } from "../src/display/palette";
import { formatArea, formatLength, formatVolume } from "../src/units/length";
import { conductivity, formatThermal, rValue, uaValue, uValue } from "../src/units/thermal";
import { NO_HIGHLIGHT } from "../src/views/highlight";
import { buildMeshScene, COLORS, highlight, pick, setWallsVisible } from "../src/views/meshScene";
import { Plan2dView } from "../src/views/Plan2dView";
import { framingMatrix, groupFraming, NO_DETAILS, tessellate } from "../src/views/walls";
import { AssemblySchedulePanel } from "../src/workspace/AssemblySchedulePanel";
import { DETAIL_TEXT } from "../src/workspace/commands";
import { Editors } from "../src/workspace/editors/Editors";
import { entitiesOf, otherTabs, TAB_LABEL, TAB_OF_COMMAND } from "../src/workspace/editors/model";
import { ImpactDialog } from "../src/workspace/ImpactDialog";
import { highlightOf } from "../src/workspace/selection";
import { snapshotLabels, wallDetails } from "../src/workspace/wallLabels";
import { Workspace } from "../src/workspace/Workspace";
import { editorProps } from "./editorProps";
import { fakeApi } from "./fakeApi";
import { assemblies, fixture, mesh, plan, studInfill } from "./fixtures";

afterEach(cleanup);
beforeEach(() => localStorage.clear());

const snapshot = fixture.snapshot;
const planPayload = plan.payload!;
const meshPayload = mesh.payload!;
const assemblyPayload = assemblies.payload!;
const studPlan = studInfill.plan2d.payload!;
const studMesh = studInfill.mesh3d.payload!;
const revision = plan.source_revision_id;
const details = wallDetails(assemblies, revision, "imperial");
const plane = (id: string, payload = planPayload) => payload.planes.find((p) => p.plane_id === id)!;
const walls = entitiesOf(snapshot, "Wall");
const openings = entitiesOf(snapshot, "Opening");
const wallByKey = (key: string) => walls.find((w) => w.generation_key === key)!;
const openingsOf = (key: string) => openings.filter((o) => o.wall_id === wallByKey(key).id);
const SW0 = "wall/axis-x/y0/x0-x1/level-0";
const swWindow = openingsOf(SW0)[0]!;
const door = openings.find((o) => o.opening_kind === "DOOR")!;
const strawId = entitiesOf(snapshot, "AssemblyDefinition").find((d) => d.family === "STRAW_BALE")!.id;
const studId = entitiesOf(snapshot, "AssemblyDefinition").find((d) => d.family === "STUD_INFILL")!.id;

/** Points of an SVG polygon, in plan coordinates (the view draws y downward). */
const pointsOf = (polygon: Element) =>
  polygon
    .getAttribute("points")!
    .split(" ")
    .map((p) => p.split(",").map(Number))
    .map(([x, y]) => [x!, -y!]);
const close = (a: number[][], b: number[][]) => a.every((p, i) => Math.abs(p[0]! - b[i]![0]!) < 1e-9 && Math.abs(p[1]! - b[i]![1]!) < 1e-9);

function renderPlan(props: Partial<Parameters<typeof Plan2dView>[0]> = {}) {
  return render(<Plan2dView plan={planPayload} units="imperial" highlight={NO_HIGHLIGHT} showConnections={true} details={details} onSelect={vi.fn()} {...props} />);
}

const planFigure = (container: HTMLElement) => container.querySelector<HTMLElement>("figure.plan2d")!;

function renderWorkspace(override?: Parameters<typeof fakeApi>[0]) {
  const { api, calls } = fakeApi(override);
  render(
    <AppContext.Provider value={{ api, units: "imperial", setUnits: () => {}, signOut: () => {} }}>
      <Workspace projectId={fixture.project.project_id} revisionId={null} />
    </AppContext.Provider>,
  );
  return calls;
}

function renderEditors(state?: ReturnType<typeof editorProps>["flow"]["state"], selection?: Parameters<typeof Editors>[0]["selection"]) {
  const props = editorProps();
  const flow = state ? { ...props.flow, state } : props.flow;
  const view = render(<Editors {...props} flow={flow as typeof props.flow} versions={{}} onOpenPrices={vi.fn()} selection={selection ?? null} />);
  return { ...props, view };
}

const tab = (name: string) => userEvent.click(screen.getByRole("tab", { name }));
const lastCommand = (spy: { mock: { calls: unknown[][] } }) => spy.mock.calls.at(-1)![0] as Command & { args: Record<string, unknown> };

describe("1. plan walls (§4.1)", () => {
  it("draws 10 bands and 10 opening marks on each level, and none on the eave and roof", async () => {
    const { container } = renderPlan();
    const figure = planFigure(container);
    const count = (selector: string) => container.querySelectorAll(selector).length;
    expect([figure.dataset.wallCount, figure.dataset.openingCount]).toEqual(["10", "10"]);
    expect(count(".wall-band")).toBe(10);
    expect(count('.opening-mark[data-opening-kind="DOOR"]')).toBe(1);
    expect(count('.opening-mark[data-opening-kind="WINDOW"]')).toBe(9);
    await userEvent.click(screen.getByRole("button", { name: "Level 1" }));
    expect(count(".wall-band")).toBe(10);
    expect(count('.opening-mark[data-opening-kind="WINDOW"]')).toBe(10);
    for (const name of ["Eave", "Roof"]) {
      await userEvent.click(screen.getByRole("button", { name }));
      expect([count(".wall-band"), count(".opening-mark"), count(".framing-mark")]).toEqual([0, 0, 0]);
    }
  });

  it("places each band's corners at the served extents, with a gap at each opening's served points", () => {
    const { container } = renderPlan();
    for (const wall of plane("level-0").walls) {
      const n = wall.outward_xy;
      const at = (p: number[], k: number) => [p[0]! + n[0]! * k, p[1]! + n[1]! * k];
      const quad = (a: number[], b: number[]) => [at(a, wall.exterior_m), at(b, wall.exterior_m), at(b, -wall.interior_m), at(a, -wall.interior_m)];
      const stations = [wall.start_xy_m, ...wall.openings.flatMap((o) => [o.start_xy_m, o.end_xy_m]), wall.end_xy_m];
      const polygons = [...container.querySelectorAll(`.wall-band[data-wall-id="${wall.wall_id}"] polygon`)];
      expect(polygons).toHaveLength(wall.openings.length + 1);
      polygons.forEach((polygon, i) => expect(close(pointsOf(polygon), quad(stations[2 * i]!, stations[2 * i + 1]!))).toBe(true));
      for (const opening of wall.openings) {
        const mark = container.querySelector(`.opening-mark[data-opening-id="${opening.opening_id}"] polygon`)!;
        expect(close(pointsOf(mark), quad(opening.start_xy_m, opening.end_xy_m))).toBe(true);
      }
    }
    // Straw bale: 10½" out and 10" in (D083).
    expect(plane("level-0").walls[0]!.exterior_m).toBeCloseTo(0.2667, 12);
    expect(plane("level-0").walls[0]!.interior_m).toBeCloseTo(0.254, 12);
  });

  it("draws the bands before every member, openings and framing after them, and glyphs last; a window has a glazing line and a door none", () => {
    const { container } = renderPlan();
    const drawn = [...container.querySelectorAll("svg > *")];
    const index = (selector: string) => drawn.map((el, i) => (el.matches(selector) ? i : -1)).filter((i) => i >= 0);
    expect(Math.max(...index(".wall-band"))).toBeLessThan(Math.min(...index("[data-member-id]")));
    expect(Math.max(...index("[data-member-id]"))).toBeLessThan(Math.min(...index(".opening-mark")));
    expect(Math.max(...index(".opening-mark"))).toBeLessThan(Math.min(...index(".framing-mark")));
    expect(Math.max(...index(".framing-mark"))).toBeLessThan(Math.min(...index(".connection-glyph")));
    expect(container.querySelector('.opening-mark[data-opening-kind="WINDOW"] .glazing')).not.toBeNull();
    expect(container.querySelector('.opening-mark[data-opening-kind="DOOR"] .glazing')).toBeNull();
  });

  it("titles a wall with its label and key, and an opening with its label and size", () => {
    const { container } = renderPlan();
    const sw = wallByKey(SW0);
    expect(container.querySelector(`.wall-band[data-wall-id="${sw.id}"] title`)!.textContent).toBe(`South wall, Level 0, x0–x1\n${SW0}`);
    expect(container.querySelector(`.opening-mark[data-opening-id="${swWindow.id}"] title`)!.textContent).toBe(`Window 5' 0" × 4' 0", south wall, Level 0, x0–x1`);
  });
});

describe("2. plan framing (§4.2)", () => {
  const marks = (payload: typeof planPayload, id: string) => groupFraming(plane(id, payload).wall_framing);

  it("groups coincident pieces: 30 marks for 39 and 40 pieces (straw bale), 106 and 100 for 126 and 120 (stud infill)", () => {
    expect([plane("level-0").wall_framing.length, marks(planPayload, "level-0").length]).toEqual([39, 30]);
    expect([plane("level-1").wall_framing.length, marks(planPayload, "level-1").length]).toEqual([40, 30]);
    expect([plane("level-0", studPlan).wall_framing.length, marks(studPlan, "level-0").length]).toEqual([126, 106]);
    expect([plane("level-1", studPlan).wall_framing.length, marks(studPlan, "level-1").length]).toEqual([120, 100]);
    expect(Math.max(...marks(studPlan, "level-0").map((m) => m.pieces.length))).toBe(2);
  });

  it("draws each plane's marks, whose piece IDs together are exactly the plane's wall_framing", async () => {
    for (const [payload, counts] of [
      [planPayload, ["30", "30"]],
      [studPlan, ["106", "100"]],
    ] as const) {
      cleanup();
      const { container } = renderPlan({ plan: payload });
      for (const [i, level] of (["Level 0", "Level 1"] as const).entries()) {
        await userEvent.click(screen.getByRole("button", { name: level }));
        const id = i === 0 ? "level-0" : "level-1";
        const drawn = [...container.querySelectorAll(".framing-mark")];
        expect(planFigure(container).dataset.framingMarkCount).toBe(counts[i]);
        expect(drawn).toHaveLength(Number(counts[i]));
        const ids = drawn.flatMap((el) => el.getAttribute("data-piece-ids")!.split(" ")).sort();
        expect(ids).toEqual(plane(id, payload).wall_framing.map((p) => p.piece_id).sort());
        expect(planFigure(container).dataset.framingCount).toBe(String(ids.length));
      }
    }
  });

  it("titles a mark with each piece's kind and section from the schedule, or the kind alone without it", () => {
    const { container } = renderPlan();
    const pair = [...container.querySelectorAll(".framing-mark")].find((el) => el.getAttribute("data-piece-ids")!.includes(" "))!;
    const ids = pair.getAttribute("data-piece-ids")!.split(" ");
    const rows = ids.map((id) => assemblyPayload.wall_framing.find((p) => p.piece_id === id)!);
    expect(pair.querySelector("title")!.textContent).toBe(rows.map((r) => `${r.piece_kind === "BUCK_HEAD" ? "Buck head" : "Buck sill"} 1.5x18 · ${r.generation_key}`).join("\n"));
    cleanup();
    const bare = renderPlan({ details: wallDetails({ ...assemblies, status: "STALE" }, revision, "imperial") });
    const same = bare.container.querySelector(`.framing-mark[data-piece-ids="${ids.join(" ")}"] title`)!;
    expect(same.textContent).toBe(rows.map((r) => (r.piece_kind === "BUCK_HEAD" ? "Buck head" : "Buck sill")).join("\n"));
  });

  it("colors marks by framing group", () => {
    const { container } = renderPlan();
    const jamb = container.querySelector('.framing-mark[data-piece-kind="BUCK_JAMB"] rect')!;
    expect(jamb.getAttribute("fill")).toBe(`#${FRAMING_COLOR.buck.toString(16).padStart(6, "0")}`);
    expect(framingGroupOf("STUD")).toBe("layout");
    expect(framingGroupOf("CRIPPLE")).toBe("opening");
  });
});

describe("3. 3D walls and framing (§5)", () => {
  it("draws 60 layer solids with 20 voids, 79 framing boxes, and 20 pick surfaces (straw bale); 80 and 246 (stud infill)", () => {
    const scene = buildMeshScene(meshPayload);
    expect(scene.walls.solids).toHaveLength(60);
    expect(meshPayload.walls.reduce((n, w) => n + w.voids.length, 0)).toBe(20);
    expect(scene.walls.openings).toHaveLength(20);
    expect(scene.framing.boxes.reduce((n, b) => n + b.mesh.count, 0)).toBe(79);
    scene.dispose();
    const studs = buildMeshScene(studMesh);
    expect(studs.walls.solids).toHaveLength(80);
    expect(studs.framing.boxes.reduce((n, b) => n + b.mesh.count, 0)).toBe(246);
    studs.dispose();
  });

  it("gives each framing box the basis of the served rule within 1e-9", () => {
    for (const payload of [meshPayload, studMesh]) {
      const outward = new Map(payload.walls.map((w) => [w.wall_id, w.outward_xy]));
      for (const piece of payload.wall_framing) {
        const n = outward.get(piece.wall_id)!;
        const { matrix, size } = framingMatrix(piece, n);
        const along = new THREE.Vector3(), inPlane = new THREE.Vector3(), through = new THREE.Vector3();
        matrix.extractBasis(along, inPlane, through);
        const axis = new THREE.Vector3(...(piece.axis_end_m as [number, number, number])).sub(new THREE.Vector3(...(piece.axis_start_m as [number, number, number])));
        expect(along.distanceTo(axis.clone().normalize())).toBeLessThan(1e-9);
        expect(through.distanceTo(new THREE.Vector3(n[0], n[1], 0))).toBeLessThan(1e-9); // through-wall along outward_xy
        expect(Math.abs(inPlane.dot(along))).toBeLessThan(1e-9); // in-plane: perpendicular to the axis…
        expect(Math.abs(inPlane.dot(through))).toBeLessThan(1e-9); // …and in the wall's plane
        expect(size.toArray()).toEqual([axis.length(), piece.section_in_plane_m, piece.section_through_wall_m]);
      }
    }
  });

  it("tessellates a face around its voids without covering them", () => {
    const rects = tessellate(4, 3, [{ u_m: [1, 2], v_m: [1, 2] }]);
    const area = rects.reduce((a, r) => a + (r.u[1] - r.u[0]) * (r.v[1] - r.v[0]), 0);
    expect(area).toBeCloseTo(11, 12);
    expect(rects.some((r) => r.u[0] < 1.5 && 1.5 < r.u[1] && r.v[0] < 1.5 && 1.5 < r.v[1])).toBe(false);
  });

  it("picks an opening through its void, a wall through a layer, and a glyph first", () => {
    const scene = buildMeshScene(meshPayload);
    const wall = meshPayload.walls.find((w) => w.generation_key === SW0)!;
    const hole = wall.voids[0]!;
    const n = new THREE.Vector3(wall.outward_xy[0], wall.outward_xy[1], 0);
    const u = new THREE.Vector3(...(wall.base_end_m as [number, number, number])).sub(new THREE.Vector3(...(wall.base_start_m as [number, number, number]))).normalize();
    const base = new THREE.Vector3(...(wall.base_start_m as [number, number, number]));
    const at = (uu: number, vv: number) => base.clone().addScaledVector(u, uu).add(new THREE.Vector3(0, 0, vv));
    const ray = (target: THREE.Vector3) => new THREE.Raycaster(target.clone().addScaledVector(n, 5), n.clone().negate());
    const middle = at((hole.u_m[0]! + hole.u_m[1]!) / 2, (hole.v_m[0]! + hole.v_m[1]!) / 2);
    expect(pick(scene, ray(middle))).toEqual({ kind: "opening", id: hole.opening_id });
    expect(pick(scene, ray(at(0.5, wall.height_m / 2)))).toEqual({ kind: "wall", id: wall.wall_id });
    const glyph = scene.markers.glyphs[0]!;
    const toGlyph = new THREE.Vector3(...(glyph.position as [number, number, number]));
    const from = toGlyph.clone().add(new THREE.Vector3(-20, -20, 10));
    expect(pick(scene, new THREE.Raycaster(from, toGlyph.clone().sub(from).normalize()))).toEqual({ kind: "connections", ids: glyph.markers.map((m) => m.connection_id) });
    scene.dispose();
  });
});

describe("4. switches (§6)", () => {
  it("default on, and are read and written through preferences.ts", () => {
    expect([readShowWallLayers(), readShowWallFraming()]).toEqual([true, true]);
    writeShowWallLayers(false);
    writeShowWallFraming(false);
    expect([localStorage.getItem("homedesign.wallLayers"), localStorage.getItem("homedesign.wallFraming")]).toEqual(["off", "off"]);
    expect([readShowWallLayers(), readShowWallFraming()]).toEqual([false, false]);
  });

  it("hide bands and opening marks (Wall layers) and framing (Wall framing) in the plan; both off draws what it drew before", () => {
    const { container, rerender } = renderPlan({ showWallLayers: false });
    expect([container.querySelectorAll(".wall-band, .opening-mark").length, container.querySelectorAll(".framing-mark").length]).toEqual([0, 30]);
    rerender(<Plan2dView plan={planPayload} units="imperial" highlight={NO_HIGHLIGHT} showConnections={true} showWallFraming={false} onSelect={vi.fn()} />);
    expect([container.querySelectorAll(".wall-band").length, container.querySelectorAll(".framing-mark").length]).toEqual([10, 0]);
    rerender(<Plan2dView plan={planPayload} units="imperial" highlight={NO_HIGHLIGHT} showConnections={true} showWallLayers={false} showWallFraming={false} onSelect={vi.fn()} />);
    const svg = container.querySelector("svg")!;
    // Before UI-004: the outlines, ridge, members, glyphs, and dimensions, and nothing else.
    const before = [...svg.children].filter((el) => !el.matches("title"));
    expect(before.every((el) => el.matches(".eave, .footprint, .ridge, [data-member-id], .connection-glyph, .dimension"))).toBe(true);
    const figure = planFigure(container);
    expect([figure.dataset.wallCount, figure.dataset.openingCount, figure.dataset.framingCount, figure.dataset.framingMarkCount]).toEqual(["0", "0", "0", "0"]);
    expect(within(screen.getByTestId("plan-legend")).queryByText("Walls")).toBeNull();
    expect(screen.getByTestId("plan-legend").querySelector("[data-framing-group]")).toBeNull();
  });

  it("hide 3D solids, outlines, and boxes, and report the drawn counts", async () => {
    renderWorkspace();
    const mesh3d = await waitFor(() => {
      const figure = document.querySelector<HTMLElement>("figure.mesh3d");
      expect(figure).not.toBeNull();
      return figure!;
    });
    expect([mesh3d.dataset.wallCount, mesh3d.dataset.openingCount, mesh3d.dataset.framingCount, mesh3d.dataset.wallSolidCount, mesh3d.dataset.framingBoxCount]).toEqual(["20", "20", "79", "60", "79"]);
    await userEvent.click(screen.getByRole("switch", { name: "Wall layers" }));
    expect(mesh3d.dataset.wallSolidCount).toBe("0");
    await userEvent.click(screen.getByRole("switch", { name: "Wall framing" }));
    expect(mesh3d.dataset.framingBoxCount).toBe("0");
    expect(within(screen.getByTestId("mesh-legend")).queryByText("Finish")).toBeNull();
    // The scene's own switches: nothing hidden is picked.
    const scene = buildMeshScene(meshPayload);
    const wall = meshPayload.walls.find((w) => w.generation_key === SW0)!;
    const n = new THREE.Vector3(wall.outward_xy[0], wall.outward_xy[1], 0);
    const target = new THREE.Vector3(...(wall.base_start_m as [number, number, number])).add(new THREE.Vector3(0.5, 0, wall.height_m / 2));
    const ray = () => new THREE.Raycaster(target.clone().addScaledVector(n, 5), n.clone().negate());
    expect(pick(scene, ray())?.kind).toBe("wall");
    setWallsVisible(scene, false, false);
    expect(["wall", "opening", "pieces"]).not.toContain(pick(scene, ray())?.kind);
    scene.dispose();
  });

  it("clear a selection they hide", async () => {
    renderWorkspace();
    const row = await screen.findByText(`Window 5' 0" × 4' 0", south wall, Level 0, x0–x1`, { selector: "[data-testid=assembly-openings] td" });
    await userEvent.click(row);
    expect(document.querySelector(`.opening-mark.selected[data-opening-id="${swWindow.id}"]`)).not.toBeNull();
    await userEvent.click(screen.getByRole("switch", { name: "Wall layers" }));
    await userEvent.click(screen.getByRole("switch", { name: "Wall layers" }));
    expect(document.querySelector(".opening-mark.selected")).toBeNull();
    expect(document.querySelector('[data-testid=assembly-openings] tr[aria-selected="true"]')).toBeNull();
  });
});

describe("5. selection (§7)", () => {
  it("an opening row highlights its plan mark, its outline, and its framing as related (4 pieces for a window, 3 for the door)", async () => {
    renderWorkspace();
    const row = await screen.findByText(`Window 5' 0" × 4' 0", south wall, Level 0, x0–x1`, { selector: "[data-testid=assembly-openings] td" });
    await userEvent.click(row);
    expect(document.querySelector(`.opening-mark.selected[data-opening-id="${swWindow.id}"]`)).not.toBeNull();
    const related = [...document.querySelectorAll(".framing-mark.related")].flatMap((el) => el.getAttribute("data-piece-ids")!.split(" "));
    expect(related.sort()).toEqual(assemblyPayload.wall_framing.filter((p) => p.opening_id === swWindow.id).map((p) => p.piece_id).sort());
    expect(related).toHaveLength(4);
    expect(document.querySelectorAll("[data-testid=assembly-pieces] tr.related")).toHaveLength(4);

    const h = highlightOf({ kind: "opening", id: door.id }, null, revision, assemblies);
    expect(h.relatedPieces.size).toBe(3);
    const scene = buildMeshScene(meshPayload);
    highlight(scene, highlightOf({ kind: "opening", id: swWindow.id }, null, revision, assemblies));
    const outline = scene.walls.openings.find((o) => o.openingId === swWindow.id)!;
    expect((outline.outline.material as THREE.LineBasicMaterial).color.getHex()).toBe(COLORS.selected);
    const color = new THREE.Color();
    const relatedBoxes = scene.framing.boxes.flatMap((b) => b.pieces.filter((_, i) => (b.mesh.getColorAt(i, color), color.getHex() === COLORS.related)));
    expect(relatedBoxes).toHaveLength(4);
    scene.dispose();
  });

  it("a wall highlights its band and its layer solids, and its row", async () => {
    const sw = wallByKey(SW0);
    const h = highlightOf({ kind: "wall", id: sw.id }, null, revision, assemblies);
    const { container } = renderPlan({ highlight: h });
    expect(container.querySelector(`.wall-band.selected[data-wall-id="${sw.id}"]`)).not.toBeNull();
    const scene = buildMeshScene(meshPayload);
    highlight(scene, h);
    const selected = scene.walls.solids.filter((s) => (s.mesh.material as THREE.MeshStandardMaterial).color.getHex() === COLORS.selected);
    expect(selected.map((s) => s.wallId)).toEqual([sw.id, sw.id, sw.id]);
    scene.dispose();
    render(<AssemblySchedulePanel assemblies={assemblies} units="imperial" highlight={h} onSelect={vi.fn()} />);
    expect(document.querySelector(`[data-testid=assembly-walls] tr[data-wall-id="${sw.id}"]`)).toHaveAttribute("aria-selected", "true");
  });

  it("without a CURRENT assembly schedule for the views' revision, only the picked object is highlighted", () => {
    for (const env of [null, { ...assemblies, status: "STALE" as const }, { ...assemblies, source_revision_id: "another" }]) {
      const h = highlightOf({ kind: "opening", id: swWindow.id }, null, revision, env as AssemblyScheduleEnvelope | null);
      expect([...h.openings]).toEqual([swWindow.id]);
      expect(h.relatedPieces.size).toBe(0);
    }
  });

  it("plan picks report walls, openings, and pieces", async () => {
    const onSelect = vi.fn();
    const { container } = renderPlan({ onSelect });
    await userEvent.click(container.querySelector(`.opening-mark[data-opening-id="${swWindow.id}"] polygon`)!);
    expect(onSelect).toHaveBeenLastCalledWith({ kind: "opening", id: swWindow.id });
    await userEvent.click(container.querySelector(`.wall-band[data-wall-id="${swWindow.wall_id}"] polygon`)!);
    expect(onSelect).toHaveBeenLastCalledWith({ kind: "wall", id: swWindow.wall_id });
    const mark = container.querySelector(".framing-mark")!;
    await userEvent.click(mark.firstElementChild!.nextElementSibling!);
    expect(onSelect).toHaveBeenLastCalledWith({ kind: "pieces", ids: mark.getAttribute("data-piece-ids")!.split(" ") });
  });
});

describe("6. the Walls tab (§8)", () => {
  it("lists eight tabs in order", () => {
    renderEditors();
    expect(screen.getAllByRole("tab").map((t) => t.textContent)).toEqual(["Footprint", "Stories", "Roof", "Grid", "Frame", "Sections", "Connections", "Walls"]);
  });

  it("selects the assembly, shows the chosen build-up, and previews SetWallAssembly", async () => {
    const { flow } = renderEditors();
    await tab("Walls");
    const select = screen.getByLabelText("Assembly for every wall");
    expect(select).toHaveDisplayValue("Straw bale");
    expect(screen.getByRole("button", { name: "Preview" })).toBeDisabled();
    await userEvent.selectOptions(select, studId);
    const buildup = screen.getByTestId("wall-buildup");
    expect(buildup.querySelectorAll("tbody tr")).toHaveLength(4);
    expect(within(buildup).getByText("Dense-pack cellulose")).toBeInTheDocument();
    const framing = screen.getByTestId("wall-framing-parameters").textContent!;
    expect(framing).toContain(`2x6 studs at 2' 0" on center`);
    expect(framing).toContain("1 girt (2x6)");
    expect(framing).toContain("2x8 headers");
    expect(framing).toContain(`Jack studs at openings wider than 4' 0"`);
    expect(buildup).toHaveTextContent(`Total thickness 0' 7 1/4"`);
    await userEvent.click(screen.getByRole("button", { name: "Preview" }));
    expect(flow.preview).toHaveBeenCalledTimes(1);
    expect(lastCommand(flow.preview)).toMatchObject({ type: "SetWallAssembly", args: { assembly_definition_id: studId } });
    expect(flow.apply).not.toHaveBeenCalled();
    expect(screen.getByTestId("wall-pricing-note")).toHaveTextContent("Set unit prices");
  });

  it("lists 20 openings in 20 wall groups and shows the chosen opening's stored values; an untouched Apply sends them exactly", async () => {
    const { flow } = renderEditors();
    await tab("Walls");
    expect(screen.getAllByTestId("opening-group")).toHaveLength(20);
    expect(screen.getByTestId("opening-list").querySelectorAll("button[data-opening-id]")).toHaveLength(20);
    await userEvent.click(screen.getByTestId("opening-list").querySelector(`button[data-opening-id="${swWindow.id}"]`)!);
    expect(screen.getByLabelText("Width")).toHaveValue(`5' 0"`);
    expect(screen.getByLabelText("Height")).toHaveValue(`4' 0"`);
    expect(screen.getByLabelText("Sill height")).toHaveValue(`3' 0"`);
    expect(screen.getByLabelText("Offset")).toHaveValue(`3' 6"`);
    expect(screen.getByText("From the west post axis to the rough opening's start.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Apply" }));
    expect(flow.preview).not.toHaveBeenCalled();
    expect(lastCommand(flow.apply)).toMatchObject({
      type: "SetOpening",
      args: { opening_id: swWindow.id, width_m: swWindow.width_m, height_m: swWindow.height_m, sill_height_m: swWindow.sill_height_m, offset_m: swWindow.offset_m },
    });
  });

  it("follows a picked opening or wall without changing the active tab", () => {
    const props = editorProps();
    const { rerender } = render(<Editors {...props} versions={{}} onOpenPrices={vi.fn()} selection={{ kind: "opening", id: door.id }} />);
    expect(screen.getByRole("tab", { name: "Footprint" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("opening-form")).toHaveAttribute("data-opening-id", door.id);
    const ne = wallByKey("wall/axis-x/y2/x2-x3/level-1");
    rerender(<Editors {...props} versions={{}} onOpenPrices={vi.fn()} selection={{ kind: "wall", id: ne.id }} />);
    expect(screen.getByTestId("opening-form")).toHaveAttribute("data-opening-id", "new");
    expect(screen.getByLabelText("Wall", { selector: "select" })).toHaveValue(ne.id);
  });

  it("fixes a door's sill at 0 and disables it", async () => {
    renderEditors(undefined, { kind: "opening", id: door.id });
    await tab("Walls");
    expect(screen.getByLabelText("Sill height")).toBeDisabled();
    expect(screen.getByLabelText("Sill height")).toHaveValue(`0' 0"`);
    await userEvent.click(screen.getByRole("button", { name: "New opening" }));
    await userEvent.selectOptions(screen.getByLabelText("Kind", { selector: "select" }), "DOOR");
    expect(screen.getByLabelText("Sill height")).toBeDisabled();
  });

  it("centers a 3' opening in a 12' wall at 4' 6\", and sends the computed value", async () => {
    const { flow } = renderEditors(undefined, { kind: "wall", id: wallByKey("wall/axis-x/y2/x2-x3/level-1").id });
    await tab("Walls");
    await userEvent.type(screen.getByLabelText("Width"), `3'`);
    await userEvent.type(screen.getByLabelText("Height"), `2'`);
    await userEvent.type(screen.getByLabelText("Sill height"), `3'`);
    await userEvent.click(screen.getByRole("button", { name: "Center in wall" }));
    expect(screen.getByLabelText("Offset")).toHaveValue(`4' 6"`);
    await userEvent.click(screen.getByRole("button", { name: "Add opening" }));
    const wall = wallByKey("wall/axis-x/y2/x2-x3/level-1");
    const length = Math.hypot(wall.end_m[0]! - wall.start_m[0]!, wall.end_m[1]! - wall.start_m[1]!);
    expect(lastCommand(flow.apply)).toMatchObject({ type: "AddOpening", args: { wall_id: wall.id, opening_kind: "WINDOW", width_m: 0.9144, offset_m: (length - 0.9144) / 2 } });
  });

  it("places server details on their fields, naming the other opening of an overlap", async () => {
    const ne = wallByKey("wall/axis-x/y2/x2-x3/level-1");
    const other = openings.find((o) => o.wall_id === ne.id)!;
    const command = { command_id: "c", project_id: fixture.project.project_id, base_revision_id: snapshot.revision_id, type: "AddOpening", args: { wall_id: ne.id } } as unknown as Command;
    const detail: ErrorDetail = { path: "args.offset_m", code: "OPENINGS_OVERLAP", related_paths: [`entities[${other.id}].offset_m`] };
    const error = new ApiError(422, { code: "VALIDATION_FAILED", message: "Overlap.", details: [detail] }, "x");
    renderEditors({ step: "idle", failed: { command, error } } as never, { kind: "wall", id: ne.id });
    await tab("Walls");
    const offset = screen.getByLabelText("Offset");
    expect(offset).toHaveAttribute("aria-invalid", "true");
    expect(document.getElementById("opening-offset-error")).toHaveTextContent(
      `The opening's framing overlaps another opening's (OPENINGS_OVERLAP): with Window 3' 0" × 4' 0", north wall, Level 1, x2–x3`,
    );
  });

  it("shows a SetWallAssembly rejection under the select, with the path named", async () => {
    const definition = entitiesOf(snapshot, "AssemblyDefinition").find((d) => d.id === studId)!;
    const command = { command_id: "c", project_id: fixture.project.project_id, base_revision_id: snapshot.revision_id, type: "SetWallAssembly", args: { assembly_definition_id: studId } } as unknown as Command;
    const detail: ErrorDetail = { path: `entities[${definition.id}].layers[2].framing.girt_count`, code: "GIRT_CROSSES_BRACE", related_paths: ["args.assembly_definition_id"] };
    renderEditors({ step: "idle", failed: { command, error: new ApiError(422, { code: "UNSUPPORTED_CONFIGURATION", message: "No.", details: [detail] }, "x") } } as never);
    await tab("Walls");
    expect(screen.getByTestId("wall-assembly-error")).toHaveTextContent("Stud infill: layers[2].framing.girt count: A girt would cross a knee brace (GIRT_CROSSES_BRACE)");
  });
});

describe("7. paths and messages (§8.3)", () => {
  it("maps the four commands and the wall kinds' paths to the Walls tab", () => {
    for (const type of ["SetWallAssembly", "AddOpening", "SetOpening", "RemoveOpening"]) expect(TAB_OF_COMMAND[type]).toBe("walls");
    const system = entitiesOf(snapshot, "WallSystem")[0]!;
    const details: ErrorDetail[] = [
      { path: `entities[${swWindow.id}].offset_m`, code: "OPENING_CROSSES_BRACE" },
      { path: `entities[${system.id}].default_assembly_definition_id`, code: "X" },
      { path: `entities[${strawId}].layers`, code: "X" },
    ];
    expect(otherTabs(details, snapshot, "frame")).toEqual(["walls"]);
    expect(TAB_LABEL.walls).toBe("Walls");
  });

  it("shows a detail at an opening's path with the opening's label, the raw path in its tooltip, and points to the Walls tab", () => {
    const footprint = entitiesOf(snapshot, "Footprint")[0]!;
    const path = `entities[${swWindow.id}].offset_m`;
    const error = new ApiError(422, { code: "UNSUPPORTED_CONFIGURATION", message: "No.", details: [{ path, code: "OPENING_OUTSIDE_WALL", related_paths: ["args.width_m", `entities[${footprint.id}].width_m`] }] }, "x");
    render(<ImpactDialog state={{ step: "error", command: fixture.width_command, error }} units="imperial" snapshot={snapshot} onConfirm={vi.fn()} onCancel={vi.fn()} />);
    const item = within(screen.getByTestId("dialog-details")).getByText(`Window 5' 0" × 4' 0", south wall, Level 0, x0–x1: offset`);
    expect(item).toHaveAttribute("title", path);
    expect(screen.getByTestId("dialog-details")).toHaveTextContent("The opening's framing does not fit inside the wall (OPENING_OUTSIDE_WALL)");
    expect(screen.getAllByTestId("tab-pointer").map((p) => p.textContent)).toContain("Also see the Walls tab: its values are part of this problem.");
  });

  it("has detail texts for the four new codes", () => {
    expect(DETAIL_TEXT.OPENING_OUTSIDE_WALL).toBe("The opening's framing does not fit inside the wall");
    expect(DETAIL_TEXT.OPENING_CROSSES_BRACE).toBe("The opening's framing meets a knee brace");
    expect(DETAIL_TEXT.OPENINGS_OVERLAP).toBe("The opening's framing overlaps another opening's");
    expect(DETAIL_TEXT.GIRT_CROSSES_BRACE).toBe("A girt would cross a knee brace");
  });
});

describe("8. the dialog and the assembly schedule (§9, §10)", () => {
  const review = (preview: typeof fixture.assembly_preview, command: Command) =>
    render(<ImpactDialog state={{ step: "review", command, preview }} units="imperial" snapshot={snapshot} onConfirm={vi.fn()} onCancel={vi.fn()} />);

  it("shows SetWallAssembly's wall counts, artifacts, and labeled definitions", () => {
    review(fixture.assembly_preview, fixture.assembly_command);
    expect(screen.getByTestId("impact-members")).toHaveTextContent("Timber members: 0 added, 0 removed, 0 updated.");
    expect(screen.getByTestId("impact-connections")).toHaveTextContent("Connections: 0 added, 0 removed, 0 updated.");
    expect(screen.getByTestId("impact-walls")).toHaveTextContent("Walls: 0 added, 0 removed, 20 updated.");
    expect(screen.getByTestId("impact-wall-framing")).toHaveTextContent("Wall framing: 246 added, 79 removed, 0 updated.");
    expect(screen.getByTestId("impact-artifacts")).toHaveTextContent("Updates: 2D plan, 3D model, Assembly schedule, Estimate. Unchanged: Timber schedule.");
    const row = within(screen.getByTestId("impact-changes")).getByText("default_assembly_definition_id").closest("tr")!;
    expect([...row.querySelectorAll("td")].map((td) => td.textContent)).toEqual(["WallSystem", "default_assembly_definition_id", "Straw bale", "Stud infill"]);
    expect(screen.queryByTestId("removed-openings")).toBeNull();
  });

  it("lists the 8 windows a re-identified grid line removes, above Confirm (D088)", () => {
    review(fixture.reidentify_preview, fixture.reidentify_command);
    const block = screen.getByTestId("removed-openings");
    expect(block).toHaveTextContent("These 8 openings will be removed with their walls. Undo restores them.");
    const items = within(block).getAllByRole("listitem").map((li) => li.textContent);
    expect(items).toHaveLength(8);
    expect(items.every((t) => /^Window \d' \d+"? × \d' \d+"?, (east|west) wall, Level [01], y0–y1$/.test(t!) || /^Window .*, (east|west) wall, Level [01], y1–y2$/.test(t!))).toBe(true);
    const confirm = screen.getByRole("button", { name: "Confirm" });
    expect(block.compareDocumentPosition(confirm) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByTestId("impact-walls")).toHaveTextContent("Walls: 8 added, 8 removed, 0 updated.");
    expect(screen.getByTestId("impact-wall-framing")).toHaveTextContent("Wall framing: 0 added, 32 removed, 0 updated.");
  });

  it("shows the width preview's 16 updated walls", () => {
    review(fixture.width_preview, fixture.width_command);
    expect(screen.getByTestId("impact-walls")).toHaveTextContent("Walls: 0 added, 0 removed, 16 updated.");
  });

  it("shows the assembly schedule: warning and details, declared values, figures, walls, openings, takeoff, and pieces", () => {
    render(<AssemblySchedulePanel assemblies={assemblies} units="imperial" highlight={NO_HIGHLIGHT} onSelect={vi.fn()} />);
    const climate = assemblies.warnings.find((w) => w.code === "CLIMATE_DETAILS_UNVERIFIED")!;
    expect(screen.getByTestId("climate-warning")).toHaveTextContent(climate.message);
    expect(screen.getByTestId("climate-details").querySelectorAll("li")).toHaveLength(5);
    const layers = screen.getByTestId("assembly-layers");
    expect(layers.querySelectorAll("tbody tr")).toHaveLength(3);
    expect(within(layers).getAllByText("Not declared").length).toBeGreaterThanOrEqual(6);
    const figures = screen.getByTestId("thermal-figures");
    const cells = [...figures.querySelectorAll("td")].map((td) => td.textContent);
    expect(cells.filter((t) => t !== "—").every((t) => t === "Not computed")).toBe(true);
    const missing = screen.getByTestId("missing-inputs");
    expect(missing).toHaveTextContent("Missing declared values:");
    expect(missing).toHaveTextContent("Lime plaster (conductivity or resistance)");
    expect(missing).toHaveTextContent("Spruce-pine-fir framing (conductivity)");
    expect(within(missing).getAllByRole("listitem")).toHaveLength(4);
    const wallRows = screen.getByTestId("assembly-walls").querySelectorAll("tbody tr");
    expect(wallRows).toHaveLength(20);
    for (const key of [SW0, "wall/axis-x/y0/x2-x3/level-0"]) {
      const row = screen.getByTestId("assembly-walls").querySelector(`tr[title="${key}"]`)!;
      expect(row).toHaveTextContent("2.31%");
    }
    expect(screen.getByTestId("assembly-openings").querySelectorAll("tbody tr")).toHaveLength(20);
    expect([...screen.getByTestId("assembly-framing-aggregates").querySelectorAll("tbody tr")].map((tr) => tr.getAttribute("data-piece-kind"))).toEqual(["BUCK_HEAD", "BUCK_JAMB", "BUCK_SILL"]);
    expect(screen.getByTestId("assembly-pieces").querySelectorAll("tbody tr")).toHaveLength(79);
    expect([...screen.getByTestId("assembly-assumptions").querySelectorAll("li")].map((li) => li.textContent)).toEqual(assemblyPayload.assumptions.map((a) => a.message));
    const bales = screen.getByTestId("assembly-layer-aggregates").querySelector('tr[data-layer="bales"]')!;
    expect(bales).toHaveTextContent(formatVolume(84.03687902268001, "imperial"));
    expect(screen.getByTestId("assembly-totals")).toHaveTextContent(formatArea(assemblyPayload.totals.net_area_m2, "imperial"));
  });

  it("shows test-only declared figures as served in metric and converted in imperial, each with its unit", () => {
    const declared = { ...assemblies, payload: fixture.assembly_schedule_declared.payload };
    const t = declared.payload.thermal;
    expect(fixture.assembly_schedule_declared._note).toMatch(/^TEST ONLY/);
    expect(t.all_walls.u_value_w_m2_k).not.toBeNull();
    for (const units of ["metric", "imperial"] as const) {
      cleanup();
      render(<AssemblySchedulePanel assemblies={declared} units={units} highlight={NO_HIGHLIGHT} onSelect={vi.fn()} />);
      const row = (figure: string) => [...screen.getByTestId("thermal-figures").querySelectorAll(`tr[data-figure="${figure}"] td`)].map((td) => td.textContent);
      const def = t.definitions[0]!;
      expect(row("center_of_cavity").slice(0, 2)).toEqual([formatThermal(uValue(def.center_of_cavity.u_value_w_m2_k!, units)), formatThermal(rValue(def.center_of_cavity.r_value_m2_k_w!, units))]);
      expect(row("all_walls")).toEqual([
        formatThermal(uValue(t.all_walls.u_value_w_m2_k!, units)),
        formatThermal(rValue(t.all_walls.r_value_m2_k_w!, units)),
        formatThermal(uaValue(t.all_walls.ua_w_k!, units)),
      ]);
      const lime = screen.getByTestId("assembly-layers").querySelector('tr[data-layer="lime-plaster"]')!;
      expect(lime).toHaveTextContent(formatThermal(conductivity(0.7, units)));
      expect(lime).toHaveTextContent("TEST ONLY: UI-004 fixture value, 2026-11-22");
      expect(screen.queryByTestId("missing-inputs")).toBeNull();
    }
    // Spot values: metric as served; imperial converted (IT Btu).
    expect(formatThermal(rValue(t.all_walls.r_value_m2_k_w!, "metric"))).toBe(`${t.all_walls.r_value_m2_k_w!.toFixed(2)} m²·K/W`);
    expect(formatThermal(rValue(1, "imperial"))).toBe("5.68 h·ft²·°F/Btu");
    expect(formatThermal(uValue(1, "imperial"))).toBe("0.176 Btu/(h·ft²·°F)");
    expect(formatThermal(conductivity(1, "imperial"))).toBe("6.933 Btu·in/(h·ft²·°F)");
    expect(formatThermal(uaValue(1, "imperial"))).toBe("1.9 Btu/(h·°F)");
    expect(formatThermal(null)).toBe("Not computed");
  });

  it("formats volumes and the stud infill takeoff (76 studs)", () => {
    expect(formatVolume(1, "metric")).toBe("1.00 m³");
    expect(formatVolume(0.028316846592, "imperial")).toBe("1.0 ft³");
    expect(formatVolume(84.03687902268001, "imperial")).toBe("2,967.7 ft³");
    render(<AssemblySchedulePanel assemblies={studInfill.assembly_schedule} units="imperial" highlight={NO_HIGHLIGHT} onSelect={vi.fn()} />);
    expect(screen.getByTestId("assembly-framing-aggregates").querySelector('tr[data-piece-kind="STUD"]')).toHaveTextContent(/^Stud2x676/);
    expect(screen.getByTestId("assembly-definition")).toHaveTextContent("Stud infill");
  });
});

describe("11. still preliminary (AC2b-06, AC2b-09)", () => {
  it("keeps the banner, shows the climate warning and the method notes, and never shows a thermal figure as 0", async () => {
    renderWorkspace();
    const panel = await screen.findByTestId("climate-warning");
    expect(panel).toHaveTextContent("have not been verified");
    expect(screen.getByTestId("preliminary-banner")).toHaveTextContent("Framing and estimates are preliminary");
    expect(screen.getByTestId("thermal-notes")).toHaveTextContent("Declared values, not verified. Not a code-compliance calculation.");
    const text = screen.getByTestId("assembly-schedule").textContent!;
    expect(text).not.toMatch(/\b0(\.0+)? (W\/\(m²·K\)|m²·K\/W|Btu|h·ft²)/);
    expect(text).not.toMatch(/complian(t|ce with)|meets code|passes/i);
  });
});

describe("§12 labels and palette (item 15)", () => {
  it("labels families, layer functions, opening kinds, sides, groups, walls, and openings", () => {
    expect(FAMILY_LABEL).toEqual({ STRAW_BALE: "Straw bale", STUD_INFILL: "Stud infill" });
    expect(Object.values(LAYER_FUNCTION_LABEL)).toEqual(["Finish", "Sheathing", "Insulation", "Framing layer"]);
    expect(OPENING_KIND_LABEL).toEqual({ WINDOW: "Window", DOOR: "Door" });
    expect(Object.values(SIDE_LABEL).sort()).toEqual(["East", "North", "South", "West"]);
    expect(Object.keys(FRAMING_GROUP_LABEL)).toEqual(["layout", "opening", "buck"]);
    expect(wallLabel("south", 0, SW0)).toBe("South wall, Level 0, x0–x1");
    expect(sideOfKey("wall/axis-y/x3/y0-y1/level-1", ["x0", "x1", "x2", "x3"], ["y0", "y1", "y2"])).toBe("east");
    expect(openingLabel("WINDOW", formatLength(0.9144, "imperial"), formatLength(1.2192, "imperial"), "South wall, Level 0, x1–x2")).toBe(`Window 3' 0" × 4' 0", south wall, Level 0, x1–x2`);
    // Snapshot and schedule labels agree (the snapshot's side comes from the key and the grid's line order).
    const fromSchedule = wallDetails(assemblies, revision, "imperial");
    const fromSnapshot = snapshotLabels(snapshot, "imperial");
    expect(assemblyPayload.walls).toHaveLength(20);
    for (const w of assemblyPayload.walls) {
      expect(fromSchedule.walls.get(w.wall_id)).toBe(wallLabel(w.elevation_side, w.level_index, w.generation_key));
      expect(fromSnapshot.wall(w.wall_id)).toBe(fromSchedule.walls.get(w.wall_id));
    }
    for (const o of assemblyPayload.openings) expect(fromSnapshot.opening(o.opening_id)).toBe(fromSchedule.openings.get(o.opening_id));
  });

  it("keeps the wall colors distinct from each other and from the role, type, mixed, and selection colors", () => {
    const colors = [
      ...Object.values(ROLE_COLOR),
      ...Object.values(TYPE_COLOR),
      MIXED_COLOR,
      SELECTION_COLOR.selected,
      SELECTION_COLOR.related,
      ...Object.values(LAYER_COLOR),
      ...Object.values(FRAMING_COLOR),
      WALL_BAND_COLOR,
      OPENING_COLOR,
    ];
    expect(Object.keys(LAYER_COLOR)).toHaveLength(4);
    expect(Object.keys(FRAMING_COLOR)).toHaveLength(3);
    expect(new Set(colors).size).toBe(colors.length);
    expect(NO_DETAILS.walls.size).toBe(0);
  });

  it("the snapshot's two definitions are straw bale (in use) and stud infill", () => {
    const system = entitiesOf(snapshot as Snapshot, "WallSystem")[0]!;
    expect(system.default_assembly_definition_id).toBe(strawId);
  });
});
