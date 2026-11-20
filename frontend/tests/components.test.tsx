import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppContext } from "../src/app/context";
import { Plan2dView } from "../src/views/Plan2dView";
import { placeDetails } from "../src/workspace/commands";
import { FootprintEditor } from "../src/workspace/editors/FootprintEditor";
import { ImpactDialog } from "../src/workspace/ImpactDialog";
import { EstimatePanel, PreliminaryBanner, SchedulePanel } from "../src/workspace/panels";
import { buildBook, initialRows } from "../src/workspace/PriceBookForm";
import { Workspace } from "../src/workspace/Workspace";
import { editorProps } from "./editorProps";
import { fakeApi } from "./fakeApi";
import { catalog, estimateComplete, estimateNone, fixture, plan, schedule } from "./fixtures";

afterEach(cleanup);

describe("Plan2dView", () => {
  it("labels dimensions from value_m and shows every member of each plane", async () => {
    const { container } = render(<Plan2dView plan={plan.payload!} units="imperial" selected={null} onSelect={() => {}} />);
    expect(screen.getByTestId("dim-footprint-width")).toHaveTextContent(`Width: 36' 0"`);
    expect(screen.getByTestId("dim-footprint-depth")).toHaveTextContent(`Depth: 24' 0"`);
    expect(screen.getByRole("img")).toHaveAccessibleName(`Plan, Level 0. Width 36' 0", Depth 24' 0".`);
    const ids: string[] = [];
    for (const label of ["Level 0", "Level 1", "Eave", "Roof"]) {
      await userEvent.click(screen.getByRole("button", { name: label }));
      container.querySelectorAll("[data-member-id]").forEach((el) => ids.push(el.getAttribute("data-member-id")!));
    }
    // Every role, once (ART-002 §4.1, §9).
    expect(ids.sort()).toEqual(schedule.payload!.members.map((m) => m.member_id).sort());
  });

  it("shows rafters and purlins on the roof tab, drawn neutrally", async () => {
    const { container } = render(<Plan2dView plan={plan.payload!} units="imperial" selected={null} onSelect={() => {}} />);
    await userEvent.click(screen.getByRole("button", { name: "Roof" }));
    expect(screen.getByRole("img")).toHaveAccessibleName(/^Plan, Roof\./);
    expect(container.querySelectorAll('line[data-array="rafters"]')).toHaveLength(8);
    expect(container.querySelectorAll('line[data-array="purlins"]')).toHaveLength(12);
    expect(container.querySelectorAll(".member")).toHaveLength(20);
    expect(container.querySelectorAll(".post, .beam")).toHaveLength(0);
  });

  it("reports selection by member ID", async () => {
    const onSelect = vi.fn();
    const { container } = render(<Plan2dView plan={plan.payload!} units="metric" selected={null} onSelect={onSelect} />);
    const first = container.querySelector("[data-member-id]")!;
    await userEvent.click(first);
    expect(onSelect).toHaveBeenCalledWith(first.getAttribute("data-member-id"));
    expect(screen.getByTestId("dim-footprint-width")).toHaveTextContent("10.973 m");
  });
});

