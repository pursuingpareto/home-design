/**
 * ART-003 §13 test 14 (D085; AC2b-10's price-book bullet): a per-square-foot price saves as an m2 row, prices
 * the assembly line, and reloads.
 *
 * UI-004 §16 test 9 (AC2b-04, AC2b-07, AC2b-10) in a real browser against a real API: walls, openings, and
 * wall framing in both views with the two switches, the assembly switch, opening edits applied with Undo,
 * fit rejections, and the openings a grid edit removes. The counts were measured through the service while
 * drafting (UI-004 §8.2, §9). The timings at the end are reported, not gated (UI-004 §13; D063).
 */

import { expect, test, type Locator, type Page } from "@playwright/test";

import { TOKENS } from "../playwright.config";

async function newProject(page: Page) {
  await page.goto("/#/projects");
  await page.getByLabel("Development token").fill(TOKENS.a);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("button", { name: "Create Reference House 001" }).click();
  await expect(page.getByTestId("views-paired")).toBeVisible();
}

test("assembly line: a per-square-foot price is stored per square meter, prices the line, and reloads", async ({ page }) => {
  await newProject(page);
  await expect(page.getByTestId("status-assembly_schedule")).toHaveText("Assembly schedule: CURRENT");
  const bales = page.getByTestId("estimate").locator('tr[data-key="assembly.straw-bale.bales"]');
  await page.getByRole("button", { name: "Set unit prices" }).click();
  const form = page.getByTestId("price-book-form");
  await form.getByLabel("Source").fill("E2E quote");
  await form.getByLabel("Geography").fill("VT");
  await expect(form.locator('tr[data-key="assembly.straw-bale.bales"]')).toContainText("per square foot");
  await form.getByLabel("Straw (straw-bale, bales)").fill("2.04");
  // 204 c/sf ÷ 0.09290304 = 2195.83… → 2196 c/m², half-even
  await expect(form.getByTestId("stored-assembly.straw-bale.bales")).toContainText("$21.96/m²");
  await form.getByRole("button", { name: "Save prices" }).click();
  await expect(form).toContainText("Saved as version 1.");
  await expect(page.getByTestId("estimate-coverage")).toContainText("partial");
  await expect(bales).toContainText("Straw (straw-bale, bales)");
  await expect(bales).toContainText(/1,978\.\d sf/);
  await expect(bales).toContainText("$21.96/m²");
  await expect(bales).toContainText("$4,036.42"); // 2196 c × 183.80769690000002 m², half-even
  await expect(page.getByTestId("estimate").locator('tr[data-key="wallframing.BUCK_JAMB.1.5x18"]')).toContainText("40 pcs");

  await page.reload();
  await expect(bales).toContainText("$21.96/m²");
  await page.getByRole("button", { name: "Set unit prices" }).click();
  await expect(page.getByTestId("price-book-form").getByLabel("Straw (straw-bale, bales)")).toHaveValue("2.04"); // reloaded from the stored book
});

const tab = (page: Page, name: string) => page.getByRole("tab", { name }).click();
const plane = (page: Page, name: string) => page.getByRole("group", { name: "Plan plane" }).getByRole("button", { name }).click();
const preview = (page: Page) => page.getByRole("tabpanel").getByRole("button", { name: "Preview" }).click();
const dialog = (page: Page) => page.getByTestId("impact-dialog");
const confirm = (page: Page) => dialog(page).getByRole("button", { name: "Confirm" }).click();
const revision = (page: Page, n: number) => expect(page.getByTestId("revision-label")).toContainText(`Revision ${n} `);
const walls = (page: Page) => page.locator("#panel-walls");
const field = (page: Page, name: string) => walls(page).getByRole("textbox", { name, exact: true });
const SW_WINDOW = `Window 5' 0" × 4' 0", south wall, Level 0, x0–x1`;
// The straw bale walls' six lines (ART-003 §7.1): layers per square foot, bucks per foot (D085).
const WALL_PRICES = [
  ["Straw (straw-bale, bales)", "2.04"], ["Clay plaster (straw-bale, clay-plaster)", "3.25"], ["Lime plaster (straw-bale, lime-plaster)", "3.90"],
  ["Buck head 1.5x18", "5.79"], ["Buck jamb 1.5x18", "5.79"], ["Buck sill 1.5x18", "5.79"],
] as const;

