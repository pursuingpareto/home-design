/**
 * UI-003 §13 test 9 in a real browser against a real API: markers and selection, the Frame tab, the
 * Connections tab, the dialog's impact, and the brace-fit pointer to the Frame tab. The preview counts
 * are those DEP-001 §8 measured on Reference House 001 v2.
 */

import { expect, test, type Page } from "@playwright/test";

import { TOKENS } from "../playwright.config";

async function newProject(page: Page) {
  await page.goto("/#/projects");
  await page.getByLabel("Development token").fill(TOKENS.a);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("button", { name: "Create Reference House 001" }).click();
  await expect(page.getByTestId("views-paired")).toBeVisible();
  await expect(page.getByTestId("schedule-connections")).toBeVisible();
}

const tab = (page: Page, name: string) => page.getByRole("tab", { name }).click();
const plane = (page: Page, name: string) => page.getByRole("group", { name: "Plan plane" }).getByRole("button", { name }).click();
const preview = (page: Page) => page.getByRole("tabpanel").getByRole("button", { name: "Preview" }).click();
const dialog = (page: Page) => page.getByTestId("impact-dialog");
const confirm = (page: Page) => dialog(page).getByRole("button", { name: "Confirm" }).click();
const revision = (page: Page, n: number) => expect(page.getByTestId("revision-label")).toContainText(`Revision ${n} `);
const ALL_FOUR = "Updates: 2D plan, 3D model, Timber schedule, Estimate.";

test("markers: Level 1 shows 162 connections in 91 glyphs, selection highlights, and the switch hides them", async ({ page }) => {
  await newProject(page);
  await plane(page, "Level 1");
  const plan = page.locator(".plan2d");
  await expect(plan.locator(".connection-glyph")).toHaveCount(91);
  await expect(plan).toHaveAttribute("data-connection-count", "162");
  const mesh = page.locator(".mesh3d");
  await expect(mesh).toHaveAttribute("data-connection-count", "312");
  await expect(mesh).toHaveAttribute("data-glyph-count", "193");

  const row = page.getByTestId("schedule-connections").locator("tbody tr", { hasText: "Joist–beam" }).first();
  const id = await row.getAttribute("data-connection-id");
  await row.locator("td").first().click();
  await expect(row).toHaveAttribute("aria-selected", "true");
  const glyph = plan.locator(".connection-glyph.selected");
  await expect(glyph).toHaveCount(1);
  expect((await glyph.getAttribute("data-connection-ids"))!.split(" ")).toContain(id);
  await expect(plan.locator("line.related")).toHaveCount(2); // the beam and the joist

  const toggle = page.getByRole("switch", { name: "Connections" });
  await toggle.uncheck();
  await expect(plan.locator(".connection-glyph")).toHaveCount(0);
  await expect(mesh).toHaveAttribute("data-glyph-count", "0");
  await page.reload();
  await expect(page.getByRole("switch", { name: "Connections" })).not.toBeChecked(); // remembered per browser
  await page.getByRole("switch", { name: "Connections" }).check();
  await expect(page.locator(".plan2d .connection-glyph")).toHaveCount(12);
});

test("frame: eave braces off changes all four artifacts", async ({ page }) => {
  await newProject(page);
  await tab(page, "Frame");
  await page.getByRole("checkbox", { name: "Knee braces at the eave" }).uncheck();
  await preview(page);
  await expect(dialog(page).getByTestId("impact-members")).toContainText("Timber members: 0 added, 34 removed");
  await expect(dialog(page).getByTestId("impact-connections")).toContainText("Connections: 0 added, 68 removed");
  await expect(dialog(page).getByTestId("impact-artifacts")).toHaveText(ALL_FOUR);
  await confirm(page);
  await revision(page, 2);
  const mesh = page.locator(".mesh3d");
  await expect(mesh).toHaveAttribute("data-member-count", "159");
  await expect(mesh).toHaveAttribute("data-connection-count", "244");
  await plane(page, "Eave");
  await expect(page.locator('.plan2d line[data-array="braces"]')).toHaveCount(0);
  await expect(page.getByTestId("schedule-connection-aggregates").locator('tr[data-junction-class="brace"]')).toContainText("68");
});