describe("panels", () => {
  it("shows the envelope's preliminary message", () => {
    render(<PreliminaryBanner envelopes={[null, plan]} />);
    const message = plan.warnings.find((w) => w.code === "PRELIMINARY_UNVERIFIED")!.message;
    expect(screen.getByTestId("preliminary-banner")).toHaveTextContent(message);
  });

  it("shows an unavailable estimate as not configured, never a zero total", () => {
    render(<EstimatePanel estimate={estimateNone} catalog={catalog} units="imperial" onEditPrices={null} />);
    expect(screen.getByTestId("estimate-unavailable")).toHaveTextContent("Costs not configured");
    expect(screen.queryByTestId("estimate-total")).toBeNull();
    expect(screen.getByTestId("estimate")).not.toHaveTextContent("$0.00");
  });

  it("shows a complete estimate's total and book", () => {
    render(<EstimatePanel estimate={estimateComplete} catalog={catalog} units="imperial" onEditPrices={null} />);
    const total = estimateComplete.payload!.totals.grand_total_minor!;
    expect(screen.getByTestId("estimate-total")).toHaveTextContent(`$${(total / 100).toLocaleString("en-US", { minimumFractionDigits: 2 })}`);
    expect(screen.getByTestId("estimate-coverage")).toHaveTextContent("Fixture supplier quote");
  });

  it("shows connection lines as counts priced each, with the type's description (ART-002 §9)", () => {
    const { container } = render(<EstimatePanel estimate={estimateComplete} catalog={catalog} units="imperial" onEditPrices={null} />);
    const row = container.querySelector('tr[data-key="connection.PEGGED_MORTISE_TENON"]')!;
    const cells = [...row.querySelectorAll("td")].map((td) => td.textContent);
    const line = estimateComplete.payload!.line_items.find((li) => li.key === "connection.PEGGED_MORTISE_TENON")!;
    expect(cells).toEqual([
      "Pegged mortise and tenon. Representational only: no capacity, sizes, or fasteners.",
      "248 each",
      `$${(line.unit_price_minor! / 100).toFixed(2)} each`,
      `$${(line.amount_minor! / 100).toLocaleString("en-US", { minimumFractionDigits: 2 })}`,
    ]);
    const timber = [...container.querySelector('tr[data-key="timber.BEAM.8x12"]')!.querySelectorAll("td")].map((td) => td.textContent);
    expect(timber[0]).toBe("BEAM 8x12");
    expect(timber[2]).toMatch(/^\$47\.25\/m ≈ \$/);
  });

  it("falls back to the connection type without a catalog", () => {
    const { container } = render(<EstimatePanel estimate={estimateComplete} catalog={null} units="metric" onEditPrices={null} />);
    expect(container.querySelector('tr[data-key="connection.BRIDLE"] td')).toHaveTextContent("BRIDLE");
  });

  it("lists every schedule member and the aggregates", async () => {
    const onSelect = vi.fn();
    render(<SchedulePanel schedule={schedule} units="imperial" selected={null} onSelect={onSelect} />);
    expect(within(screen.getByTestId("schedule-members")).getAllByRole("row")).toHaveLength(194);
    expect(screen.getByTestId("schedule-aggregates")).toHaveTextContent("BEAM8x1234");
    await userEvent.click(screen.getAllByRole("button", { name: /frame\// })[0]!);
    expect(onSelect).toHaveBeenCalledWith(schedule.payload!.members[0]!.member_id);
  });
});

describe("edit flow pieces", () => {
  it("previews with stored values for untouched fields and parsed values for edited ones", async () => {
    const onPreview = vi.fn();
    render(<FootprintEditor {...editorProps(onPreview)} />);
    const width = screen.getByLabelText(/Width/);
    expect(width).toHaveValue(`36' 0"`);
    await userEvent.clear(width);
    await userEvent.type(width, "40'");
    await userEvent.click(screen.getByRole("button", { name: "Preview" }));
    const command = onPreview.mock.calls[0]![0];
    expect(command.args).toEqual({ width_m: 12.192, depth_m: 7.3152 });
    expect(command.base_revision_id).toBe(fixture.snapshot.revision_id);
  });

  it("re-entering the current width sends the stored value exactly (a no-op)", async () => {
    const onPreview = vi.fn();
    render(<FootprintEditor {...editorProps(onPreview)} />);
    const width = screen.getByLabelText(/Width/);
    await userEvent.clear(width);
    await userEvent.type(width, "36'");
    await userEvent.click(screen.getByRole("button", { name: "Preview" }));
    expect(onPreview.mock.calls[0]![0].args.width_m).toBe(10.9728);
  });

  it("shows parse errors without previewing", async () => {
    const onPreview = vi.fn();
    render(<FootprintEditor {...editorProps(onPreview)} />);
    await userEvent.clear(screen.getByLabelText(/Depth/));
    await userEvent.type(screen.getByLabelText(/Depth/), "lots");
    await userEvent.click(screen.getByRole("button", { name: "Preview" }));
    expect(onPreview).not.toHaveBeenCalled();
    expect(screen.getByLabelText(/Depth/)).toHaveAttribute("aria-invalid", "true");
  });

  it("places server details on inputs by path and related_paths (D037)", () => {
    const { byField, other } = placeDetails(
      [
        { path: "entities[x].x_lines", code: "OUT_OF_SUPPORTED_RANGE", related_paths: ["args.width_m", "entities[f].width_m"] },
        { path: "args.depth_m", code: "WRONG_TYPE" },
        { path: "project_id", code: "DANGLING_REFERENCE" },
      ],
      { width: "args.width_m", depth: "args.depth_m" },
    );
    expect(byField.width?.map((d) => d.code)).toEqual(["OUT_OF_SUPPORTED_RANGE"]);
    expect(byField.depth?.map((d) => d.code)).toEqual(["WRONG_TYPE"]);
    expect(other.map((d) => d.code)).toEqual(["DANGLING_REFERENCE"]);
  });

  it("renders the server's impact preview in display units", () => {
    render(<ImpactDialog state={{ step: "review", command: fixture.width_command, preview: fixture.width_preview }} units="imperial" snapshot={fixture.snapshot} onConfirm={() => {}} onCancel={() => {}} />);
    const changes = screen.getByTestId("impact-changes");
    expect(changes).toHaveTextContent(`width_m36' 0"40' 0"`);
    const members = fixture.width_preview.members;
    expect(screen.getByTestId("impact-members")).toHaveTextContent(`${members.added.length} added, ${members.removed.length} removed, ${members.updated.length} updated`);
    expect(screen.getByRole("button", { name: "Confirm" })).toBeEnabled();
  });

  it("offers no confirmation for a no-op", () => {
    const noop = { ...fixture.width_preview, is_noop: true, revision_id: null, changes: [], confirmation_required: false };
    render(<ImpactDialog state={{ step: "review", command: fixture.width_command, preview: noop }} units="imperial" onConfirm={() => {}} onCancel={() => {}} />);
    expect(screen.getByRole("heading", { name: "No changes" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Confirm" })).toBeNull();
  });
});

describe("price-book form (UI-001 §5.1)", () => {
  const meta = { source: " Quote ", geography: "VT", as_of: "2026-11-01" };
  const rows = initialRows(estimateNone.payload!, null, "imperial", catalog);
  const firstTimber = rows.findIndex((r) => r.unit === "m");
  const pmt = rows.findIndex((r) => r.key === "connection.PEGGED_MORTISE_TENON");

  it("builds rows from the estimate's line items", () => {
    expect(rows.map((r) => r.key)).toEqual(estimateNone.payload!.line_items.map((li) => li.key));
    expect(rows.map((r) => r.unit)).toEqual(estimateNone.payload!.line_items.map((li) => li.quantity_unit));
    expect(rows[pmt]!.label).toBe("Pegged mortise and tenon. Representational only: no capacity, sizes, or fasteners.");
    expect(buildBook(meta, rows, "imperial")!.book).toEqual({ currency: "USD", as_of: "2026-11-01", source: "Quote", geography: "VT", rows: [] });
  });

  it("converts per-foot prices half-even and leaves blank rows out (partial)", () => {
    const edited = rows.map((r, i) => (i === firstTimber ? { ...r, text: "10.00", dirty: true } : r));
    expect(buildBook(meta, edited, "imperial")!.book.rows).toEqual([{ key: rows[firstTimber]!.key, unit: "m", unit_price_minor: 3281 }]);
    expect(buildBook(meta, edited, "metric")!.book.rows[0]!.unit_price_minor).toBe(1000);
  });

  it("takes per-piece prices for each rows, with no unit conversion (ART-002 §9)", () => {
    const edited = rows.map((r, i) => (i === pmt ? { ...r, text: "45.00", dirty: true } : r));
    for (const units of ["imperial", "metric"] as const) {
      expect(buildBook(meta, edited, units)!.book.rows).toEqual([{ key: "connection.PEGGED_MORTISE_TENON", unit: "each", unit_price_minor: 4500 }]);
    }
    const stored = { ...fixture.price_book, book: { ...fixture.price_book.book, rows: [{ key: "connection.PEGGED_MORTISE_TENON", unit: "each" as const, unit_price_minor: 4500 }] } };
    for (const units of ["imperial", "metric"] as const) {
      expect(initialRows(estimateNone.payload!, stored, units, catalog)[pmt]!.text).toBe("45.00");
    }
  });

  it("keeps untouched stored prices exactly and keeps unused rows with their unit", () => {
    const extra = [
      { key: "timber.RAFTER.4x8", unit: "m" as const, unit_price_minor: 999 },
      { key: "connection.STEEL_KNIFE_PLATE", unit: "each" as const, unit_price_minor: 12000 },
    ];
    const stored = { ...fixture.price_book, book: { ...fixture.price_book.book, rows: [...fixture.price_book.book.rows, ...extra] } };
    const loaded = initialRows(estimateNone.payload!, stored, "imperial", catalog);
    expect(loaded.filter((r) => r.unused).map((r) => [r.key, r.unit])).toEqual([["timber.RAFTER.4x8", "m"], ["connection.STEEL_KNIFE_PLATE", "each"]]);
    const book = buildBook(meta, loaded, "imperial")!.book;
    expect(book.rows.map((r) => [r.key, r.unit, r.unit_price_minor])).toEqual(
      [...stored.book.rows].sort((a, b) => loaded.findIndex((r) => r.key === a.key) - loaded.findIndex((r) => r.key === b.key)).map((r) => [r.key, r.unit, r.unit_price_minor]),
    );
  });

  it("rejects an invalid price", () => {
    const edited = rows.map((r, i) => (i === firstTimber ? { ...r, text: "1.234", dirty: true } : r));
    expect(buildBook(meta, edited, "imperial")).toBeNull();
  });
});

describe("Workspace with the real client over a fake server", () => {
  it("pairs both views for one revision and shows statuses and history", async () => {
    const { api, calls } = fakeApi();
    render(
      <AppContext.Provider value={{ api, units: "imperial", setUnits: () => {}, signOut: () => {} }}>
        <Workspace projectId={fixture.project.project_id} revisionId={null} />
      </AppContext.Provider>,
    );
    const views = await screen.findByTestId("views-paired");
    expect(views).toHaveAttribute("data-source-revision-id", fixture.project.head_revision_id);
    await waitFor(() => expect(screen.getByTestId("status-preliminary_estimate")).toHaveTextContent("UNAVAILABLE"));
    expect(screen.getByTestId("revision-kind")).toHaveTextContent("Head");
    expect(screen.getByTestId("status-plan2d")).toHaveTextContent("CURRENT");
    expect(screen.getByTestId("history")).toHaveTextContent("1. CreateReferenceProject");
    expect(views.querySelector(".mesh3d")).toHaveAttribute("data-member-count", "193");
    expect(calls.every((c) => !c.path.includes("token"))).toBe(true);
  });

  it("previews a width change through the API and shows the impact", async () => {
    const { api, calls } = fakeApi();
    render(
      <AppContext.Provider value={{ api, units: "imperial", setUnits: () => {}, signOut: () => {} }}>
        <Workspace projectId={fixture.project.project_id} revisionId={null} />
      </AppContext.Provider>,
    );
    const width = await screen.findByRole("textbox", { name: /Width/ });
    await waitFor(() => expect(width).toBeEnabled());
    await userEvent.clear(width);
    await userEvent.type(width, "40'");
    await userEvent.click(screen.getByRole("button", { name: "Preview" }));
    expect(await screen.findByTestId("impact-dialog")).toHaveTextContent("Review the impact");
    const preview = calls.find((c) => c.path.endsWith("/commands/preview"))!;
    expect((preview.body as { args: unknown }).args).toEqual({ width_m: 12.192, depth_m: 7.3152 });
  });
});
