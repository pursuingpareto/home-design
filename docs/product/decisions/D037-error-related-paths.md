# D037 — `related_paths` on error details

**Status:** Confirmed  
**Date:** 2026-11-18  
**Scope:** The error detail object in [interfaces.md §7](../../architecture/interfaces.md#7-error-contract). Approved from [MODEL-001](../../implementation/tasks/MODEL-001.md) §9, item 3.  
**Amended by:** [D042](D042-stable-grid-line-ids.md). The bay-length row's `path` is now the grid's `x_lines` or `y_lines`, replacing `x_fractions` / `y_fractions`. A new row, `DUPLICATE_LINE_ID`, takes each later occurrence's `id` as `path` and the first occurrence's `id` as `related_paths`. The other rows are unchanged.

## Decision

An error detail may include an optional **`related_paths`** array, for issues that involve more than one field:

```json
{
  "path": "entities[4223b175-1758-59fc-95fc-073ee00eaf99].x_fractions",
  "code": "OUT_OF_SUPPORTED_RANGE",
  "related_paths": ["entities[9ba359f1-6354-5019-9b3f-d15f8e53523b].width_m"]
}
```

- **What `path` points at:** `path` stays the single main location, the field that holds the violated rule. `related_paths` lists the other fields that contribute to the issue, written in the [D036](D036-error-path-syntax.md) syntax.
- **Shape:** entries are unique, never repeat `path`, and are sorted by code unit. The field is **left out when there is nothing to list**; it is never an empty array.
- **No effect on order or identity:** issues are still ordered by `(path, code)`. `related_paths` does not affect ordering, and does not count toward one issue being distinct from another.
- **Backward compatible:** this is additive. Clients that ignore unknown fields are unaffected, and generated TypeScript types include it automatically.
- **Commands:** command processing (`MODEL-003`) may translate snapshot paths into `args.` paths, so that the field the user just edited appears either as `path` or in `related_paths`. The translation rules belong to that task.

## Initial mapping for checks that span several fields

| Detail code | Situation | `path` | `related_paths` |
|---|---|---|---|
| `OUT_OF_SUPPORTED_RANGE` | Bay length outside D032 bounds | the grid's `x_fractions` or `y_fractions` | footprint `width_m` or `depth_m` |
| `STORY_HEIGHT_MISMATCH` | D033 consistency | lower level's `story_height_m` | next level's `elevation_m` |
| `NOT_STRICTLY_ASCENDING` | Level elevations | the higher-index level's `elevation_m` | the previous level's `elevation_m` |
| `MEMBER_SET_MISMATCH` | Member missing from, or extra in, `member_ids` | `FrameSystem.member_ids` | each affected `entities[<member id>]` (when the member exists) |
| `DUPLICATE_ID` | Shared ID | each later occurrence, `entities[#j]` | the first occurrence, `entities[#i]` |
| `DUPLICATE_GENERATION_KEY` | Shared key | `generation_key` of each member after the first (by `id` order) | the first member's `generation_key` |

New detail codes that span fields add their mapping to [building-model.md §6.1](../../architecture/building-model.md#61-detail-codes). Changing an existing mapping requires a decision, like changing a detail code ([D035](D035-validation-stages-detail-codes.md)).

## Rationale

One issue per problem, with every contributing field linked, lets a UI highlight all the inputs involved. Reporting one issue per field would duplicate messages and lose the link between them.
