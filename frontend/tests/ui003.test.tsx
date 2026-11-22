/** UI-003 §13, Vitest tests 1–8 and 11, against the captured Reference House 001 v2 fixture. */

import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import * as THREE from "three";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../src/api/client";
import { CONNECTION_CATALOG } from "../src/api/connectionCatalog";
import type { Command } from "../src/api/types";
import { AppContext } from "../src/app/context";
import { readShowConnections, writeShowConnections } from "../src/app/preferences";
import { ARTIFACT_LABEL, CONNECTION_TYPE_LABEL, JUNCTION_LABEL, ROLE_LABEL, ROLES, type ConnectionType } from "../src/display/labels";
import { css, glyphColor, MIXED_COLOR, ROLE_COLOR, SELECTION_COLOR, TYPE_COLOR } from "../src/display/palette";
import { NO_HIGHLIGHT } from "../src/views/highlight";
import { groupMarkers } from "../src/views/markers";
import { buildMeshScene, MARKER_RENDER_ORDER, pick, setMarkersVisible } from "../src/views/meshScene";
import { Plan2dView } from "../src/views/Plan2dView";
import { DETAIL_TEXT } from "../src/workspace/commands";
import { Editors } from "../src/workspace/editors/Editors";
import { otherTabs, TAB_LABEL } from "../src/workspace/editors/model";
import { ImpactDialog } from "../src/workspace/ImpactDialog";
import { SchedulePanel } from "../src/workspace/panels";
import { highlightOf } from "../src/workspace/selection";
import { Workspace } from "../src/workspace/Workspace";
import { editorProps } from "./editorProps";
import { fakeApi } from "./fakeApi";
import { fixture, mesh, plan, schedule } from "./fixtures";

afterEach(cleanup);
beforeEach(() => localStorage.clear());

const planPayload = plan.payload!;
const meshPayload = mesh.payload!;
const schedulePayload = schedule.payload!;
const PLANES = { "level-0": "Level 0", "level-1": "Level 1", eave: "Eave", roof: "Roof" } as const;
const ROLE_ARRAYS = { posts: "POST", beams: "BEAM", sills: "SILL", joists: "FLOOR_JOIST", braces: "KNEE_BRACE", rafters: "PRINCIPAL_RAFTER", purlins: "PURLIN" } as const;
const plane = (id: keyof typeof PLANES) => planPayload.planes.find((p) => p.plane_id === id)!;
const glyphsIn = (container: HTMLElement) => [...container.querySelectorAll<SVGGElement>(".connection-glyph")];
const idsOf = (el: Element) => el.getAttribute("data-connection-ids")!.split(" ");

function renderPlan(showConnections = true, onSelect = vi.fn()) {
  return render(<Plan2dView plan={planPayload} units="imperial" highlight={NO_HIGHLIGHT} showConnections={showConnections} onSelect={onSelect} />);
}

function renderWorkspace() {
  const { api, calls } = fakeApi();
  render(
    <AppContext.Provider value={{ api, units: "imperial", setUnits: () => {}, signOut: () => {} }}>
      <Workspace projectId={fixture.project.project_id} revisionId={null} />
    </AppContext.Provider>,
  );
  return calls;
}

