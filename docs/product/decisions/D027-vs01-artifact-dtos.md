# D027 — VS-01 derived artifact DTOs

**Status:** Confirmed  
**Date:** 2026-11-16  
**Scope:** VS-01 read models for plan, mesh, timber schedule, and preliminary estimate.  
**Amended (2026-11-19):** the envelope and manifest gain a `head` flag, true only when the artifact is for the current head ([ART-001](../../implementation/tasks/ART-001.md) §8, item 4). The change is additive; all other fields are unchanged.  
**Amended by:** [D048](D048-roof-plane-through-wall-line.md) — the `mesh3d` roof surfaces' overhang edge is at 5.334 m (true 9/12 slope), not 5.7912 m; the ridge stays at 8.5344 m.  
**Amended (2026-11-19):** price-book metadata (`currency`, `as_of`, `source`, `geography`) is book-level rather than per row; books are versioned per project ([EST-001](../../implementation/tasks/EST-001.md) §7, item 4; artifacts.md §8.2).
**Amended by:** [D060](D060-vs02-artifact-payloads.md) and [ART-002](../../implementation/tasks/ART-002.md) (implemented 2026-11-20) — version 2 payloads (generator version `"2"`, artifacts.md §5–8): `plan2d` gains a `roof` plane and an array per role, and loses `section_id`; connection markers in `plan2d` and `mesh3d`; connections and counts in `timber_schedule`; `kind`-discriminated estimate lines with "each" connection lines; price-book rows in `m` or `each`.
**Amended by:** [D070](D070-vs02b-quantities-and-outputs.md) and [ART-003](../../implementation/tasks/ART-003.md) (implemented 2026-11-22) — a fifth artifact, `assembly_schedule`, in every manifest and commit response; walls and wall framing in `plan2d` and `mesh3d` and wall estimate lines (generator versions `"3"`); price-book rows in `m2` for `assembly.` keys.

## Decision

Derived outputs for VS-01 are the four artifact types and envelopes specified in [artifacts.md](../../architecture/artifacts.md): `plan2d`, `mesh3d`, `timber_schedule`, `preliminary_estimate`.

- Geometry artifacts are **display views** (plan rings/lines/dimensions; 3D oriented boxes and gable surfaces). They are not the semantic model, not a CAD kernel, and not permit drawings.
- Timber schedule lengths are **reference-axis** lengths and must reconcile with the member inventory.
- Preliminary estimate is gated: **no project price book → `UNAVAILABLE`**, `grand_total_minor` is `null`, never a fabricated `$0`. Partial books must not report a complete grand total.
- Every VS-01 artifact is `suitability: preliminary` with verification claims false (AC-08).
- 2D and 3D may be shown together only when both are `CURRENT` for the same `source_revision_id`.

## What this does not decide

Exact CAD kernel, browser tessellation library, drawing/export files (open question 9), or any licensed price/carbon dataset (open question 6). Three.js remains a provisional renderer (D022).
