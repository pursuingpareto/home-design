/** UI-002 editors in a real browser against a real API (UI-002 §8, item 3). */

import { expect, test, type Page } from "@playwright/test";

import { TOKENS } from "../playwright.config";

async function newProject(page: Page) {
  await page.goto("/#/projects");
  await page.getByLabel("Development token").fill(TOKENS.a);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("button", { name: "Create Reference House 001" }).click();
  await expect(page.getByTestId("views-paired")).toBeVisible();
}

const tab = (page: Page, name: string) => page.getByRole("tab", { name }).click();
const confirm = (page: Page) => page.getByTestId("impact-dialog").getByRole("button", { name: "Confirm" }).click();
const revision = (page: Page, n: number) => expect(page.getByTestId("revision-label")).toContainText(`Revision ${n} `);

test("stories: raising Level 1 lifts the eave and lengthens the posts", async ({ page }) => {
  await newProject(page);
  await tab(page, "Stories");
  await page.getByRole("textbox", { name: "Level 1 story height" }).fill("10'");
  await page.getByRole("button", { name: "Preview" }).click();
  await expect(page.getByTestId("impact-dialog")).toContainText("story_height_m");
  await confirm(page);
  await revision(page, 2);
  await expect(page.locator(".mesh3d")).toHaveAttribute("data-eave-z-m", "6.096");
  await expect(page.getByTestId("schedule-aggregates")).toContainText(`Post8x824240' 0"`); // 228' + 12 × 1'
});

test("roof: a pitch change is previewed (D057), and moves rafters and purlins", async ({ page }) => {
  await newProject(page);
  await tab(page, "Roof");
  await page.getByRole("textbox", { name: "Pitch" }).fill("10/12");
  await page.getByRole("button", { name: "Preview" }).click();
  await expect(page.getByTestId("impact-dialog")).toContainText("pitch_rad");
  await expect(page.getByTestId("impact-members")).toContainText("20 updated"); // 8 principal rafters, 12 purlins
  await confirm(page);
  await revision(page, 2);
  await expect(page.getByRole("textbox", { name: "Pitch" })).toHaveValue("10/12");
});

test("sections: a routine change applies without preview, and Undo goes through the preview", async ({ page }) => {
  await newProject(page);
  await tab(page, "Sections");
  await page.getByRole("textbox", { name: "Label" }).fill("10x10");
  await page.getByRole("textbox", { name: "Actual width" }).fill(`9 1/2"`);
  await page.getByRole("textbox", { name: "Actual depth" }).fill(`9 1/2"`);
  await page.getByRole("button", { name: "Add section" }).click();
  await expect(page.getByTestId("applied-notice")).toContainText("Saved as revision 2. Added section 10x10");
  await expect(page.getByTestId("impact-dialog")).toHaveCount(0);
  await revision(page, 2);

  await page.getByTestId("applied-notice").getByRole("button", { name: "Undo" }).click();
  await expect(page.getByTestId("impact-dialog")).toContainText("Review the impact");
  await confirm(page);
  await revision(page, 3);
  await expect(page.getByTestId("section-catalog")).not.toContainText("10x10");
  await expect(page.getByTestId("history")).toContainText("UndoToRevision");
});

test("grid: dividing X into 4 bays keeps the original interior line IDs", async ({ page }) => {
  await newProject(page);
  await expect(page.getByTestId("schedule-members")).toContainText("Members (193)");
  await tab(page, "Grid");
  const x = page.getByTestId("grid-x");
  await x.getByRole("spinbutton").fill("4");
  await x.getByRole("button", { name: "Divide" }).click();
  await page.getByRole("button", { name: "Preview" }).click();
  await expect(page.getByTestId("impact-members")).toContainText("added");
  await confirm(page);
  await revision(page, 2);
  await expect(x.getByRole("textbox", { name: "x1" })).toHaveValue(`9' 0"`);
  await expect(x.getByRole("textbox", { name: "x2" })).toHaveValue(`18' 0"`);
  await expect(x.getByRole("textbox", { name: "x4" })).toHaveValue(`27' 0"`); // the new line, numbered by the server
  await expect(page.getByTestId("schedule-members")).not.toContainText("Members (193)");
});