describe("1. role styling (§4)", () => {
  it("gives every served role a color and a label", () => {
    const roles = new Set([...meshPayload.members.map((m) => m.role), ...schedulePayload.members.map((m) => m.role)]);
    expect([...roles].sort()).toEqual([...ROLES].sort());
    for (const role of roles) {
      expect(ROLE_COLOR[role]).toBeTypeOf("number");
      expect(ROLE_LABEL[role]).toMatch(/^[A-Z][a-z]/);
    }
  });

  it("keeps the role, type, mixed, and selection colors pairwise distinct", () => {
    const colors = [...Object.values(ROLE_COLOR), ...Object.values(TYPE_COLOR), MIXED_COLOR, SELECTION_COLOR.selected, SELECTION_COLOR.related];
    expect(Object.keys(ROLE_COLOR)).toHaveLength(7);
    expect(Object.keys(TYPE_COLOR)).toHaveLength(5);
    expect(new Set(colors).size).toBe(colors.length);
  });

  it("draws every brace after every beam on Level 1, and the legend lists the plane's roles", async () => {
    const { container } = renderPlan();
    await userEvent.click(screen.getByRole("button", { name: "Level 1" }));
    const drawn = [...container.querySelectorAll("svg [data-member-id]")];
    const lastBeam = Math.max(...drawn.map((el, i) => (el.getAttribute("data-array") === "beams" ? i : -1)));
    const braces = drawn.map((el, i) => (el.getAttribute("data-array") === "braces" ? i : Infinity));
    expect(braces.filter(Number.isFinite).length).toBe(plane("level-1").braces.length);
    expect(Math.min(...braces)).toBeGreaterThan(lastBeam);
    // Braces have their own color, not the beams'.
    expect(container.querySelector('line[data-array="braces"]')).toHaveAttribute("stroke", css(ROLE_COLOR.KNEE_BRACE));
    for (const id of Object.keys(PLANES) as (keyof typeof PLANES)[]) {
      await userEvent.click(screen.getByRole("button", { name: PLANES[id] }));
      const expected = (Object.keys(ROLE_ARRAYS) as (keyof typeof ROLE_ARRAYS)[]).filter((a) => plane(id)[a].length > 0).map((a) => ROLE_ARRAYS[a]);
      const legend = [...screen.getByTestId("plan-legend").querySelectorAll("[data-role]")].map((li) => li.getAttribute("data-role"));
      expect(legend.sort()).toEqual(expected.sort());
    }
  });

  it("shows role swatches and labels in the schedule, with the code in the tooltip", () => {
    render(<SchedulePanel schedule={schedule} units="imperial" highlight={NO_HIGHLIGHT} onSelect={() => {}} />);
    const cell = screen.getByTestId("schedule-members").querySelector('[data-role="KNEE_BRACE"]')!;
    expect(cell).toHaveTextContent("Knee brace");
    expect(cell).toHaveAttribute("title", "KNEE_BRACE");
  });
});

