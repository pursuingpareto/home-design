# D077 — VS-02b supported ranges for assembly definition values

**Status:** Confirmed (not yet implemented; [MODEL-006](../../implementation/tasks/MODEL-006.md))  
**Date:** 2026-11-21  
**Scope:** Which assembly definition and opening values have supported-range bounds (stage 4) in version 3. Approved as [MODEL-006](../../implementation/tasks/MODEL-006.md) §13 item 5, within [D066](D066-vs02b-wall-framing.md), [D067](D067-vs02b-assembly-definitions.md), and [D069](D069-vs02b-openings.md).

## Decision

- **Borrowed ranges** (inclusive, `OUT_OF_SUPPORTED_RANGE`, stage 4), each the frame's approved range for the analogous generator input:

  | Field | Supported range | Borrowed from |
  |---|---|---|
  | `framing.stud_spacing_m` (`STUD` framing) | 0.3048–1.2192 m (12"–48") | `joist_spacing_m` ([MODEL-005](../../implementation/tasks/MODEL-005.md) §5) |
  | `framing.girt_count` (`STUD` framing) | 0–4 | `purlins_per_slope` (MODEL-005 §5) |

- **Physical checks only** (stage 3, `OUT_OF_RANGE`) for layer thicknesses, section dimensions, and `jack_threshold_width_m`.
- **Openings** have no size bounds beyond width and height greater than 0 and the fit rules ([D076](D076-vs02b-framed-opening-geometry.md)).
- These are **supported-range limits for the generator, not structural or code limits** (as [D032](D032-vs01-numeric-bounds.md)). Nothing about them claims adequacy (AC-08).
- **Reference House 001 v3** (24" studs, 1 girt; [D072](D072-reference-house-001-v3-design-intent.md)) lies inside them.

## Rationale

- Every generator input has a supported range, as D032 and MODEL-005 §5 set for the frame, so a hand-built snapshot cannot ask the wall rule for an unbounded number of pieces.
- No command can change a definition in VS-02b (D067), so borrowing approved ranges invents no new numbers and costs no user-facing behavior.

## Alternatives considered

- **No supported ranges until definitions become editable:** simpler, but it leaves the generator unbounded for hand-built snapshots.

## What this does not decide

Ranges for user-edited definitions, which come with definition authoring and get their own decision. Payload budgets for wall framing ([D063](D063-vs02-traceability-and-budgets.md)'s ceilings apply; `TEST-003`).
