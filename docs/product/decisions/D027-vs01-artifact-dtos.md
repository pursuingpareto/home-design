# D027 — VS-01 derived artifact DTOs

**Status:** Confirmed  
**Date:** 2026-11-16  
**Scope:** VS-01 read models for plan, mesh, timber schedule, and preliminary estimate.

## Decision

Derived outputs for VS-01 are the four artifact types and envelopes specified in [artifacts.md](../../architecture/artifacts.md): `plan2d`, `mesh3d`, `timber_schedule`, `preliminary_estimate`.

- Geometry artifacts are **display views** (plan rings/lines/dimensions; 3D oriented boxes and gable surfaces). They are not the semantic model, not a CAD kernel, and not permit drawings.
- Timber schedule lengths are **reference-axis** lengths and must reconcile with the member inventory.
- Preliminary estimate is gated: **no project price book → `UNAVAILABLE`**, `grand_total_minor` is `null`, never a fabricated `$0`. Partial books must not report a complete grand total.
- Every VS-01 artifact is `suitability: preliminary` with verification claims false (AC-08).
- 2D and 3D may be shown together only when both are `CURRENT` for the same `source_revision_id`.

## What this does not decide

Exact CAD kernel, browser tessellation library, drawing/export files (open question 9), or any licensed price/carbon dataset (open question 6). Three.js remains a provisional renderer (D022).
