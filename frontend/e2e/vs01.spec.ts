/** VS-01 in a real browser against a real API (UI-001 §9, item 5; AC-01, AC-02, AC-05–AC-08). */

import { expect, test, type Page } from "@playwright/test";

import { TOKENS } from "../playwright.config";

async function signIn(page: Page, token = TOKENS.a) {
  await page.goto("/#/projects");
  await page.getByLabel("Development token").fill(token);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Projects" })).toBeVisible();
}

async function createProject(page: Page): Promise<string> {
  await page.getByRole("button", { name: "Create Reference House 001" }).click();
  await expect(page.getByTestId("views-paired")).toBeVisible();
  return decodeURIComponent(/#\/projects\/([^/]+)/.exec(page.url())![1]!);
}

/** Record every moment the paired views show a revision other than the revision bar's (AC-07). */
async function watchConsistency(page: Page) {
  await page.evaluate(() => {
    const w = window as unknown as { __violations: string[] };
    w.__violations = [];
    const check = () => {
      const views = document.querySelector("[data-testid=views-paired]");
      const label = document.querySelector("[data-testid=revision-label] code")?.textContent ?? "";
      const source = views?.getAttribute("data-source-revision-id") ?? null;
      if (source && label && !source.startsWith(label)) w.__violations.push(`${label} vs ${source}`);
    };
    new MutationObserver(check).observe(document.body, { subtree: true, childList: true, attributes: true, characterData: true });
  });
}

async function violations(page: Page): Promise<string[]> {
  return page.evaluate(() => (window as unknown as { __violations: string[] }).__violations);
}

async function setWidth(page: Page, text: string) {
  const width = page.getByRole("textbox", { name: /Width/ });
  await expect(width).toBeEnabled();
  await width.fill(text);
  await page.getByRole("button", { name: "Preview" }).click();
}

test("the plan's roof tab shows the rafters and purlins (ART-002 §9)", async ({ page }) => {
  await signIn(page);
  await createProject(page);
  await page.getByRole("group", { name: "Plan plane" }).getByRole("button", { name: "Roof" }).click();
  const plan = page.locator(".plan2d svg");
  await expect(plan.locator('line[data-array="rafters"]')).toHaveCount(8);
  await expect(plan.locator('line[data-array="purlins"]')).toHaveCount(12);
});

test("AC-01: Reference House 001 shows the same dimensions in 2D and 3D", async ({ page }) => {
  await signIn(page);
  await createProject(page);
  await expect(page.getByTestId("dim-footprint-width")).toHaveText(`Width: 36' 0"`);
  await expect(page.getByTestId("dim-footprint-depth")).toHaveText(`Depth: 24' 0"`);
  const mesh = page.locator(".mesh3d");
  await expect(mesh).toHaveAttribute("data-member-count", "193");
  expect(Number(await mesh.getAttribute("data-footprint-width-m"))).toBeCloseTo(10.9728, 9);
  expect(Number(await mesh.getAttribute("data-footprint-depth-m"))).toBeCloseTo(7.3152, 9);
  await expect(page.locator(".mesh3d canvas")).toBeVisible();
  await expect(page.getByTestId("status-preliminary_estimate")).toHaveText("Estimate: UNAVAILABLE");
  await expect(page.getByTestId("estimate-unavailable")).toContainText("Costs not configured");
});

test("AC-02, AC-07: a width change updates both views and the schedule, never pairing old geometry", async ({ page }) => {
  await signIn(page);
  await createProject(page);
  const beamTotalBefore = await page.getByTestId("schedule-aggregates").textContent();
  await watchConsistency(page);
  await setWidth(page, "40'");
  const dialog = page.getByTestId("impact-dialog");
  await expect(dialog).toContainText("consequential");
  await expect(dialog.getByTestId("impact-changes")).toContainText(`40' 0"`);
  await dialog.getByRole("button", { name: "Confirm" }).click();
  await expect(page.getByTestId("revision-label")).toContainText("Revision 2");
  await expect(page.getByTestId("dim-footprint-width")).toHaveText(`Width: 40' 0"`);
  const mesh = page.locator(".mesh3d");
  await expect(mesh).toHaveAttribute("data-footprint-width-m", "12.192");
  const label = await page.getByTestId("revision-label").locator("code").textContent();
  expect(await page.getByTestId("views-paired").getAttribute("data-source-revision-id")).toMatch(new RegExp(`^${label}`));
  await expect(page.getByTestId("schedule-aggregates")).not.toHaveText(beamTotalBefore ?? "");
  expect(await violations(page)).toEqual([]);
});

test("AC-05: reloading and reopening restores the revision and dimensions", async ({ page }) => {
  await signIn(page);
  const projectId = await createProject(page);
  await setWidth(page, `38' 6"`);
  await page.getByTestId("impact-dialog").getByRole("button", { name: "Confirm" }).click();
  await expect(page.getByTestId("revision-label")).toContainText("Revision 2");
  const label = await page.getByTestId("revision-label").textContent();
  await page.reload();
  await page.goto("/#/projects");
  await page.getByRole("link", { name: new RegExp(projectId.slice(0, 8)) }).click();
  await expect(page.getByTestId("revision-label")).toHaveText(label!);
  await expect(page.getByTestId("dim-footprint-width")).toHaveText(`Width: 38' 6"`);
  await expect(page.getByRole("textbox", { name: /Width/ })).toHaveValue(`38' 6"`);
});

test("AC-06: an unsupported width is rejected with a field error and no new revision", async ({ page }) => {
  await signIn(page);
  await createProject(page);
  await setWidth(page, "100'");
  await expect(page.getByRole("heading", { name: "The change was not applied" })).toBeVisible();
  await expect(page.getByRole("dialog")).toContainText("UNSUPPORTED_CONFIGURATION");
  await expect(page.getByRole("textbox", { name: /Width/ })).toHaveAttribute("aria-invalid", "true");
  await page.getByRole("dialog").getByRole("button", { name: "Close" }).click();
  await expect(page.getByTestId("history").locator("li")).toHaveCount(1);
});

test("AC-08 and undo: history is labeled, preliminary, and undo goes through the preview", async ({ page }) => {
  await signIn(page);
  const projectId = await createProject(page);
  await setWidth(page, "40'");
  await page.getByTestId("impact-dialog").getByRole("button", { name: "Confirm" }).click();
  await expect(page.getByTestId("revision-label")).toContainText("Revision 2");

  await page.getByTestId("history").locator("li").first().getByRole("button", { name: "View" }).click();
  await expect(page).toHaveURL(new RegExp(`#/projects/${projectId}/revisions/`));
  await expect(page.getByTestId("revision-kind")).toContainText("Historical");
  await expect(page.getByTestId("preliminary-banner")).toContainText("Structural adequacy has not been assessed");
  await expect(page.getByTestId("dim-footprint-width")).toHaveText(`Width: 36' 0"`);
  await expect(page.getByRole("textbox", { name: /Width/ })).toHaveCount(0); // read-only

  await page.getByTestId("history").locator("li").first().getByRole("button", { name: "Undo to this revision" }).click();
  const dialog = page.getByTestId("impact-dialog");
  await expect(dialog).toContainText("Review the impact");
  await dialog.getByRole("button", { name: "Confirm" }).click();
  await expect(page.getByTestId("revision-label")).toContainText("Revision 3");
  await expect(page.getByTestId("revision-kind")).toHaveText("Head");
  await expect(page.getByTestId("dim-footprint-width")).toHaveText(`Width: 36' 0"`);
  await expect(page.getByTestId("history").locator("li")).toHaveCount(3);
  await expect(page.getByTestId("history")).toContainText("UndoToRevision");
});

test("a commit from another tab gives a conflict and a fresh preview", async ({ page, context }) => {
  await signIn(page);
  const projectId = await createProject(page);
  await setWidth(page, "40'");
  await expect(page.getByTestId("impact-dialog")).toBeVisible();

  const other = await context.newPage();
  await signIn(other);
  await other.goto(`/#/projects/${projectId}`);
  await setWidth(other, "38'");
  await other.getByTestId("impact-dialog").getByRole("button", { name: "Confirm" }).click();
  await expect(other.getByTestId("revision-label")).toContainText("Revision 2");

  await page.getByTestId("impact-dialog").getByRole("button", { name: "Confirm" }).click();
  await expect(page.getByRole("dialog")).toContainText("Someone else changed the project first");
  await page.getByRole("dialog").getByRole("button", { name: "Close" }).click();
  await expect(page.getByTestId("revision-label")).toContainText("Revision 2");
  await expect(page.getByTestId("dim-footprint-width")).toHaveText(`Width: 38' 0"`);
  await expect(page.getByRole("textbox", { name: /Width/ })).toHaveValue("40'"); // the user's input is kept
  await page.getByRole("button", { name: "Preview" }).click();
  await page.getByTestId("impact-dialog").getByRole("button", { name: "Confirm" }).click();
  await expect(page.getByTestId("revision-label")).toContainText("Revision 3");
  await expect(page.getByTestId("dim-footprint-width")).toHaveText(`Width: 40' 0"`);
});

test("price book: complete then partial coverage", async ({ page }) => {
  await signIn(page);
  await createProject(page);
  await page.getByRole("button", { name: "Set unit prices" }).click();
  const form = page.getByTestId("price-book-form");
  await form.getByLabel("Source").fill("E2E supplier quote");
  await form.getByLabel("Geography").fill("Chittenden County, VT");
  await form.getByLabel("Beam 8x12").fill("14.40");
  await form.getByLabel("Post 8x8").fill("9.60");
  await form.getByLabel("Sill 8x8").fill("9.60");
  await form.getByLabel("Floor joist 4x8").fill("3.66");
  await form.getByLabel("Principal rafter 8x10").fill("11.90");
  await form.getByLabel("Purlin 6x8").fill("7.16");
  await form.getByLabel("Knee brace 4x6").fill("2.74");
  await expect(form.getByTestId("stored-timber.BEAM.8x12")).toContainText("$47.24/m"); // 1440 c/ft × 1250/381 = 4724.41
  // Connection lines are priced per piece, with no unit conversion (ART-002 §9, AC2-08).
  await form.getByLabel("Pegged mortise and tenon").fill("45.00");
  await form.getByLabel("Bridle joint").fill("65.00");
  await form.getByLabel("Housed dovetail").fill("38.00");
  await expect(form.getByTestId("stored-connection.PEGGED_MORTISE_TENON")).toHaveText("$45.00 each");
  // VS-02b's wall lines (ART-003 §10, D085): layers per square foot, bucks per foot as timber is.
  await form.getByLabel("Straw (straw-bale, bales)").fill("2.04");
  await form.getByLabel("Clay plaster (straw-bale, clay-plaster)").fill("3.25");
  await form.getByLabel("Lime plaster (straw-bale, lime-plaster)").fill("3.90");
  for (const label of ["Buck head 1.5x18", "Buck jamb 1.5x18", "Buck sill 1.5x18"]) await form.getByLabel(label).fill("5.79");
  await form.getByRole("button", { name: "Save prices" }).click();
  await expect(form).toContainText("Saved as version 1.");
  await expect(page.getByTestId("status-preliminary_estimate")).toHaveText("Estimate: CURRENT");
  await expect(page.getByTestId("estimate-coverage")).toContainText("complete");
  await expect(page.getByTestId("estimate-total")).toContainText("Total: $");
  const pegged = page.getByTestId("estimate").locator('tr[data-key="connection.PEGGED_MORTISE_TENON"]');
  await expect(pegged).toContainText("248 each");
  await expect(pegged).toContainText("$45.00 each");
  await expect(pegged).toContainText("$11,160.00"); // 4500 c × 248
  await expect(form.getByLabel("Pegged mortise and tenon")).toHaveValue("45.00"); // reloaded from the stored book

  await form.getByLabel("Post 8x8").fill("");
  await form.getByRole("button", { name: "Save prices" }).click();
  await expect(form).toContainText("Saved as version 2.");
  await expect(page.getByTestId("estimate-coverage")).toContainText("partial");
  await expect(page.getByTestId("estimate-total")).toContainText("No total: 1 line(s) unpriced");
});

test("sign-in rejects unknown tokens, and other actors cannot see a project", async ({ page, context }) => {
  await page.goto("/");
  await page.getByLabel("Development token").fill("not-a-token");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("alert")).toContainText("not recognized");

  await page.getByLabel("Development token").fill(TOKENS.a);
  await page.getByRole("button", { name: "Sign in" }).click();
  const projectId = await createProject(page);

  const other = await context.newPage();
  await signIn(other, TOKENS.b);
  await expect(other.getByRole("link", { name: new RegExp(projectId.slice(0, 8)) })).toHaveCount(0);
  await other.goto(`/#/projects/${projectId}`);
  await expect(other.getByRole("alert")).toContainText("Project not found");
});
