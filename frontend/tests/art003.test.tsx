/**
 * ART-003 §10 and §13 test 14 (D085): the browser interim for VS-02b's payloads. The estimate table labels
 * assembly and wall framing lines and shows areas; the price-book form takes per-square-foot (or per-square-
 * meter) prices for m2 rows and converts them exactly. Walls are not drawn here (UI-004).
 */

import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { EstimateEnvelope } from "../src/api/types";
import { ARTIFACT_LABEL } from "../src/display/labels";
import { formatArea } from "../src/units/length";
import { centsPerSquareMeter, perSquareFootToPerSquareMeter } from "../src/units/money";
import { lineLabel, lineQuantity, type LineItem } from "../src/workspace/lineItems";
import { EstimatePanel } from "../src/workspace/panels";
import { buildBook, initialRows, rowResult, rowText } from "../src/workspace/PriceBookForm";
import fixture from "./fixtures/reference-house-001.json";

const estimate = fixture.envelopes.preliminary_estimate as unknown as EstimateEnvelope;
const complete = fixture.estimate_complete as unknown as EstimateEnvelope;
const lines = estimate.payload!.line_items as LineItem[];
const byKey = (key: string) => lines.find((li) => li.key === key)!;

describe("ART-003 §10: the fifth artifact type", () => {
  it("labels assembly_schedule", () => {
    expect(ARTIFACT_LABEL.assembly_schedule).toBe("Assembly schedule");
    expect(fixture.manifest.artifacts.map((a) => a.artifact_type)).toEqual(["plan2d", "mesh3d", "timber_schedule", "assembly_schedule", "preliminary_estimate"]);
  });
});

describe("ART-003 §10: estimate lines", () => {
  it("labels assembly and wall framing lines, with areas and piece counts", () => {
    expect(lines).toHaveLength(16);
    const bales = byKey("assembly.straw-bale.bales");
    expect(lineLabel(bales, null)).toBe("Straw (straw-bale, bales)");
    expect(lineLabel(byKey("assembly.straw-bale.lime-plaster"), null)).toBe("Lime plaster (straw-bale, lime-plaster)");
    expect(lineQuantity(bales, "imperial")).toBe(formatArea(bales.quantity_value, "imperial"));
    expect(lineQuantity(bales, "imperial")).toMatch(/^1,978\.\d sf$/);
    expect(lineQuantity(bales, "metric")).toBe("183.81 m²");
    const jamb = byKey("wallframing.BUCK_JAMB.1.5x18");
    expect(lineLabel(jamb, null)).toBe("Buck jamb 1.5x18");
    expect(lineQuantity(jamb, "metric")).toBe("53.365 m · 40 pcs");
  });

  it("formats areas in square feet or square meters", () => {
    expect(formatArea(187.29252864, "imperial")).toBe("2,016.0 sf");
    expect(formatArea(187.29252864, "metric")).toBe("187.29 m²");
  });

  it("prices assembly lines per square meter, with the per-square-foot equivalent", () => {
    render(<EstimatePanel estimate={complete} catalog={null} units="imperial" onEditPrices={null} />);
    const row = screen.getByText("Straw (straw-bale, bales)").closest("tr")!;
    expect(within(row).getByText(/\$22\.00\/m²/)).toBeInTheDocument();
    expect(row).toHaveTextContent("≈ $2.0439/sf");
    expect(row).toHaveTextContent(/1,978\.\d sf/);
    const jamb = screen.getByText("Buck jamb 1.5x18").closest("tr")!;
    expect(jamb).toHaveTextContent("$19.00/m");
    expect(jamb).toHaveTextContent("40 pcs");
  });
});

describe("ART-003 §10: m2 price-book rows (AC2b-10's moved bullet)", () => {
  it("converts per-square-foot prices exactly, rounded half-even", () => {
    // $2.04/sf = 204 cents/sf → 204 / 0.09290304 = 2195.83… → 2196 cents/m²
    expect(perSquareFootToPerSquareMeter(204n)).toBe(2196n);
    expect(perSquareFootToPerSquareMeter(145161n)).toBe(1562500n); // exact
    expect(centsPerSquareMeter(2200n, "metric")).toBe(2200n);
    expect(rowResult({ unit: "m2", stored: null, text: "2.04", dirty: true }, "imperial")).toEqual({ kind: "price", unitPriceMinor: 2196 });
    expect(rowResult({ unit: "m2", stored: null, text: "22.00", dirty: true }, "metric")).toEqual({ kind: "price", unitPriceMinor: 2200 });
    expect(rowResult({ unit: "m", stored: null, text: "19.00", dirty: true }, "metric")).toEqual({ kind: "price", unitPriceMinor: 1900 });
  });

  it("shows stored m2 prices per square foot or meter", () => {
    expect(rowText(2200, "m2", "metric")).toBe("22.00");
    expect(rowText(2200, "m2", "imperial")).toBe("2.04");
  });

  it("builds rows from the estimate's lines with their units, and submits m2", () => {
    const rows = initialRows(estimate.payload!, null, "imperial");
    const bales = rows.find((r) => r.key === "assembly.straw-bale.bales")!;
    const jamb = rows.find((r) => r.key === "wallframing.BUCK_JAMB.1.5x18")!;
    expect([bales.unit, jamb.unit]).toEqual(["m2", "m"]);
    const typed = rows.map((r) => (r.key === bales.key ? { ...r, text: "2.04", dirty: true } : r));
    const built = buildBook({ source: "Quote", geography: "VT", as_of: "2026-11-22" }, typed, "imperial")!;
    expect(built.book.rows).toEqual([{ key: "assembly.straw-bale.bales", unit: "m2", unit_price_minor: 2196 }]);
  });
});
