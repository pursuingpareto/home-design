# D058 — Member reference axes lie on datums; joists frame into beams

**Status:** Confirmed (implemented in VS-02)  
**Date:** 2026-11-19  
**Scope:** Where the reference axes of `vs02-frame-1` members lie, and how members bear on each other. Approved from [TIMBER-002](../../implementation/tasks/TIMBER-002.md) §11, item 1.  
**Amended by:** [D066](D066-vs02b-wall-framing.md), for VS-02b wall framing only: king and jack positions and cripple ends use the definition's stud and header sections. The timber frame is unchanged.  
**Resolves:** the open point in [D053](D053-reference-house-001-v2-design-intent.md), "how members bear on each other".

## Decision

Every member's reference axis lies on a **datum**: a grid station, a level or eave plane, or a [D048](D048-roof-plane-through-wall-line.md) roof plane. **Section sizes never move an axis.**

- **Posts, beams, and sills** lie on grid stations and on the Level 0, Level 1, and eave planes.
- **Floor joists frame into beams:** their axes lie on the Level 1 plane, level with the beam axes, and end on the beams' axes. This matches [D054](D054-vs02-connection-catalog.md)'s `joist-beam` class and its `HOUSED_DOVETAIL` default.
- **Principal rafters bear on the plate line:** each runs in the roof plane from the wall line at `z_eave` to the ridge. There are no rafter tails over the eave overhang, which stays roof-surface geometry only.
- **Purlins lie in the roof plane** and cross the rafter axes.
- **Knee braces lie in their beam's vertical plane**, from a point on the post axis to a point on the beam axis.

## Rationale

- **Exact junctions:** every junction is an intersection of axes, so connection locations (D054) are exact points.
- **Independent sections:** a section change changes only sections. Members and connections never move for it, and the `plan2d` selector (axes, not sections; [D056](D056-dependency-selectors.md)) stays meaningful.
- **Lengths unchanged in meaning:** lengths remain reference-axis lengths, already labeled "not fabrication cut lengths".

## Alternatives considered

Joists bearing on top of beams, with axes raised by half the beam depth plus half the joist depth. This is closer to some framing practice, but it couples geometry to sections: a section change would move other members and their connections.

## What this does not decide

- Machining, cut lengths, and the physical offset of members from their axes: these are fabrication concerns, still out of scope.
- How `mesh3d` orients each new role's box (`ART-002`), beyond D053's "depth vertical" and "depth perpendicular to the roof plane".
- Any structural claim. Nothing here asserts that a bearing is adequate (AC-08).