async function shown(page: Page) {
  await expect(page.getByTestId("views-paired")).toBeVisible();
  await expect(page.getByTestId("schedule-members")).toBeVisible();
  await expect(page.getByTestId("assembly-pieces")).toBeVisible();
}

/** The width of an opening's gap, from its glazing line (plan meters). */
async function gapWidth(mark: Locator): Promise<number> {
  const line = mark.locator(".glazing");
  const [x1, y1, x2, y2] = await Promise.all(["x1", "y1", "x2", "y2"].map(async (a) => Number(await line.getAttribute(a))));
  return Math.hypot(x2! - x1!, y2! - y1!);
}

test.describe("9. UI-004 end to end", () => {
  test("views and switches: 10 walls on Level 0, 20 walls and 79 pieces in 3D; the switches hide them and are remembered", async ({ page }) => {
    await newProject(page);
    await shown(page);
    const plan = page.locator(".plan2d");
    const mesh = page.locator(".mesh3d");
    await expect(plan).toHaveAttribute("data-wall-count", "10");
    await expect(plan.locator(".wall-band")).toHaveCount(10);
    await expect(plan.locator(".opening-mark")).toHaveCount(10);
    await expect(plan).toHaveAttribute("data-framing-mark-count", "30");
    await expect(mesh).toHaveAttribute("data-wall-count", "20");
    await expect(mesh).toHaveAttribute("data-framing-count", "79");
    await expect(mesh).toHaveAttribute("data-wall-solid-count", "60");
    await expect(mesh).toHaveAttribute("data-framing-box-count", "79");

    await page.getByRole("switch", { name: "Wall layers" }).uncheck();
    await expect(plan.locator(".wall-band, .opening-mark")).toHaveCount(0);
    await expect(mesh).toHaveAttribute("data-wall-solid-count", "0");
    await expect(plan.locator(".framing-mark")).toHaveCount(30);
    await page.getByRole("switch", { name: "Wall framing" }).uncheck();
    await expect(plan.locator(".framing-mark")).toHaveCount(0);
    await expect(mesh).toHaveAttribute("data-framing-box-count", "0");
    await expect(plan.locator('rect[data-role="POST"]').first()).toBeVisible(); // the timber frame stays

    await page.reload();
    await shown(page);
    await expect(page.getByRole("switch", { name: "Wall layers" })).not.toBeChecked();
    await expect(page.getByRole("switch", { name: "Wall framing" })).not.toBeChecked();
    await expect(page.locator(".plan2d .wall-band")).toHaveCount(0);
    await expect(page.locator(".mesh3d")).toHaveAttribute("data-framing-box-count", "0");
  });

  test("switch the assembly: Stud infill previews its impact, regenerates 246 pieces, and leaves the frame unchanged", async ({ page }) => {
    await newProject(page);
    await shown(page);
    await page.getByRole("button", { name: "Set unit prices" }).click();
    const prices = page.getByTestId("price-book-form");
    await prices.getByLabel("Source").fill("E2E quote");
    await prices.getByLabel("Geography").fill("VT");
    for (const [label, price] of WALL_PRICES) await prices.getByLabel(label).fill(price);
    await prices.getByRole("button", { name: "Save prices" }).click();
    await expect(prices).toContainText("Saved as version 1.");
    await prices.getByRole("button", { name: "Close" }).click();

    await tab(page, "Walls");
    await walls(page).getByLabel("Assembly for every wall").selectOption({ label: "Stud infill" });
    await expect(page.getByTestId("wall-framing-parameters")).toContainText(`2x6 studs at 2' 0" on center`);
    await preview(page);
    await expect(dialog(page).getByTestId("impact-members")).toHaveText("Timber members: 0 added, 0 removed, 0 updated.");
    await expect(dialog(page).getByTestId("impact-connections")).toHaveText("Connections: 0 added, 0 removed, 0 updated.");
    await expect(dialog(page).getByTestId("impact-walls")).toHaveText("Walls: 0 added, 0 removed, 20 updated.");
    await expect(dialog(page).getByTestId("impact-wall-framing")).toHaveText("Wall framing: 246 added, 79 removed, 0 updated.");
    await expect(dialog(page).getByTestId("impact-artifacts")).toHaveText("Updates: 2D plan, 3D model, Assembly schedule, Estimate. Unchanged: Timber schedule.");
    await expect(dialog(page).getByTestId("impact-changes")).toContainText("Straw baleStud infill");
    await confirm(page);
    await revision(page, 2);

    await expect(page.locator(".mesh3d")).toHaveAttribute("data-framing-box-count", "246");
    await expect(page.locator(".mesh3d")).toHaveAttribute("data-wall-solid-count", "80");
    await expect(page.getByTestId("assembly-definition")).toContainText("Stud infill");
    await expect(page.getByTestId("assembly-framing-aggregates").locator('tr[data-piece-kind="STUD"]')).toContainText("76");
    const studLine = page.getByTestId("estimate").locator('tr[data-key^="assembly.stud-infill."]').first();
    await expect(studLine).toContainText("Not priced");
    await expect(page.getByTestId("estimate").locator('tr[data-key^="wallframing.STUD."]')).toContainText("Not priced");
    await expect(page.getByTestId("schedule-members")).toContainText("Members (193)");
    await expect(page.getByTestId("schedule-connections")).toContainText("Connections (312)");
    await page.getByTestId("wall-pricing-note").getByRole("button", { name: "Set unit prices" }).click();
    await expect(page.getByTestId("price-book-form").locator('tr[data-key="assembly.straw-bale.bales"]')).toContainText("unused");
  });

  test("change an opening: a pick makes it current, Apply needs no dialog, the plan and schedule follow, and Undo restores it", async ({ page }) => {
    await newProject(page);
    await shown(page);
    const row = page.getByTestId("assembly-openings").locator("tr", { hasText: SW_WINDOW });
    const id = (await row.getAttribute("data-opening-id"))!;
    const mark = page.locator(`.plan2d .opening-mark[data-opening-id="${id}"]`);
    expect(await gapWidth(mark)).toBeCloseTo(1.524, 9);
    // The buck head and sill share a mark on the reference line, across the opening; pick the opening beside it.
    await mark.locator("polygon").click({ position: { x: 4, y: 2 } });
    await expect(row).toHaveAttribute("aria-selected", "true");
    await expect(page.locator(".plan2d .framing-mark.related")).toHaveCount(3); // 4 bucks; the head and sill share a mark
    await tab(page, "Walls");
    await expect(page.getByTestId("opening-form")).toHaveAttribute("data-opening-id", id);
    await field(page, "Width").fill(`6'`);
    await walls(page).getByRole("button", { name: "Apply" }).click();
    await expect(page.getByTestId("applied-notice")).toContainText("Saved as revision 2.");
    await expect(dialog(page)).toHaveCount(0);
    const widened = page.getByTestId("assembly-openings").locator(`tr[data-opening-id="${id}"]`);
    await expect(widened).toContainText(`6' 0" × 4' 0"`);
    expect(await gapWidth(page.locator(`.plan2d .opening-mark[data-opening-id="${id}"]`))).toBeCloseTo(1.8288, 9);

    await page.getByTestId("applied-notice").getByRole("button", { name: "Undo" }).click();
    await expect(dialog(page).getByTestId("impact-changes")).toContainText("width_m");
    await confirm(page);
    await revision(page, 3);
    await expect(page.getByTestId("assembly-openings").locator(`tr[data-opening-id="${id}"]`)).toContainText(`5' 0" × 4' 0"`);
  });

  test("add and remove: an overlap is rejected on the offset field; at 9' the window is added with 4 bucks, becomes current, and is removed with Undo", async ({ page }) => {
    await newProject(page);
    await shown(page);
    await tab(page, "Walls");
    await expect(page.getByTestId("opening-form")).toHaveAttribute("data-opening-id", "new");
    await walls(page).getByLabel("Wall", { exact: true }).selectOption({ label: "North wall, Level 1, x2–x3" });
    await field(page, "Width").fill(`2'`);
    await field(page, "Height").fill(`2'`);
    await field(page, "Sill height").fill(`3'`);
    await field(page, "Offset").fill(`6'`);
    await walls(page).getByRole("button", { name: "Add opening" }).click();
    const error = page.getByRole("dialog");
    await expect(error.getByTestId("dialog-details")).toContainText("OPENINGS_OVERLAP");
    await error.getByRole("button", { name: "Close" }).click();
    await expect(page.locator("#opening-offset-error")).toContainText("The opening's framing overlaps another opening's (OPENINGS_OVERLAP): with Window 3' 0\" × 4' 0\", north wall, Level 1, x2–x3");

    await field(page, "Offset").fill(`9'`);
    await walls(page).getByRole("button", { name: "Add opening" }).click();
    await expect(page.getByTestId("applied-notice")).toContainText("Saved as revision 2.");
    await expect(page.getByTestId("assembly-pieces")).toContainText("Wall framing pieces (83)");
    await expect(page.getByTestId("opening-form")).not.toHaveAttribute("data-opening-id", "new");
    await expect(page.getByTestId("opening-form")).toContainText(`Window 2' 0" × 2' 0", north wall, Level 1, x2–x3`);
    await expect(page.getByTestId("assembly-openings").locator("tbody tr")).toHaveCount(21);

    await walls(page).getByRole("button", { name: "Remove" }).click();
    await expect(page.getByTestId("applied-notice")).toContainText("Saved as revision 3.");
    await expect(page.getByTestId("applied-notice").getByRole("button", { name: "Undo" })).toBeVisible();
    await expect(page.getByTestId("assembly-openings").locator("tbody tr")).toHaveCount(20);
    await expect(page.getByTestId("assembly-pieces")).toContainText("Wall framing pieces (79)");
  });

  test("a fit rejection from a frame edit: with stories 10' and 8' and a 4' brace leg, Stud infill is rejected with GIRT_CROSSES_BRACE", async ({ page }) => {
    await newProject(page);
    await shown(page);
    await tab(page, "Stories");
    await page.getByRole("textbox", { name: "Level 1 story height" }).fill(`8'`);
    await preview(page);
    await confirm(page);
    await revision(page, 2);
    await tab(page, "Frame");
    await page.getByRole("textbox", { name: "Knee brace leg" }).fill(`4'`);
    await preview(page);
    await confirm(page);
    await revision(page, 3);

    await tab(page, "Walls");
    await walls(page).getByLabel("Assembly for every wall").selectOption({ label: "Stud infill" });
    await preview(page);
    const error = page.getByRole("dialog");
    await expect(error.getByTestId("dialog-details")).toContainText("GIRT_CROSSES_BRACE");
    await expect(error.getByTestId("tab-pointer").filter({ hasText: "Stories" })).toHaveText("Also see the Stories tab: its values are part of this problem.");
    await expect(error.getByTestId("tab-pointer").filter({ hasText: "Frame" })).toHaveText("Also see the Frame tab: its values are part of this problem.");
    await error.getByRole("button", { name: "Close" }).click();
    await expect(page.getByTestId("wall-assembly-error")).toContainText("A girt would cross a knee brace (GIRT_CROSSES_BRACE)");
    await expect(page.getByTestId("history").locator("li")).toHaveCount(3);
  });

  test("removed openings: re-identifying y1 lists the 8 east and west windows above Confirm, and each level then shows 6 openings", async ({ page }) => {
    await newProject(page);
    await shown(page);
    await tab(page, "Grid");
    await page.getByRole("button", { name: "Remove line y1" }).click();
    await page.getByRole("button", { name: "Add a line after y0 on Y" }).click();
    await preview(page);
    const block = dialog(page).getByTestId("removed-openings");
    await expect(block).toContainText("These 8 openings will be removed with their walls. Undo restores them.");
    await expect(block.getByRole("listitem")).toHaveCount(8);
    await expect(block.getByRole("listitem").filter({ hasText: /(east|west) wall, Level [01], y[01]–y[12]$/ })).toHaveCount(8);
    await expect(dialog(page).getByTestId("impact-walls")).toHaveText("Walls: 8 added, 8 removed, 0 updated.");
    await expect(dialog(page).getByTestId("impact-wall-framing")).toHaveText("Wall framing: 0 added, 32 removed, 0 updated.");
    await confirm(page);
    await revision(page, 2);
    await expect(page.locator(".plan2d")).toHaveAttribute("data-opening-count", "6");
    await plane(page, "Level 1");
    await expect(page.locator(".plan2d")).toHaveAttribute("data-opening-count", "6");
  });
});

