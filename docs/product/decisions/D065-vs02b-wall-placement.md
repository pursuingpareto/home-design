# D065 — VS-02b wall placement: generated in-plane infill in every perimeter bay

**Status:** Confirmed  
**Refined by:** [D083](D083-vs02b-layer-placement.md): the framing layer, not the whole build-up, is centered on the reference plane.  
**Date:** 2026-11-21  
**Scope:** Which surfaces get walls in VS-02b, how a wall relates to the frame, and whether walls are generated or placed. Approved as proposal 2 of the [VS-02b scope proposal](../../implementation/acceptance-tests/vs-02b.md) (§7), within [D064](D064-vs02b-slice-boundary.md).

## Decision

- **Where:** one wall in every **perimeter bay of each story**: between two adjacent grid stations on a perimeter grid line, from the story's lower datum to its upper one (Level 0: `z0` to `z1`; Level 1: `z1` to `z_eave`). The count is `2 · ((nx − 1) + (ny − 1))` per story.
- **In-plane infill:** the wall fills the bay between posts. Its reference plane is the grid line, as member axes lie on datums ([D058](D058-datum-reference-axes.md)). The definition's layers are placed symmetrically about it unless the approved build-ups say otherwise.
- **Generated, not placed,** as members and connections are: walls regenerate with the frame, keep their IDs under footprint, story, and roof edits, and are added or removed with grid lines ([D042](D042-stable-grid-line-ids.md)). Users cannot remove a wall to leave a bay open in VS-02b.
- **Not in VS-02b:** gable-end triangles above the eave tie beams, interior partitions, rooms, and walls off the grid.

**Reference House 001:** 10 walls per story, **20 walls**, with reference areas of 1,200 sf on Level 0 and 1,080 sf on Level 1 (2,280 sf, 211.8189312 m²; from the D025 dimensions). The gable-end triangles left out are 216 sf.

### Consequences accepted

- **Knee braces lie in the perimeter wall planes.** With both brace planes on, each perimeter wall has a brace in each top corner: 40 of the reference house's 68 braces. Quantities ignore them, and an assumption line says so (how quantities are measured is proposal 7).
- **Bales are thicker than posts.** An in-plane straw bale wall projects beyond the posts on both sides. That is a display and detailing fact; the wall's plane stays on the grid line.

## Rationale

- "Infill" is the word D008, the vision, and the roadmap use.
- A plane on the grid line keeps walls independent of member sections, as D058 did for member axes: a section change never moves a wall.
- Generating walls from the grid gives them stable, grid-based identity and conformance, as members have, with no hand-placement identity story yet.

## Alternatives considered

- **Outside the frame (a wrap):** common for straw bale on timber frames, keeping the frame exposed inside and avoiding bridging at the posts. Its plane would sit at the frame's outer face, so post sections would move walls.
- **Per family:** straw bale outside, stud infill in plane. Two placement rules.
- **User-placed walls** (an `AddWall` command): needed eventually for interior and off-grid walls, but needs its own identity and validation story.
- **Gable-end walls now:** completes the end walls, but needs triangular panels in 2D, 3D, and quantities.

## What this does not decide

Infill framing, definition contents, how an assembly is chosen, openings, quantities, property values, and the Reference House 001 v3 design intent (proposals 3–9). Wall generation keys and conformance codes follow proposal 11 and are set in the task file. Nothing here claims structural, fire, energy-code, or moisture performance (AC-08).
