# D034 — VS-01 level datum and story-height bounds

**Status:** Confirmed  
**Date:** 2026-11-18  
**Scope:** Domain validation of `Level` records in VS-01 snapshots and command candidates. Completes the bounds left open by [D032](D032-vs01-numeric-bounds.md), using the `story_height_m` field from [D033](D033-level-story-height.md).  
**Amended by:** [D043](D043-vs01-command-set.md) — `SetLevelElevations` is renamed `SetStoryHeights`; the rules are unchanged.

## Decision

| Rule | Requirement | Rejected with |
|---|---|---|
| Level count and indices | Exactly two levels, with `index` exactly `0` and `1` | `UNSUPPORTED_CONFIGURATION` for a well-formed snapshot with a different number of levels; `VALIDATION_FAILED` for duplicate, negative, or non-integer indices |
| Level 0 elevation | `elevation_m` exactly `0` (negative zero counts as zero) | `VALIDATION_FAILED` |
| Story height, each level | 2.4384–4.2672 m (8'–14'), inclusive, compared with the 1e-6 m epsilon | `UNSUPPORTED_CONFIGURATION` when finite and positive but outside the range; non-finite or ≤ 0 is `VALIDATION_FAILED` (D033) |

- **Level 0 elevation:** this generalizes the datum D025 and D026 set for Reference House 001 (Z = 0 is the first-floor reference, not grade) to all of VS-01, because every VS-01 project is created from that template. Like the footprint origin in [D031](D031-vs01-unsupported-configurations.md), it is a datum, not a scope limit, so it is compared exactly. A future slice that models grade or foundations may introduce a separate site datum, but it must not move this datum.
- **Level 1 elevation:** follows from the D033 consistency check (`level[1].elevation_m = level[0].story_height_m`), so its range is 8'–14'.
- **Eave plate:** `z_eave` therefore falls between 16' and 28' above the first-floor reference.
- **Checked on the candidate snapshot:** as in D032, the bounds apply to the full snapshot after a command is applied. A `SetLevelElevations` command that would break the consistency check or these ranges creates no revision.

Reference House 001 (10' and 9' story heights) is within these bounds.

## Rationale

The 8' minimum allows for story height including the 12"-deep beams on the floor and eave planes, so the space under the beams is shorter than the story height. The 14' maximum keeps posts within plausible display lengths. **These are supported-range limits only. They are not headroom, egress, or building-code requirements**, which remain open (open question 5).

## What this does not decide

- More than two levels, lofts, or split levels (future slices).
- True clear height (derived later, D033).
- Any code-based minimum ceiling height.
