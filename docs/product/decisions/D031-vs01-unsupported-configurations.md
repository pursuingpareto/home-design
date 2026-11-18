# D031 — VS-01 unsupported footprint and roof configurations

**Status:** Confirmed  
**Date:** 2026-11-18  
**Scope:** Domain validation of snapshots and commands in VS-01. The fields stay in the schema for later slices.

## Decision

Some values are allowed by the schema but not handled by the `vs01-post-beam-1` generation rule or the `plan2d`/`mesh3d` specifications. VS-01 rejects them instead of producing incorrect or invented output.

| Field | VS-01 requirement | Rejected with | Reason |
|---|---|---|---|
| `Footprint.rotation_rad` | `0` | `UNSUPPORTED_CONFIGURATION` (422) | The station formulas ignore rotation; a rotated footprint would place members incorrectly. |
| `GableRoof.ridge_axis` | `"X"` | `UNSUPPORTED_CONFIGURATION` (422) | The plan and mesh roof rules (ridge, eave ring, south/north surfaces) are defined only for a ridge along X. |
| `GableRoof.ridge_offset_m` | `0` | `UNSUPPORTED_CONFIGURATION` (422) | With a single `pitch_rad`, an off-center ridge is ambiguous (different pitches or different eave heights), and the sign convention is undefined. |
| `Footprint.origin_m` | `[0, 0]` | `VALIDATION_FAILED` (422) | Not a scope limit but a consequence of [D026](D026-canonical-units-identity-persistence.md): the building-local origin *is* the southwest footprint corner. |

- **Exact comparison:** these values must be exactly zero (or `"X"`). Negative zero counts as zero, and RFC 8785 writes it as `0` anyway. No tolerance applies, because no VS-01 command sets these fields. They can only come from the reference template or from a submitted snapshot, so a near-zero value means a mistake upstream.
- **Error details:** each rejection names the field path (for example `entities[<id>].ridge_axis`, or `args.ridge_offset_m` for a command), as in the [error contract](../../architecture/interfaces.md#7-error-contract). The catalog of detail codes is still to be specified.
- **Commands:** if a VS-01 command such as `SetGableRoofParameters` exposes any of these fields, the same rules apply to its arguments, and a rejected command creates no revision.
- **Enums keep `Y`:** the `ridge_axis` enum keeps `Y`. The schema accepts it, and domain validation rejects it as unsupported. That keeps "unsupported in VS-01" (`UNSUPPORTED_CONFIGURATION`) separate from "malformed" (`VALIDATION_FAILED`).

## Rationale

This follows FR-07 and the domain validation rule in building-model.md §6: unsupported cases return an explicit result, never a silent pass or invented geometry. Reference House 001 (D025) uses none of these configurations. A Y-axis ridge would be cheap to add later as a mirrored roof rule, but it is not needed for any VS-01 acceptance criterion.

## What this does not decide

- Numeric bounds for width, depth, bays, pitch, overhang, and levels.
- The catalog of detail codes.
- How rotation, Y-axis ridges, or offset ridges will be supported later. Each will need its own generation-rule version and artifact rules.