test("AC-06: a width the grid cannot support points to the Grid tab, and works after adding a bay", async ({ page }) => {
  await newProject(page);
  await page.getByRole("textbox", { name: /Width/ }).fill("76'");
  await page.getByRole("button", { name: "Preview" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toContainText("UNSUPPORTED_CONFIGURATION");
  await expect(dialog.getByTestId("tab-pointer")).toHaveText("Also see the Grid tab: its values are part of this problem.");
  await expect(page.getByRole("textbox", { name: /Width/ })).toHaveAttribute("aria-invalid", "true");
  await dialog.getByRole("button", { name: "Close" }).click();

  await tab(page, "Grid");
  await page.getByTestId("grid-x").getByRole("spinbutton").fill("4");
  await page.getByTestId("grid-x").getByRole("button", { name: "Divide" }).click();
  await page.getByRole("button", { name: "Preview" }).click();
  await confirm(page);
  await revision(page, 2);

  await tab(page, "Footprint");
  await expect(page.getByRole("textbox", { name: /Width/ })).toHaveValue("76'"); // typed value kept
  await page.getByRole("button", { name: "Preview" }).click();
  await confirm(page);
  await revision(page, 3);
  await expect(page.getByTestId("dim-footprint-width")).toHaveText(`Width: 76' 0"`);
});

// The straw bale walls' six lines (ART-003 §7.1): layers per square foot, bucks per foot (D085).
const WALL_PRICES = [
  ["Straw (straw-bale, bales)", "2.04"], ["Clay plaster (straw-bale, clay-plaster)", "3.25"], ["Lime plaster (straw-bale, lime-plaster)", "3.90"],
  ["Buck head 1.5x18", "5.79"], ["Buck jamb 1.5x18", "5.79"], ["Buck sill 1.5x18", "5.79"],
] as const;

test("sections: add, reject a duplicate, apply to beams, and see the price row become unused", async ({ page }) => {
  await newProject(page);
  await page.getByRole("button", { name: "Set unit prices" }).click();
  const prices = page.getByTestId("price-book-form");
  await prices.getByLabel("Source").fill("E2E quote");
  await prices.getByLabel("Geography").fill("VT");
  await prices.getByLabel("Beam 8x12").fill("14.40");
  await prices.getByLabel("Post 8x8").fill("9.60");
  await prices.getByLabel("Sill 8x8").fill("9.60");
  await prices.getByLabel("Floor joist 4x8").fill("3.66");
  await prices.getByLabel("Principal rafter 8x10").fill("11.90");
  await prices.getByLabel("Purlin 6x8").fill("7.16");
  await prices.getByLabel("Knee brace 4x6").fill("2.74");
  await prices.getByLabel("Pegged mortise and tenon").fill("45.00"); // per piece (ART-002 §9)
  await prices.getByLabel("Bridle joint").fill("65.00");
  await prices.getByLabel("Housed dovetail").fill("38.00");
  for (const [label, price] of WALL_PRICES) await prices.getByLabel(label).fill(price);
  await prices.getByRole("button", { name: "Save prices" }).click();
  await expect(page.getByTestId("estimate-coverage")).toContainText("complete");
  await prices.getByRole("button", { name: "Close" }).click();

  await tab(page, "Sections");
  const addSection = async () => {
    await page.getByRole("textbox", { name: "Label" }).fill("10x12");
    await page.getByRole("textbox", { name: "Actual width" }).fill(`9 1/2"`);
    await page.getByRole("textbox", { name: "Actual depth" }).fill(`11 1/2"`);
    await page.getByRole("button", { name: "Add section" }).click();
  };
  await addSection();
  await expect(page.getByTestId("applied-notice")).toContainText("Added section 10x12");
  await revision(page, 2);
  await expect(page.getByTestId("section-catalog")).toContainText("10x12");

  await addSection();
  await expect(page.getByRole("dialog")).toContainText("DUPLICATE_SECTION_LABEL");
  await page.getByRole("dialog").getByRole("button", { name: "Close" }).click();
  await expect(page.getByRole("textbox", { name: "Label" })).toHaveAttribute("aria-invalid", "true");

  await page.getByRole("combobox", { name: "Beam" }).selectOption({ label: "10x12" });
  await page.getByRole("button", { name: "Preview Beam change" }).click();
  await confirm(page);
  await revision(page, 3);
  await expect(page.getByTestId("schedule-aggregates")).toContainText("Beam10x1234");
  await expect(page.getByTestId("estimate-coverage")).toContainText("partial");
  await page.getByTestId("pricing-note").getByRole("button", { name: "Set unit prices" }).click();
  await expect(page.getByTestId("price-book-form").locator('tr[data-key="timber.BEAM.8x12"]')).toContainText("unused");
});

test("submitting a consequential tab without edits previews as a no-op", async ({ page }) => {
  await newProject(page);
  for (const name of ["Footprint", "Stories", "Roof", "Grid", "Frame"]) {
    await tab(page, name);
    await page.getByRole("tabpanel").getByRole("button", { name: "Preview" }).click();
    await expect(page.getByRole("heading", { name: "No changes" })).toBeVisible();
    await page.getByRole("dialog").getByRole("button", { name: "Close" }).click();
  }
  // Connections rows preview only a changed type (UI-003 §7.2), so an untouched row cannot be submitted.
  await tab(page, "Connections");
  const previews = page.getByTestId("connection-types").getByRole("button", { name: /^Preview / });
  await expect(previews).toHaveCount(7);
  for (const button of await previews.all()) await expect(button).toBeDisabled();
  await expect(page.getByTestId("history").locator("li")).toHaveCount(1);
});