describe("2. markers, one glyph per point (§5.1, item 10)", () => {
  it("groups each plane's markers into 12, 91, 46, and 28 glyphs covering exactly its markers", async () => {
    const { container } = renderPlan();
    const counts: Record<string, number> = {};
    let largest = 0;
    for (const id of Object.keys(PLANES) as (keyof typeof PLANES)[]) {
      await userEvent.click(screen.getByRole("button", { name: PLANES[id] }));
      const glyphs = glyphsIn(container);
      counts[id] = glyphs.length;
      const ids = glyphs.flatMap(idsOf);
      expect(ids.sort()).toEqual(plane(id).connections.map((c) => c.connection_id).sort());
      for (const g of glyphs) {
        expect(Number(g.getAttribute("data-connection-count"))).toBe(idsOf(g).length);
        const types = new Set(idsOf(g).map((cid) => plane(id).connections.find((c) => c.connection_id === cid)!.connection_type));
        const style = types.size === 1 ? [...types][0]! : "mixed";
        expect(g.getAttribute("data-connection-type")).toBe(style);
        expect(g.querySelector("circle")).toHaveAttribute("fill", style === "mixed" ? "#ffffff" : css(TYPE_COLOR[style as ConnectionType]));
        if (idsOf(g).length > 1) expect(g.querySelector("text")).toHaveTextContent(String(idsOf(g).length));
        largest = Math.max(largest, idsOf(g).length);
      }
      expect(container.querySelector(".plan2d")).toHaveAttribute("data-glyph-count", String(glyphs.length));
    }
    expect(counts).toEqual({ "level-0": 12, "level-1": 91, eave: 46, roof: 28 });
    expect(largest).toBe(8);
  });

  it("titles a glyph with each connection's labels and key", async () => {
    const { container } = renderPlan();
    await userEvent.click(screen.getByRole("button", { name: "Level 1" }));
    const group = glyphsIn(container).find((g) => idsOf(g).length === 8)!;
    const title = group.querySelector("title")!.textContent!.split("\n");
    expect(title).toHaveLength(8);
    expect(title.some((line) => line.startsWith("Knee brace ends · Pegged mortise and tenon · connection/brace/"))).toBe(true);
  });

  it("builds 193 3D glyphs covering the 312 connections, largest 4, colored by type or mixed", () => {
    const scene = buildMeshScene(meshPayload);
    const { glyphs, mesh: instanced } = scene.markers;
    expect(glyphs).toHaveLength(193);
    expect(instanced.count).toBe(193);
    expect(glyphs.flatMap((g) => g.markers.map((m) => m.connection_id)).sort()).toEqual(meshPayload.connections.map((c) => c.connection_id).sort());
    expect(Math.max(...glyphs.map((g) => g.markers.length))).toBe(4);
    const color = new THREE.Color();
    glyphs.forEach((glyph, i) => {
      const types = new Set(glyph.markers.map((m) => m.connection_type));
      expect(glyph.style).toBe(types.size === 1 ? [...types][0] : "mixed");
      instanced.getColorAt(i, color);
      expect(color.getHex()).toBe(new THREE.Color(glyphColor(glyph.style)).getHex());
    });
    scene.dispose();
  });

  it("groups by exact coordinates only", () => {
    const m = (id: string, at: number[], type: ConnectionType = "BRIDLE") => ({ connection_id: id, connection_type: type, junction_class: "rafter-peak", generation_key: id, at });
    const glyphs = groupMarkers([m("a", [1, 2]), m("b", [1, 2], "JOIST_HANGER"), m("c", [1, 2.0000000001]), m("d", [1, 2])], (x) => x.at);
    expect(glyphs.map((g) => [g.markers.map((x) => x.connection_id).join(""), g.style])).toEqual([["abd", "mixed"], ["c", "BRIDLE"]]);
  });
});

describe("3. 3D markers over members, and the switch (§5.3, item 11)", () => {
  it("draws markers after members without depth testing, and picks a marker before a member", () => {
    const scene = buildMeshScene(meshPayload);
    const instanced = scene.markers.mesh;
    const material = instanced.material as THREE.MeshBasicMaterial;
    expect(material.depthTest).toBe(false);
    expect(material.depthWrite).toBe(false);
    expect(instanced.renderOrder).toBe(MARKER_RENDER_ORDER);
    for (const box of scene.members.values()) expect(box.renderOrder).toBeLessThan(MARKER_RENDER_ORDER);
    // A vertical ray through a post-top glyph passes through the post and beams first.
    const glyph = scene.markers.glyphs.find((g) => g.markers.some((m) => m.junction_class === "post-beam"))!;
    const [x, y, z] = glyph.position as [number, number, number];
    const raycaster = new THREE.Raycaster(new THREE.Vector3(x, y, z + 20), new THREE.Vector3(0, 0, -1));
    const members = raycaster.intersectObjects([...scene.members.values()], false);
    const marker = raycaster.intersectObject(instanced, false)[0]!;
    expect(members[0]!.distance).toBeLessThan(marker.distance); // the ray meets a member before any glyph
    const hit = scene.markers.glyphs[marker.instanceId!]!;
    expect(hit.position[0]).toBe(x);
    expect(pick(scene, raycaster)).toEqual({ kind: "connections", ids: hit.markers.map((m) => m.connection_id) });
    setMarkersVisible(scene, false);
    expect(pick(scene, raycaster)).toEqual({ kind: "member", id: members[0]!.object.userData.memberId });
    scene.dispose();
  });

  it("reads and writes the switch through preferences.ts, on by default", () => {
    expect(readShowConnections()).toBe(true);
    writeShowConnections(false);
    expect(localStorage.getItem("homedesign.connections")).toBe("off");
    expect(readShowConnections()).toBe(false);
  });

  it("hides markers in both views when the switch is off, and remembers it", async () => {
    renderWorkspace();
    const views = await screen.findByTestId("views-paired");
    const toggle = within(views).getByRole("switch", { name: "Connections" });
    expect(toggle).toBeChecked();
    expect(views.querySelectorAll(".connection-glyph")).toHaveLength(12);
    expect(views.querySelector(".mesh3d")).toHaveAttribute("data-glyph-count", "193");
    await userEvent.click(toggle);
    expect(views.querySelectorAll(".connection-glyph")).toHaveLength(0);
    expect(views.querySelector(".mesh3d")).toHaveAttribute("data-glyph-count", "0");
    expect(views.querySelector(".mesh3d")).toHaveAttribute("data-connection-count", "312");
    expect(readShowConnections()).toBe(false);
    // The schedule's connection tables are unaffected.
    expect(await screen.findByTestId("schedule-connections")).toHaveTextContent("Connections (312)");
  });
});

