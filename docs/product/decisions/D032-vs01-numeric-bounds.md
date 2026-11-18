# D032 — VS-01 numeric bounds for footprint, grid, and roof

**Status:** Confirmed  
**Date:** 2026-11-18  
**Scope:** Domain validation of snapshots and command candidates in VS-01. Level-height bounds are **not** covered here; they wait on the meaning of `Level.clear_height_m`.

## Decision

These bounds define the configurations **VS-01 supports**. They are not structural limits and do not imply that any member size or span is adequate.

| Parameter | Supported range (inclusive) | Reference House 001 |
|---|---|---|
| `Footprint.width_m`, `Footprint.depth_m` | 3.6576–24.384 m (12'–80') | 10.9728 × 7.3152 m (36' × 24') |
| Bay length (distance between adjacent grid stations, each axis) | 1.2192–7.3152 m (4'–24') | 3.6576 m (12') |
| Grid stations per axis (`x_fractions`, `y_fractions` length) | 2–7 (1–6 bays) | 4 × 3 |
| `GableRoof.pitch_rad` | `atan(0.25)`–`atan(1.0)` (3/12–12/12) | `atan(0.75)` (9/12) |
| `GableRoof.eave_overhang_m` | 0–0.9144 m (0'–3') | 0.6096 m (2') |

### Tolerances

- **Lengths:** bounds are compared using the D026 coordinate comparison epsilon of 1e-6 m. A value within 1e-6 m outside a bound is accepted, so computed stations such as `3.6575999999999995` m pass a 12' bound.
- **Pitch:** compared with a tolerance of 1e-9 rad. The bounds are computed as `atan(0.25)` and `atan(1.0)`; they are not decimal literals.
- **Station count:** an exact integer comparison.

### Error classification

| Condition | Top-level code |
|---|---|
| Physically meaningless: non-finite, zero, or negative lengths; negative overhang; pitch ≤ 0 or ≥ π/2; grid fractions not strictly ascending, or not starting at 0 and ending at 1 | `VALIDATION_FAILED` (422) |
| Physically meaningful but outside the table above | `UNSUPPORTED_CONFIGURATION` (422) |

This follows the split in [D031](D031-vs01-unsupported-configurations.md): malformed input is invalid, and well-formed input VS-01 cannot handle is unsupported. Each failure names its field path. The catalog of detail codes is still to be specified.

### Bay length is checked against the footprint and grid together

Bay lengths are computed from footprint dimensions and grid fractions (`width_m × (x_fractions[i+1] − x_fractions[i])`, and likewise for Y). They are validated on the **full candidate snapshot** after a command is applied, not on the command's arguments alone. As a result, a command that is valid by itself can still be rejected. For example, widening the 3-bay reference frame beyond 72' makes each bay longer than 24', so `SetFootprintDimensions` fails unless the grid is changed first. This is one concrete case of AC-06's "contradictory constraints": the error must name both the footprint field and the affected grid. A rejected command creates no revision.

## Rationale

The bounds contain Reference House 001 with room to edit around it. They keep generated members within plausible display lengths, and they give AC-06 and building-model.md §9 test 2 concrete, testable limits. Upper bounds on footprint and bay length stop extreme inputs from producing absurd geometry. The 4' minimum bay keeps 8×8 posts (0.2032 m) well clear of each other.

## What this does not decide

- Bounds on level elevation, story height, or clear height (they wait on what `clear_height_m` means).
- Bounds on section dimensions (relevant only if `SetMemberSection` is in VS-01).
- The catalog of detail codes.
- Any structural span, load, or member-adequacy limit. Those belong to FR-07 analysis, not to domain validation.

Changing these bounds requires a new decision and updated tests. The fixture does not need to change, as long as it stays within the bounds.
