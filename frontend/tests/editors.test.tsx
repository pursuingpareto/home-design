import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Command, CommitResponse } from "../src/api/types";
import { Editors } from "../src/workspace/editors/Editors";
import { ImpactDialog } from "../src/workspace/ImpactDialog";
import { ApiError } from "../src/api/client";
import { editorProps } from "./editorProps";
import { fixture } from "./fixtures";

afterEach(cleanup);

function renderEditors(preview = vi.fn(async (_: Command) => {}), apply = vi.fn(async (_: Command): Promise<CommitResponse | null> => null)) {
  const props = editorProps(preview, apply);
  render(<Editors {...props} versions={{}} onOpenPrices={vi.fn()} />);
  return { ...props, preview, apply };
}

const tab = (name: string) => userEvent.click(screen.getByRole("tab", { name }));
const lastCommand = (spy: { mock: { calls: unknown[][] } }) => spy.mock.calls.at(-1)![0] as Command & { args: Record<string, unknown> };

describe("tabbed editors (UI-002)", () => {
  it("shows Reference House 001 values in every tab", async () => {
    renderEditors();
    expect(screen.getByRole("textbox", { name: /Width/ })).toHaveValue(`36' 0"`);
    await tab("Stories");
    expect(screen.getByRole("textbox", { name: "Level 0 story height" })).toHaveValue(`10' 0"`);
    expect(screen.getByRole("textbox", { name: "Level 1 story height" })).toHaveValue(`9' 0"`);
    expect(screen.getByTestId("level-1-elevation")).toHaveTextContent(`Level 1 elevation: 10' 0"`);
    await tab("Roof");
    expect(screen.getByRole("textbox", { name: "Pitch" })).toHaveValue("9/12");
    expect(screen.getByRole("textbox", { name: "Eave overhang" })).toHaveValue(`2' 0"`);
    await tab("Grid");
    const x = screen.getByTestId("grid-x");
    expect(within(x).getByRole("textbox", { name: "x1" })).toHaveValue(`12' 0"`);
    expect(within(x).getByRole("textbox", { name: "x2" })).toHaveValue(`24' 0"`);
    expect(within(screen.getByTestId("grid-y")).getByRole("textbox", { name: "y1" })).toHaveValue(`12' 0"`);
    await tab("Sections");
    const catalog = screen.getByTestId("section-catalog");
    expect(catalog).toHaveTextContent(`8x8`);
    expect(catalog).toHaveTextContent(`8x12`);
    expect(screen.getByRole("combobox", { name: "Beam" })).toHaveDisplayValue("8x12");
    expect(screen.getByRole("combobox", { name: "Post" })).toHaveDisplayValue("8x8");
  });

  it("keeps typed values across tab switches", async () => {
    renderEditors();
    await userEvent.clear(screen.getByRole("textbox", { name: /Width/ }));
    await userEvent.type(screen.getByRole("textbox", { name: /Width/ }), "40'");
    await tab("Roof");
    await tab("Footprint");
    expect(screen.getByRole("textbox", { name: /Width/ })).toHaveValue("40'");
  });

  it("previews story heights, sending untouched values exactly", async () => {
    const { preview } = renderEditors();
    await tab("Stories");
    const l1 = screen.getByRole("textbox", { name: "Level 1 story height" });
    await userEvent.clear(l1);
    await userEvent.type(l1, "10'");
    await userEvent.click(screen.getByRole("button", { name: "Preview" }));
    expect(lastCommand(preview)).toMatchObject({ type: "SetStoryHeights", args: { story_heights_m: [3.048, 3.048] } });
  });

  it("previews a roof change (consequential since D057)", async () => {
    const apply = vi.fn(async (_: Command) => null);
    const { preview } = renderEditors(undefined, apply);
    await tab("Roof");
    const pitch = screen.getByRole("textbox", { name: "Pitch" });
    await userEvent.clear(pitch);
    await userEvent.type(pitch, "10/12");
    await userEvent.click(screen.getByRole("button", { name: "Preview" }));
    expect(apply).not.toHaveBeenCalled();
    expect(lastCommand(preview)).toMatchObject({ type: "SetGableRoofParameters", args: { pitch_rad: Math.atan(10 / 12), eave_overhang_m: 0.6096 } });
  });

  it("builds the grid command from positions and equal bays", async () => {
    const { preview } = renderEditors();
    await tab("Grid");
    const x = screen.getByTestId("grid-x");
    await userEvent.clear(within(x).getByRole("spinbutton"));
    await userEvent.type(within(x).getByRole("spinbutton"), "4");
    await userEvent.click(within(x).getByRole("button", { name: "Divide" }));
    expect(within(x).getAllByRole("row")).toHaveLength(6);
    await userEvent.click(screen.getByRole("button", { name: "Preview" }));
    const command = lastCommand(preview);
    expect(command.type).toBe("SetTimberGrid");
    expect(command.args.x_lines).toEqual([{ id: "x0", fraction: 0 }, { id: "x1", fraction: 0.25 }, { id: "x2", fraction: 0.5 }, { fraction: 0.75 }, { id: "x3", fraction: 1 }]);
    const grid = fixture.snapshot.entities.find((e) => e.kind === "TimberGrid");
    expect(command.args.y_lines).toEqual(grid?.kind === "TimberGrid" ? grid.y_lines : null);
  });

  it("submitting an untouched grid sends the stored grid exactly", async () => {
    const { preview } = renderEditors();
    await tab("Grid");
    await userEvent.click(screen.getByRole("button", { name: "Preview" }));
    const grid = fixture.snapshot.entities.find((e) => e.kind === "TimberGrid");
    expect(lastCommand(preview).args).toEqual(grid?.kind === "TimberGrid" ? { x_lines: grid.x_lines, y_lines: grid.y_lines } : null);
  });

  it("adds a section directly and previews a role's section change", async () => {
    const apply = vi.fn(async (_: Command) => ({ revision_id: "r2", sequence: 2, is_noop: false }) as CommitResponse);
    const preview = vi.fn(async (_: Command) => {});
    renderEditors(preview, apply);
    await tab("Sections");
    await userEvent.type(screen.getByRole("textbox", { name: "Label" }), "10x12");
    await userEvent.type(screen.getByRole("textbox", { name: "Actual width" }), `9 1/2"`);
    await userEvent.type(screen.getByRole("textbox", { name: "Actual depth" }), `11 1/2"`);
    await userEvent.click(screen.getByRole("button", { name: "Add section" }));
    expect(lastCommand(apply)).toMatchObject({ type: "AddSection", args: { nominal_label: "10x12", actual_width_m: 0.2413, actual_depth_m: 0.2921 } });
    expect(preview).not.toHaveBeenCalled();

    const post = fixture.snapshot.entities.find((e) => e.kind === "Section" && e.nominal_label === "8x8")!;
    const beamSelect = screen.getByRole("combobox", { name: "Beam" });
    expect(screen.getByRole("button", { name: "Preview Beam change" })).toBeDisabled();
    await userEvent.selectOptions(beamSelect, "8x8");
    await userEvent.click(screen.getByRole("button", { name: "Preview Beam change" }));
    expect(lastCommand(preview)).toMatchObject({ type: "SetMemberSection", args: { role: "BEAM", section_id: post.id } });
    expect(screen.getByTestId("pricing-note")).toHaveTextContent("timber.BEAM.8x12");
  });

  it("puts server errors on the submitted fields", async () => {
    const props = editorProps();
    const error = new ApiError(422, { code: "UNSUPPORTED_CONFIGURATION", message: "Out of range.", details: [{ path: "entities[x].pitch_rad", code: "OUT_OF_SUPPORTED_RANGE", related_paths: ["args.pitch_rad"] }], request_id: "r" }, "");
    const command = { command_id: "c", project_id: "p", base_revision_id: "b", type: "SetGableRoofParameters" as const, args: { pitch_rad: 1.2, eave_overhang_m: 0.6 } };
    render(<Editors {...props} flow={{ ...props.flow, state: { step: "error", command, error } }} versions={{}} onOpenPrices={null} />);
    await tab("Roof");
    expect(screen.getByRole("textbox", { name: "Pitch" })).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("textbox", { name: "Eave overhang" })).toHaveAttribute("aria-invalid", "false");
  });

  it("points to other tabs named in an error (UI-002 §7)", () => {
    const grid = fixture.snapshot.entities.find((e) => e.kind === "TimberGrid")!;
    const footprint = fixture.snapshot.entities.find((e) => e.kind === "Footprint")!;
    const error = new ApiError(422, { code: "UNSUPPORTED_CONFIGURATION", message: "Bay too long.", details: [{ path: `entities[${grid.id}].x_lines`, code: "OUT_OF_SUPPORTED_RANGE", related_paths: ["args.width_m", `entities[${footprint.id}].width_m`] }], request_id: "r" }, "");
    render(<ImpactDialog state={{ step: "error", command: fixture.width_command, error }} units="imperial" snapshot={fixture.snapshot} onConfirm={() => {}} onCancel={() => {}} />);
    expect(screen.getAllByTestId("tab-pointer").map((p) => p.textContent)).toEqual(["Also see the Grid tab: its values are part of this problem."]);
  });
});