describe("4. selection (§6)", () => {
  it("highlights a selected connection's glyph and both members in the plan and the member table", async () => {
    renderWorkspace();
    const list = await screen.findByTestId("schedule-connections");
    const marker = plane("level-0").connections[0]!;
    const row = schedulePayload.connections.find((c) => c.connection_id === marker.connection_id)!;
    await userEvent.click(list.querySelector(`tr[data-connection-id="${marker.connection_id}"]`)!);
    const views = screen.getByTestId("views-paired");
    const glyph = [...views.querySelectorAll(".connection-glyph")].find((g) => idsOf(g).includes(marker.connection_id))!;
    expect(glyph).toHaveClass("selected");
    expect(list.querySelector(`tr[data-connection-id="${marker.connection_id}"]`)).toHaveAttribute("aria-selected", "true");
    for (const memberId of row.member_ids) {
      const drawn = views.querySelector(`.plan2d [data-member-id="${memberId}"]`);
      if (drawn) {
        expect(drawn).toHaveClass("related");
        expect(drawn.getAttribute(drawn.tagName === "rect" ? "fill" : "stroke")).toBe(css(SELECTION_COLOR.related));
      }
      expect(screen.getByTestId("schedule-members").querySelector(`tr[data-member-id="${memberId}"]`)).toHaveClass("related");
    }
    // At least one of the two (the post) is drawn on Level 0.
    expect(row.member_ids.some((id) => views.querySelector(`.plan2d [data-member-id="${id}"]`))).toBe(true);
    // Selecting it again clears the selection.
    await userEvent.click(list.querySelector(`tr[data-connection-id="${marker.connection_id}"]`)!);
    expect(glyph).not.toHaveClass("selected");
  });

  it("selects all of a group glyph's connections, and a member as before", async () => {
    renderWorkspace();
    const views = await screen.findByTestId("views-paired");
    await screen.findByTestId("schedule-connections");
    await userEvent.click(within(views).getByRole("button", { name: "Level 1" }));
    const group = [...views.querySelectorAll(".connection-glyph")].find((g) => idsOf(g).length === 8)!;
    await userEvent.click(group);
    const selected = [...screen.getByTestId("schedule-connections").querySelectorAll('tr[aria-selected="true"]')].map((tr) => tr.getAttribute("data-connection-id"));
    expect(selected.sort()).toEqual(idsOf(group).sort());
    const beam = views.querySelector('.plan2d line[data-array="beams"]')!;
    await userEvent.click(beam);
    expect(beam).toHaveClass("selected");
    expect(screen.getByTestId("schedule-members").querySelector(`tr[data-member-id="${beam.getAttribute("data-member-id")}"]`)).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("schedule-connections").querySelectorAll('tr[aria-selected="true"]')).toHaveLength(0);
  });

  it("highlights only the connections without a CURRENT schedule for the views' revision", () => {
    const ids = [schedulePayload.connections[0]!.connection_id];
    const current = highlightOf({ kind: "connections", ids }, schedule, schedule.source_revision_id);
    expect([...current.related].sort()).toEqual([...schedulePayload.connections[0]!.member_ids].sort());
    for (const h of [
      highlightOf({ kind: "connections", ids }, null, schedule.source_revision_id),
      highlightOf({ kind: "connections", ids }, { ...schedule, status: "STALE" }, schedule.source_revision_id),
      highlightOf({ kind: "connections", ids }, schedule, "another-revision"),
    ]) {
      expect([...h.connections]).toEqual(ids);
      expect(h.related.size).toBe(0);
    }
  });
});

