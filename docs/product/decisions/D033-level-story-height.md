# D033 — `Level.story_height_m` replaces `clear_height_m`

**Status:** Confirmed  
**Date:** 2026-11-18  
**Scope:** The `Level` entity schema, the Reference House 001 fixture, and the `vs01-post-beam-1` generation rule. Amends the terminology (not the values) of [D025](D025-reference-house-001-vs01-fixture.md).

## Problem

The field `Level.clear_height_m` did not hold a clear height:

- `vs01-post-beam-1` uses Level 1's value to locate the eave plate (`z_eave = elevation + clear_height`), the plane the eave beams sit on. Because those beams are 12" deep, the real headroom under them is less than the stored value.
- Level 0's value (3.048 m) only repeated the gap to Level 1's elevation. The generator never read it, and nothing prevented the two from disagreeing.

Later features that need a true clear height, such as headroom, egress, and MEP clearance checks, would have been misled by the name.

## Decision

- Rename `Level.clear_height_m` to **`Level.story_height_m`**: the vertical distance from a level's `elevation_m` up to the next datum above it.
  - For a level that is not the top level, that datum is the next level's `elevation_m`.
  - For the top level, it is the eave plate: `z_eave = top.elevation_m + top.story_height_m`.
- **Consistency check:** for every level except the top one, `story_height_m` must equal `next.elevation_m − elevation_m` within 1e-6 m. A mismatch is a contradictory constraint (AC-06) and is rejected with `VALIDATION_FAILED`, naming both fields. It is never silently corrected.
- `story_height_m` must be finite and greater than zero (`VALIDATION_FAILED` otherwise). Supported ranges are still to be specified.
- **Values unchanged:** Reference House 001 keeps its values. Level 0 has `story_height_m` 3.048 (10'-0"); Level 1 has `story_height_m` 2.7432 (9'-0"), so `z_eave` stays 5.7912 m. The fixture already passes the consistency check.
- True **clear height** is not a stored field. When the model knows floor and beam depths in a later slice, it becomes a value derived from story height and structure. Until then, no artifact may label any value "clear height".

## Schema version and fixture identity

No implementation or persisted data exists yet, so this is a **pre-release correction of schema version 1**: `model_schema_version` and the entity `schema_version` stay `1`, and no migration is written. The fixture keeps its `revision_id` and every entity ID. It is a specification file, not a stored revision. Any change to `Level` after implementation begins requires a schema version bump and a migration, as building-model.md §8 says.

## Effect on D025

D025's values and geometry are unchanged. Where D025 says "clear height 10'-0"" and "clear height 9'-0"", read "story height". D025 carries a note pointing here; its text is otherwise left as confirmed.
