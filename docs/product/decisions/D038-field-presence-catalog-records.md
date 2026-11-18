# D038 — Required keys, explicit nulls, and catalog records

**Status:** Confirmed  
**Date:** 2026-11-18  
**Scope:** Semantic snapshot records (building-model.md §3). Approved from [MODEL-001](../../implementation/tasks/MODEL-001.md) §9, items 4–5.

## Decision

### Field presence

- Every field listed for a record in [building-model.md §3.1](../../architecture/building-model.md#31-entity-types-for-vs-01) is a **required key**.
- Fields marked `?` (for example `Material.grade`, `density_kg_m3`, `species`, `provenance`) are **required keys whose value may be `null`**. They are never omitted. A missing key is `MISSING_FIELD`, and an unknown key is `UNKNOWN_FIELD`.
- **Why:** "unknown" stays explicit, as D026 requires (unknown is not zero and not assumed), and a record has one canonical byte form instead of two (key absent vs. `null`), as D029 requires.

### Catalog records

- **`Section` and `Material`** records may exist in a snapshot without being referenced by any member. They act as the project's catalog of available sections and materials.
- Every **`Footprint`, `Level`, `GableRoof`, `TimberGrid`, and `FrameSystem`** must be referenced from `building` or from the `FrameSystem`. Otherwise the snapshot fails with `UNREFERENCED_ENTITY` ([D035](D035-validation-stages-detail-codes.md)).
- Every **`TimberMember`** must be listed in `FrameSystem.member_ids` (`MEMBER_SET_MISMATCH`).
- **Why:** an unreferenced footprint, level, or roof has no meaning and almost certainly signals an error. Unused sections and materials are harmless, and a future section-assignment feature will need them.

## What this does not decide

- How generated members get their section and material (open gap M1). Catalog records make several options possible but choose none of them.
- Whether unreferenced catalog records appear in schedules or estimates. They do not in VS-01, because both are derived from members.
- Garbage collection or deletion of catalog records.