const tab = (name: string) => userEvent.click(screen.getByRole("tab", { name }));
const lastCommand = (spy: { mock: { calls: unknown[][] } }) => spy.mock.calls.at(-1)![0] as Command & { args: Record<string, unknown> };

function renderEditors(state?: ReturnType<typeof editorProps>["flow"]["state"]) {
  const props = editorProps();
  const flow = state ? { ...props.flow, state } : props.flow;
  render(<Editors {...props} flow={flow as typeof props.flow} versions={{}} onOpenPrices={vi.fn()} />);
  return props;
}

describe("5. the Frame tab (§7.1)", () => {
  it("lists the tabs in order", () => {
    // Eight since UI-004 added Walls (D087); this title is traced in vs-02-traceability.md (AC2-08.2).
    renderEditors();
    expect(screen.getAllByRole("tab").map((t) => t.textContent)).toEqual(["Footprint", "Stories", "Roof", "Grid", "Frame", "Sections", "Connections", "Walls"]);
    expect(Object.values(TAB_LABEL)).toEqual(["Footprint", "Stories", "Roof", "Grid", "Frame", "Sections", "Connections", "Walls"]);
  });

  it("shows the stored values and sends them exactly when untouched", async () => {
    const { flow } = renderEditors();
    await tab("Frame");
    expect(screen.getByRole("textbox", { name: "Joist spacing" })).toHaveValue(`2' 0"`);
    expect(screen.getByRole("textbox", { name: "Purlins per slope" })).toHaveValue("2");
    expect(screen.getByRole("textbox", { name: "Knee brace leg" })).toHaveValue(`3' 0"`);
    expect(screen.getByRole("checkbox", { name: "Knee braces on Level 1" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "Knee braces at the eave" })).toBeChecked();
    await userEvent.click(screen.getByRole("button", { name: "Preview" }));
    expect(lastCommand(flow.preview)).toMatchObject({
      type: "SetFrameParameters",
      args: { joist_spacing_m: 0.6096, purlins_per_slope: 2, knee_brace_leg_m: 0.9144, knee_braces_level_1: true, knee_braces_eave: true },
    });
  });

  it("treats a fractional purlin count as a parse error, with no preview", async () => {
    const { flow } = renderEditors();
    await tab("Frame");
    const purlins = screen.getByRole("textbox", { name: "Purlins per slope" });
    await userEvent.clear(purlins);
    await userEvent.type(purlins, "2.5");
    await userEvent.click(screen.getByRole("button", { name: "Preview" }));
    expect(flow.preview).not.toHaveBeenCalled();
    expect(purlins).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("Enter a whole number")).toBeInTheDocument();
  });

  it("previews eave braces off with the other four stored values", async () => {
    const { flow } = renderEditors();
    await tab("Frame");
    await userEvent.click(screen.getByRole("checkbox", { name: "Knee braces at the eave" }));
    await userEvent.click(screen.getByRole("button", { name: "Preview" }));
    expect(lastCommand(flow.preview).args).toEqual(fixture.frame_command.args);
    expect(lastCommand(flow.preview).args).toEqual({ joist_spacing_m: 0.6096, purlins_per_slope: 2, knee_brace_leg_m: 0.9144, knee_braces_level_1: true, knee_braces_eave: false });
  });

  it("places an argument detail on its field", async () => {
    const error = new ApiError(422, { code: "UNSUPPORTED_CONFIGURATION", message: "No.", details: [{ path: "entities[f].parameters.knee_brace_leg_m", code: "OUT_OF_SUPPORTED_RANGE", related_paths: ["args.knee_brace_leg_m"] }] }, "x");
    renderEditors({ step: "idle", failed: { command: fixture.frame_command, error } } as never);
    await tab("Frame");
    expect(screen.getByRole("textbox", { name: "Knee brace leg" })).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("textbox", { name: "Joist spacing" })).toHaveAttribute("aria-invalid", "false");
  });
});