test("frame: a joist spacing of 0.65 m changes only the plan and the 3D model", async ({ page }) => {
  await newProject(page);
  await tab(page, "Frame");
  await page.getByRole("textbox", { name: "Joist spacing" }).fill("0.65 m");
  await preview(page);
  await expect(dialog(page).getByTestId("impact-members")).toHaveText("Timber members: 0 added, 0 removed, 30 updated.");
  await expect(dialog(page).getByTestId("impact-connections")).toHaveText("Connections: 0 added, 0 removed, 60 updated.");
  await expect(dialog(page).getByTestId("impact-artifacts")).toHaveText("Updates: 2D plan, 3D model. Unchanged: Timber schedule, Estimate.");
  await expect(dialog(page).getByTestId("impact-changes")).toContainText(`parameters.joist_spacing_m2' 0"2' 1 9/16"`);
});

test("connection type: joist-beam to Joist hanger updates the schedule, the estimate, and the price book", async ({ page }) => {
  await newProject(page);
  await page.getByRole("button", { name: "Set unit prices" }).click();
  const prices = page.getByTestId("price-book-form");
  await prices.getByLabel("Source").fill("E2E quote");
  await prices.getByLabel("Geography").fill("VT");
  for (const [label, price] of [
    ["Beam 8x12", "14.40"], ["Post 8x8", "9.60"], ["Sill 8x8", "9.60"], ["Floor joist 4x8", "3.66"], ["Principal rafter 8x10", "11.90"],
    ["Purlin 6x8", "7.16"], ["Knee brace 4x6", "2.74"], ["Pegged mortise and tenon", "45.00"], ["Bridle joint", "65.00"], ["Housed dovetail", "38.00"],
  ] as const) {
    await prices.getByLabel(label).fill(price);
  }
  await prices.getByRole("button", { name: "Save prices" }).click();
  await expect(page.getByTestId("estimate-coverage")).toContainText("complete");
  await prices.getByRole("button", { name: "Close" }).click();

  await tab(page, "Connections");
  await page.getByRole("combobox", { name: "Joist–beam" }).selectOption("JOIST_HANGER");
  await expect(page.getByTestId("connection-type-descriptions")).toContainText("Joist hanger. Representational only");
  await page.getByRole("button", { name: "Preview Joist–beam change" }).click();
  await expect(dialog(page).getByTestId("impact-members")).toHaveText("Timber members: 0 added, 0 removed, 0 updated.");
  await expect(dialog(page).getByTestId("impact-connections")).toHaveText("Connections: 0 added, 0 removed, 60 updated.");
  await expect(dialog(page).getByTestId("impact-artifacts")).toHaveText(ALL_FOUR);
  await expect(dialog(page).getByTestId("impact-changes")).toContainText("Housed dovetailJoist hanger");
  await confirm(page);
  await revision(page, 2); // the price book is not a revision
  const counts = page.getByTestId("schedule-connection-aggregates").locator('tr[data-junction-class="joist-beam"]');
  await expect(counts).toHaveText("Joist–beamJoist hanger60");
  await expect(page.getByTestId("schedule-connection-types")).toContainText("Joist hanger. Representational only: no capacity, sizes, or fasteners.");
  const line = page.getByTestId("estimate").locator('tr[data-key="connection.JOIST_HANGER"]');
  await expect(line).toContainText("60 each");
  await expect(line).toContainText("Not priced");
  await expect(page.getByTestId("estimate-coverage")).toContainText("partial");
  await page.getByTestId("connection-pricing-note").getByRole("button", { name: "Set unit prices" }).click();
  await expect(page.getByTestId("price-book-form").locator('tr[data-key="connection.HOUSED_DOVETAIL"]')).toContainText("unused");
});