// D090 (TEST-003 §8.3): UI-004's three timings, gated at D063's browser ceilings (10 s to render, 3 s to a dialog).
// Each is the median of 5 runs in the e2e setup (the Vite dev server, unbundled; not a production build), with no
// retries. They catch order-of-magnitude regressions; they are not user-facing targets. If a CI median passes half
// its ceiling, report it to the product owner rather than raising the ceiling (D063). D063's own case stays in
// connections.spec.ts.
const RUNS = 5;
const median = (values: number[]) => [...values].sort((a, b) => a - b)[Math.floor(values.length / 2)] ?? Number.NaN;
const budget = (what: string, times: number[], ceilingMs: number) => {
  const m = median(times);
  console.log(`[budget] ${what}: median ${m} ms of ${times.length} (${times.join(", ")} ms), ${Math.round((100 * m) / ceilingMs)}% of the ${ceilingMs / 1000} s ceiling`);
  expect(m, `${what}: median ${m} ms is over the ${ceilingMs} ms budget (D090)`).toBeLessThanOrEqual(ceilingMs);
};

test("budgets: the created house's views and schedules within 10 s, the SetWallAssembly dialog within 3 s, and the stud infill house's views within 10 s", async ({ page }) => {
  test.setTimeout(240_000);
  await page.goto("/#/projects");
  await page.getByLabel("Development token").fill(TOKENS.a);
  await page.getByRole("button", { name: "Sign in" }).click();

  const created: number[] = [];
  for (let i = 0; i < RUNS; i++) {
    await page.goto("/#/projects");
    const create = page.getByRole("button", { name: "Create Reference House 001" });
    await expect(create).toBeEnabled();
    const start = Date.now();
    await create.click();
    await shown(page);
    await expect(page.locator(".mesh3d")).toHaveAttribute("data-framing-box-count", "79");
    created.push(Date.now() - start);
  }

  const previewed: number[] = [];
  await tab(page, "Walls");
  await walls(page).getByLabel("Assembly for every wall").selectOption({ label: "Stud infill" });
  for (let i = 0; i < RUNS; i++) {
    const start = Date.now();
    await preview(page);
    await expect(dialog(page).getByTestId("impact-wall-framing")).toBeVisible();
    previewed.push(Date.now() - start);
    if (i < RUNS - 1) {
      await dialog(page).getByRole("button", { name: "Cancel" }).click();
      await expect(dialog(page)).toHaveCount(0);
    }
  }
  await confirm(page);
  await revision(page, 2);
  await expect(page.locator(".mesh3d")).toHaveAttribute("data-framing-box-count", "246");

  const studs: number[] = [];
  for (let i = 0; i < RUNS; i++) {
    const start = Date.now();
    await page.reload();
    await expect(page.getByTestId("views-paired")).toBeVisible();
    await expect(page.locator(".mesh3d")).toHaveAttribute("data-framing-box-count", "246");
    await expect(page.locator(".mesh3d canvas")).toBeVisible();
    studs.push(Date.now() - start);
  }

  budget("browser: Create pressed until 2D, 3D, the timber schedule, and the assembly schedule are shown", created, 10_000);
  budget("browser: Preview pressed until the SetWallAssembly dialog shows", previewed, 3_000);
  budget("browser: the stud infill house reloaded until both views show (largest mesh, 219,188 bytes)", studs, 10_000);
});