describe("6. connection types (§7.2)", () => {
  const frameSystem = fixture.snapshot.entities.find((e) => e.kind === "FrameSystem");
  const storedTypes = (frameSystem?.kind === "FrameSystem" ? frameSystem.connection_defaults : {}) as Record<string, string>;

  it("shows seven rows in D054 order with their counts and exactly two catalog types each", async () => {
    renderEditors();
    await tab("Connections");
    const rows = [...screen.getByTestId("connection-types").querySelectorAll("tbody tr")];
    expect(rows.map((r) => r.getAttribute("data-junction-class"))).toEqual(["post-beam", "post-sill", "brace", "joist-beam", "rafter-peak", "rafter-foot", "purlin-rafter"]);
    expect(rows.map((r) => r.querySelector('[data-testid^="connection-count-"]')!.textContent)).toEqual(["68", "12", "136", "60", "4", "8", "24"]);
    for (const row of rows) {
      const junction = row.getAttribute("data-junction-class")!;
      const entry = CONNECTION_CATALOG.junction_classes.find((c) => c.junction_class === junction)!;
      const select = within(row as HTMLElement).getByRole("combobox", { name: JUNCTION_LABEL[entry.junction_class] });
      expect([...select.querySelectorAll("option")].map((o) => o.value)).toEqual([entry.default, entry.alternative]);
      expect(select).toHaveValue(storedTypes[junction]); // the stored type (here the D054 default)
      expect(within(row as HTMLElement).getByRole("button", { name: /^Preview / })).toBeDisabled();
    }
    expect(screen.getByRole("combobox", { name: "Joist–beam" })).toHaveDisplayValue("Housed dovetail (traditional)");
    expect(screen.getByTestId("connection-type-descriptions")).toHaveTextContent("Housed dovetail. Representational only: no capacity, sizes, or fasteners.");
    expect(screen.getByTestId("connection-pricing-note")).toHaveTextContent("connection.PEGGED_MORTISE_TENON");
  });

  it("previews Joist hanger for joist-beam", async () => {
    const { flow } = renderEditors();
    await tab("Connections");
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Joist–beam" }), "JOIST_HANGER");
    expect(screen.getByTestId("connection-type-descriptions")).toHaveTextContent("Joist hanger. Representational only");
    await userEvent.click(screen.getByRole("button", { name: "Preview Joist–beam change" }));
    expect(lastCommand(flow.preview)).toMatchObject({ type: "SetConnectionType", args: { junction_class: "joist-beam", connection_type: "JOIST_HANGER" } });
  });

  it("shows a row error on the submitted row", async () => {
    const command = { ...fixture.type_command, args: { junction_class: "joist-beam", connection_type: "BRIDLE" } } as Command;
    const error = new ApiError(422, { code: "UNSUPPORTED_CONFIGURATION", message: "No.", details: [{ path: 'entities[f].connection_defaults["joist-beam"]', code: "UNSUPPORTED_VALUE", related_paths: ["args.connection_type"] }] }, "x");
    renderEditors({ step: "idle", failed: { command, error } } as never);
    await tab("Connections");
    const row = screen.getByTestId("connection-types").querySelector('tr[data-junction-class="joist-beam"]') as HTMLElement;
    expect(within(row).getByRole("alert")).toHaveTextContent("Not supported (UNSUPPORTED_VALUE)");
    expect(screen.getAllByRole("alert", { hidden: true })).toHaveLength(1);
  });

  it("says a class with no connections is still editable", () => {
    const snapshot = { ...fixture.snapshot, entities: fixture.snapshot.entities.filter((e) => !(e.kind === "Connection" && e.junction_class === "brace")) };
    const props = editorProps();
    render(<Editors {...props} snapshot={snapshot} versions={{}} onOpenPrices={null} />);
    expect(screen.getByTestId("connection-count-brace")).toHaveTextContent("None in the current frame");
  });
});

