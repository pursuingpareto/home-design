# D043 — VS-01 command set and arguments

**Status:** Confirmed  
**Date:** 2026-11-18  
**Scope:** The VS-01 command types and the arguments of the commands listed below. Approved from [MODEL-003](../../implementation/tasks/MODEL-003.md) §10, item 1. Partially closes gap M5.  
**Amends:** [D034](D034-vs01-level-bounds.md) (renames the command it mentions).

## Decision

### Arguments are strict

Every argument listed is required, and unknown arguments are rejected (as [D038](D038-field-presence-catalog-records.md) does for records). Units are canonical: meters and radians ([D026](D026-canonical-units-identity-persistence.md)). Conversion from feet or rise-over-run happens in the UI.

| `type` | `args` | Effect |
|---|---|---|
| `CreateReferenceProject` | `{}` | Creates a project from the Reference House 001 template |
| `SetFootprintDimensions` | `{width_m, depth_m}`, both required | Sets the footprint dimensions and regenerates members (keys and IDs kept, endpoints move) |
| `SetStoryHeights` | `{story_heights_m: [h0, h1]}`, ordered by level index | Sets `L0.story_height_m = h0`, `L1.elevation_m = h0`, and `L1.story_height_m = h1`, then regenerates members. Level 0 stays at elevation 0 (D034), and the D033 consistency check holds by construction |
| `SetGableRoofParameters` | `{pitch_rad, eave_overhang_m}` | Sets those roof fields. `ridge_axis` and `ridge_offset_m` are not arguments, because [D031](D031-vs01-unsupported-configurations.md) fixes them |
| `SetMemberSection` | `{role, section_id}` | Sets one role's section default and regenerates that role ([D040](D040-setmembersection-role-default.md)) |
| `SetTimberGrid` | `{x_lines, y_lines}`, full replacement; see note below | Replaces grid lines; members on kept lines keep their IDs (D042) |

**`SetLevelElevations` is renamed to `SetStoryHeights`.** With D033 and D034, Level 0's elevation is fixed and Level 1's elevation equals Level 0's story height. The only free values are the two story heights, and the old name described a parameter that callers cannot set independently.

**Note (2026-11-18):** the `SetTimberGrid` argument shape was approved separately as MODEL-003 §10, item 2, and is specified in [interfaces.md §2.1](../../architecture/interfaces.md#21-settimbergrid-arguments). `AddSection {nominal_label, actual_width_m, actual_depth_m}` was approved as item 3 and added to the VS-01 command set (interfaces.md §2). Material commands remain deferred. `UndoToRevision` was approved as item 4 and recorded as [D044](D044-undo-to-revision.md).

### Pending (not decided here)

- Commands for changing or adding materials: deferred, and not in VS-01 (MODEL-003 §4.6).
- Per-member commands: not in VS-01 (D040).

## Rationale

These commands cover every editable VS-01 parameter: footprint, story heights, roof, grid, and member section. Each argument maps to fields the supported domain allows to vary. Fields that D031 and D034 fix (rotation, origin, ridge axis and offset, Level 0's elevation) have no arguments, so callers cannot attempt unsupported edits.
