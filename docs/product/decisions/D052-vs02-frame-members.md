# D052 — VS-02 frame members: sills, floor joists, principal rafters, purlins, knee braces

**Status:** Confirmed  
**Date:** 2026-11-19  
**Scope:** The member roles the VS-02 generation rule produces, and their placement. Approved as decision 2 of the [VS-02 scope proposal](../../implementation/acceptance-tests/vs-02.md) (§7), within [D051](D051-vs02-slice-boundary.md).

## Decision

A new generation rule (working name `vs02-frame-1`) **generates** every member from the grid, levels, roof, and a few new parameters, as `vs01-post-beam-1` does. User-placed members are deferred. Sections and materials stay **per role** through `FrameSystem.member_defaults` (D039, D040), with one entry for each role the rule generates.

| Role | Placement | New parameter |
|---|---|---|
| `POST`, `BEAM` | Unchanged from `vs01-post-beam-1` | — |
| `SILL` (new) | Along both grid axes on the Level 0 plane, between adjacent grid stations, like the Level 1 beams | — |
| `FLOOR_JOIST` (reserved in VS-01) | Level 1 only, spanning north–south (Y) between X-axis beams, at a fixed spacing within each bay. No joist is placed on a beam line | Joist spacing |
| `PRINCIPAL_RAFTER` (new) | One pair per X grid line (each bent), from the eave plate to the ridge, in the D048 roof planes | — |
| `PURLIN` (new) | Along X between adjacent principal rafters, on each slope, at evenly divided positions between eave and ridge | Purlins per slope |
| `KNEE_BRACE` (new) | At post-to-beam junctions on the Level 1 and eave planes, in each beam's vertical plane, at 45° | Brace leg length; on or off per plane |

**Roof system:** principal rafters and purlins, not common rafters on a ridge beam.

**Identity:** generation keys stay grid-based (D042). Keys for joists, purlins, and braces are derived from grid-line IDs plus an ordinal or side, so members on surviving lines keep their IDs. The exact key formats are specified with the rule.

**Not generated:** girts and studs (with walls, in VS-02b; *resolved by [D066](D066-vs02b-wall-framing.md): generated as wall framing owned by each wall, not as frame members*), dormers, hips, and valleys (the D031 gable only), ceiling joists, and floor openings.

## Rationale

- Principal rafters and purlins are the traditional New England heavy-timber roof (D002–003).
- They follow the grid's bents, which keeps generation keys stable under grid edits.
- They keep member counts in the tens rather than the hundreds.
- Sills, joists, rafters, and braces are what a builder expects in a frame takeoff (D009). They also give VS-02b's assemblies something to attach to.

## Alternatives considered

Common rafters at a spacing on a ridge beam carried by king posts. This suits lighter roofs and later roof assemblies, but adds many members and a spacing grid independent of the bents.

## What this does not decide

The values for Reference House 001 v2 (joist spacing, purlins per slope, brace leg length, and the section and material for each new role) are decision 3. Command names, bounds, and key formats are specified in the VS-02 task files. Nothing here claims structural adequacy (AC-08, FR-07).