describe("7. paths and messages (§7.3)", () => {
  const frame = fixture.snapshot.entities.find((e) => e.kind === "FrameSystem")!.id;
  const at = (path: string) => [{ path, code: "X" }];

  it("maps FrameSystem paths to tabs by field", () => {
    expect(otherTabs(at(`entities[${frame}].parameters.knee_brace_leg_m`), fixture.snapshot, "grid")).toEqual(["frame"]);
    expect(otherTabs(at(`entities[${frame}].connection_defaults["post-beam"]`), fixture.snapshot, "grid")).toEqual(["connections"]);
    expect(otherTabs(at(`entities[${frame}].member_defaults.BEAM`), fixture.snapshot, "grid")).toEqual(["sections"]);
    expect(otherTabs(at(`entities[${frame}].member_ids`), fixture.snapshot, "grid")).toEqual(["sections"]);
    expect(otherTabs(at(`entities[${frame}].parameters.knee_brace_leg_m`), fixture.snapshot, "frame")).toEqual([]);
  });

  it("no detail text mentions VS-01", () => {
    for (const text of Object.values(DETAIL_TEXT)) expect(text).not.toContain("VS-01");
    expect(DETAIL_TEXT.OUT_OF_SUPPORTED_RANGE).toBe("Outside the supported range");
    expect(DETAIL_TEXT.UNSUPPORTED_VALUE).toBe("Not supported");
  });
});

