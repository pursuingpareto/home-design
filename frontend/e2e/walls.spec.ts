/**
 * ART-003 §13 test 14 (D085; AC2b-10's price-book bullet): a per-square-foot price saves as an m2 row, prices
 * the assembly line, and reloads. Walls are not drawn until UI-004.
 */

import { expect, test, type Page } from "@playwright/test";

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
