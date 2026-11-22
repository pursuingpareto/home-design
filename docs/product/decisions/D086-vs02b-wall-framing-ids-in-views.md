# D086 — VS-02b views identify wall framing by ID only

**Status:** Confirmed; implemented in VS-02b by [ART-003](../../implementation/tasks/ART-003.md) (2026-11-22)  
**Date:** 2026-11-22  
**Scope:** How `plan2d` and `mesh3d` identify wall framing pieces, given [D063](D063-vs02-traceability-and-budgets.md)'s per-payload size ceilings. Approved as [ART-003](../../implementation/tasks/ART-003.md) §12 item 5.

## Problem

With the member pattern (a `generation_key` and a `primitive` field on every box), the stud infill reference house's `mesh3d` would measure about 255,500 canonical bytes: 97% of the 256 KiB ceiling, with about 6 KB to spare (prototype measurement, ART-003 §9.4).

## Decision

- **Wall framing entries in `plan2d` and `mesh3d` carry `piece_id` and no `generation_key`.** Mesh framing boxes carry no `primitive` field: every entry is an oriented box by definition.
- **Keys and sections are in the assembly schedule.** Clients join on `piece_id`, as they already join members on `member_id` for sections (ART-002 §4.3).
- **Walls keep their keys** in both views (20 entries on the reference house). Members and connections are unchanged.
- **Measured effect:** the stud infill mesh drops to about 228,000 bytes (87%); with the straw bale default, about 181,000 (69%). As implemented (ART-003 §9.4): 219,188 bytes (84%) and 174,958 (67%).

## Rationale

- Keys are the largest part of each framing entry (66–86 characters on the reference house), and the views need only an identity to select and highlight a piece.
- It keeps D063's ceiling unchanged, with room for `UI-004` and later payload additions.

## Alternatives considered

- **The member pattern, with keys on every piece:** consistent with members, within the ceiling today, but with about 6 KB of headroom.
- **Raise or split the ceiling** for VS-02b payloads: a change to D063, which belongs with `TEST-003`'s budgets.

## What this does not decide

Whether the stud infill house becomes a gated budget case (`TEST-003`). Budgets for the assembly schedule beyond D063's ceilings.