describe("8. schedule and dialog (§8, §9)", () => {
  it("shows the connection counts, the types in use, and the connection list", async () => {
    const onSelect = vi.fn();
    render(<SchedulePanel schedule={schedule} units="imperial" highlight={NO_HIGHLIGHT} onSelect={onSelect} />);
    const counts = screen.getByTestId("schedule-connection-aggregates");
    expect(within(counts).getAllByRole("row")).toHaveLength(8); // seven and the header
    expect(counts.querySelector('tr[data-junction-class="joist-beam"]')).toHaveTextContent("Joist–beamHoused dovetail60");
    const types = [...screen.getByTestId("schedule-connection-types").querySelectorAll("tbody tr")];
    expect(types.map((t) => t.getAttribute("data-connection-type")).sort()).toEqual(schedulePayload.connection_catalog.types.map((t) => t.connection_type).sort());
    for (const t of types) expect(t).toHaveTextContent("Representational only: no capacity, sizes, or fasteners.");
    const list = screen.getByTestId("schedule-connections");
    expect(list).toHaveTextContent("Connections (312)");
    expect(within(list).getAllByRole("row")).toHaveLength(313);
    const first = schedulePayload.connections[0]!;
    const row = list.querySelector(`tr[data-connection-id="${first.connection_id}"]`) as HTMLElement;
    const keys = first.member_ids.map((id) => schedulePayload.members.find((m) => m.member_id === id)!.generation_key);
    expect(within(row).getAllByRole("button").map((b) => b.textContent)).toEqual(keys);
    await userEvent.click(within(row).getAllByRole("button")[1]!);
    expect(onSelect).toHaveBeenLastCalledWith({ kind: "member", id: first.member_ids[1] }, false);
    await userEvent.click(row.querySelector("td")!);
    expect(onSelect).toHaveBeenLastCalledWith({ kind: "connections", ids: [first.connection_id] });
  });

  const dialog = (preview: typeof fixture.width_preview, command: Command = fixture.width_command) =>
    render(<ImpactDialog state={{ step: "review", command, preview }} units="imperial" snapshot={fixture.snapshot} onConfirm={() => {}} onCancel={() => {}} />);

  it("names the artifacts that update and those unchanged", () => {
    dialog(fixture.width_preview);
    expect(screen.getByTestId("impact-artifacts")).toHaveTextContent(/^Updates: 2D plan, 3D model, Timber schedule, Assembly schedule, Estimate\.$/);
    cleanup();
    dialog({ ...fixture.width_preview, impacted_artifacts: ["mesh3d", "plan2d"] });
    expect(screen.getByTestId("impact-artifacts")).toHaveTextContent(/^Updates: 2D plan, 3D model\. Unchanged: Timber schedule, Assembly schedule, Estimate\.$/);
    expect(Object.values(ARTIFACT_LABEL)).toEqual(["2D plan", "3D model", "Timber schedule", "Assembly schedule", "Estimate"]);
  });

  it("shows the frame preview's connection counts and its parameter change", () => {
    dialog(fixture.frame_preview, fixture.frame_command);
    const c = fixture.frame_preview.connections;
    expect([c.added.length, c.removed.length, c.updated.length]).toEqual([0, 68, 0]);
    expect(screen.getByTestId("impact-connections")).toHaveTextContent("Connections: 0 added, 68 removed, 0 updated.");
    expect(screen.getByTestId("impact-members")).toHaveTextContent("Timber members: 0 added, 34 removed, 0 updated.");
    const changes = screen.getByTestId("impact-changes");
    expect(changes).toHaveTextContent("FrameSystemparameters.knee_braces_eavetruefalse");
    expect(changes).not.toHaveTextContent("parameters.joist_spacing_m");
  });

  it("labels connection-type values and formats parameter lengths", () => {
    dialog(fixture.type_preview, fixture.type_command);
    expect(screen.getByTestId("impact-changes")).toHaveTextContent(`FrameSystemconnection_defaults["joist-beam"]Housed dovetailJoist hanger`);
    expect(screen.getByTestId("impact-connections")).toHaveTextContent("Connections: 0 added, 0 removed, 60 updated.");
    cleanup();
    const change = fixture.frame_preview.changes.find((x) => x.field === "parameters")!;
    const moved = { ...change, after: { ...(change.before as object), joist_spacing_m: 0.65 } };
    dialog({ ...fixture.frame_preview, changes: [moved] }, fixture.frame_command);
    expect(screen.getByTestId("impact-changes")).toHaveTextContent(`parameters.joist_spacing_m2' 0"2' 1 9/16"`);
  });

  it("keeps the empty case and Confirm", () => {
    dialog({ ...fixture.type_preview, impacted_artifacts: [] }, fixture.type_command);
    expect(screen.getByTestId("impact-artifacts")).toHaveTextContent(/^No derived views or reports change\.$/);
    expect(screen.getByRole("button", { name: "Confirm" })).toBeEnabled();
  });
});

describe("11. still preliminary (AC2-07)", () => {
  it("every type description says representational only, and no glyph carries a size", async () => {
    for (const t of CONNECTION_CATALOG.connection_types) expect(t.description).toContain("Representational only");
    expect(Object.keys(CONNECTION_TYPE_LABEL).sort()).toEqual(CONNECTION_CATALOG.connection_types.map((t) => t.connection_type).sort());
    const { container } = renderPlan();
    await userEvent.click(screen.getByRole("button", { name: "Level 1" }));
    const radii = new Set(glyphsIn(container).map((g) => g.querySelector("circle")!.getAttribute("r")));
    expect(radii.size).toBe(1); // one fixed symbol size, whatever the joint
    for (const g of glyphsIn(container)) expect(g.querySelector("title")!.textContent).not.toMatch(/capacity|\d+\s*(mm|in|")/);
  });

  it("shows the preliminary banner in the workspace", async () => {
    renderWorkspace();
    await waitFor(() => expect(screen.getByTestId("preliminary-banner")).toHaveTextContent(plan.warnings.find((w) => w.code === "PRELIMINARY_UNVERIFIED")!.message));
  });
});