test("connection type: a class with no connections changes nothing derived, and can still be confirmed", async ({ page }) => {
  await newProject(page);
  await tab(page, "Frame");
  await page.getByRole("checkbox", { name: "Knee braces on Level 1" }).uncheck();
  await page.getByRole("checkbox", { name: "Knee braces at the eave" }).uncheck();
  await preview(page);
  await confirm(page);
  await revision(page, 2);
  await tab(page, "Connections");
  await expect(page.getByTestId("connection-count-brace")).toContainText("None in the current frame");
  await page.getByRole("combobox", { name: "Knee brace ends" }).selectOption("STEEL_KNIFE_PLATE");
  await page.getByRole("button", { name: "Preview Knee brace ends change" }).click();
  await expect(dialog(page).getByTestId("impact-artifacts")).toHaveText("No derived views or reports change.");
  await expect(dialog(page).getByTestId("impact-connections")).toHaveText("Connections: 0 added, 0 removed, 0 updated.");
  await expect(dialog(page).getByRole("button", { name: "Confirm" })).toBeEnabled();
  await confirm(page);
  await revision(page, 3);
});

test("a grid bay too short for the braces points to the Frame tab", async ({ page }) => {
  await newProject(page);
  await tab(page, "Grid");
  await page.getByTestId("grid-x").getByRole("textbox", { name: "x1" }).fill(`4'`);
  await preview(page);
  const error = page.getByRole("dialog");
  await expect(error.getByRole("heading", { name: "The change was not applied" })).toBeVisible();
  await expect(error.getByTestId("dialog-details")).toContainText(".parameters.knee_brace_leg_m");
  // The bay is a fraction of the footprint, so the Footprint tab is pointed to as well (UI-002 §7).
  await expect(error.getByTestId("tab-pointer").filter({ hasText: "Frame" })).toHaveText("Also see the Frame tab: its values are part of this problem.");
  await expect(error.getByTestId("tab-pointer").filter({ hasText: "Sections" })).toHaveCount(0);
  await error.getByRole("button", { name: "Close" }).click();
  await expect(page.getByTestId("history").locator("li")).toHaveCount(1);
});

// TEST-002 §8.2 and D063: time budgets in the e2e setup (the Vite dev server, unbundled; not a production
// build). Each is the median of 5 runs with no retries, printed with its runs. They catch order-of-magnitude
// regressions, not user-facing targets; a CI value over half its ceiling is reported, not raised (D063).
const RUNS = 5;
const median = (values: number[]) => [...values].sort((a, b) => a - b)[Math.floor(values.length / 2)] ?? Number.NaN;
function report(what: string, ceilingMs: number, times: number[]) {
  const m = median(times);
  console.log(`[TEST-002 budget] ${what}: median ${m} ms of ${RUNS} (${times.join(", ")} ms), ${Math.round((100 * m) / ceilingMs)}% of the ${ceilingMs / 1000} s ceiling`);
  expect(m, `${what}: median ${m} ms is over the ${ceilingMs} ms budget (TEST-002 §8.2)`).toBeLessThanOrEqual(ceilingMs);
}

test("budgets: the created house shows its views and schedule within 10 s, and a preview's dialog within 3 s", async ({ page }) => {
  test.setTimeout(180_000);
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
    await expect(page.getByTestId("views-paired")).toBeVisible();
    await expect(page.locator(".mesh3d")).toHaveAttribute("data-glyph-count", "193");
    await expect(page.getByTestId("schedule-connections")).toBeVisible();
    created.push(Date.now() - start);
  }

  const previewed: number[] = [];
  await tab(page, "Frame");
  for (let i = 0; i < RUNS; i++) {
    await page.getByRole("textbox", { name: "Joist spacing" }).fill(`${0.62 + i / 100} m`);
    const start = Date.now();
    await preview(page);
    await expect(dialog(page).getByTestId("impact-artifacts")).toBeVisible();
    previewed.push(Date.now() - start);
    await dialog(page).getByRole("button", { name: "Cancel" }).click();
    await expect(dialog(page)).toHaveCount(0);
  }

  report("browser: Create pressed until 2D, 3D (193 glyphs), and the schedule are shown", 10_000, created);
  report("browser: Preview pressed until the confirmation dialog shows", 3_000, previewed);
  await expect(page.getByTestId("history").locator("li")).toHaveCount(1); // nothing was committed
});
