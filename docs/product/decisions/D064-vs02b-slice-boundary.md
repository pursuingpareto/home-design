# D064 — VS-02b slice boundary: perimeter infill walls with openings

**Status:** Confirmed  
**Date:** 2026-11-21  
**Scope:** What VS-02b delivers, and what waits for a later slice. Chosen as Option 1 of the [VS-02b scope proposal](../../implementation/acceptance-tests/vs-02b.md) §3 (proposal 1), within [D051](D051-vs02-slice-boundary.md), which moved assemblies to VS-02b.

## Decision

VS-02b delivers assemblies **for walls only**, on the VS-02 frame:

- **A. Assembly definitions:** reusable layered definitions for the two initial wall families, straw bale and stud infill (FR-05, D008).
- **B. Walls:** wall records in the frame's perimeter bays, each with an assembly.
- **C. Openings:** doors and windows placed in walls.
- **D. Quantities and cost:** wall areas net of openings, per-layer quantities, and estimate lines for them.
- **E. Thermal and moisture values:** declared layer values with provenance, and an assembly-level figure only when every input is known.

**Not in VS-02b:** roof, floor, and ceiling assemblies (also FR-05). They wait for a later slice.

**Unchanged:** everything stays preliminary (AC-08). Walls make no structural, fire, energy-code, or moisture-performance claim. Structural analysis remains VS-04.

## Rationale

- It delivers D008's straw bale versus stud comparison on the part of the envelope that the frame already bounds.
- Every perimeter bay is a rectangle between generated members, so wall placement can follow the grid, as members do.
- Openings are in scope because walls without them overstate every quantity, and adding them later would change the quantity basis, the schedule, and the estimate again.
- **The cost:** the envelope is incomplete (no roof, floor, or gable-end walls), so any area or thermal total must say "walls only".

## Alternatives considered

- **Option 2, walls without openings:** smaller, with no user-placed records yet, but gross areas overstate quantities and the quantity basis would be reworked when openings arrive.
- **Option 3, the whole envelope** (wall, roof, and floor assemblies): completes FR-05's list, but roof assemblies need decisions about what spans the purlins, and floor assemblies about the joists and the unmodeled foundation.

## What this does not decide

Where walls go and how they relate to the frame, infill framing (studs and girts), what definitions record, how an assembly is chosen, openings, quantities and outputs, property values, and the Reference House 001 v3 design intent. These are proposals 2–9 of the VS-02b scope proposal.
