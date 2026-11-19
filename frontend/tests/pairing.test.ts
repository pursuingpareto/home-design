import { describe, expect, it } from "vitest";

import type { MeshEnvelope, PlanEnvelope } from "../src/api/types";
import { pairViews } from "../src/views/pairing";
import { mesh, plan } from "./fixtures";

const statuses = ["CURRENT", "STALE", "MISSING", "UNAVAILABLE", "FAILED", "COMPUTING", "QUEUED", "SUPERSEDED"] as const;

describe("pairViews (artifacts.md §4, §10 test 6)", () => {
  it("pairs only CURRENT envelopes of the same revision", () => {
    const paired = pairViews(plan, mesh);
    expect(paired.kind).toBe("paired");
    if (paired.kind === "paired") expect(paired.revisionId).toBe(plan.source_revision_id);
  });

  it("refuses every other status combination", () => {
    for (const p of statuses) {
      for (const m of statuses) {
        if (p === "CURRENT" && m === "CURRENT") continue;
        const result = pairViews({ ...plan, status: p } as PlanEnvelope, { ...mesh, status: m } as MeshEnvelope);
        expect(result).toEqual({ kind: "unpaired", plan: p, mesh: m, mismatch: false });
      }
    }
  });

  it("refuses mismatched revisions even when both are CURRENT", () => {
    const other = { ...mesh, source_revision_id: "00000000-0000-4000-8000-00000000ffff" };
    expect(pairViews(plan, other)).toMatchObject({ kind: "unpaired", mismatch: true });
  });

  it("reports loading while either envelope is missing", () => {
    expect(pairViews(null, mesh)).toEqual({ kind: "unpaired", plan: "LOADING", mesh: "CURRENT", mismatch: false });
    expect(pairViews(plan, undefined)).toEqual({ kind: "unpaired", plan: "CURRENT", mesh: "LOADING", mismatch: false });
  });

  it("refuses a CURRENT envelope without payload", () => {
    expect(pairViews({ ...plan, payload: null }, mesh).kind).toBe("unpaired");
  });
});
