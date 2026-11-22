# D083 — VS-02b layer placement: the framing layer is centered on the wall's reference plane

**Status:** Confirmed; implemented in VS-02b by [ART-003](../../implementation/tasks/ART-003.md) (2026-11-22)  
**Date:** 2026-11-22  
**Scope:** Where each layer of a wall's build-up sits through the wall's thickness, as the views (`plan2d`, `mesh3d`) draw it. Approved as [ART-003](../../implementation/tasks/ART-003.md) §12 item 2.  
**Settles:** [D065](D065-vs02b-wall-placement.md)'s "the definition's layers are placed symmetrically about it unless the approved build-ups say otherwise".

## Problem

Every wall framing piece's axis lies on the wall's reference plane, the grid line ([ASM-001](../../implementation/tasks/ASM-001.md)). The [D072](D072-reference-house-001-v3-design-intent.md) build-ups are not symmetric about their framing layers, so centering the whole build-up on the plane would put the bucks ¼" off the center of the bale layer and the studs ⅜" off the center of their cavity: the framing would show partly outside its own layer.

## Decision

- **The framing layer is centered on the reference plane.** The layers before it in the build-up are stacked toward the exterior (away from the footprint), and those after it toward the interior, in build-up order.
- So the total build-up is generally not centered on the grid line. Reference House 001 v3: straw bale extends 10½" outside the grid line and 10" inside (20½" in all); stud infill 4" outside and 3¼" inside (7¼").
- Display and reporting only: no quantity depends on it, and the model, the wall rule, and the fit are unchanged.

## Rationale

- Every framing piece then sits inside its layer, on its model axis, with no display offset.
- It is the build-ups' own geometry: framing and fill share one layer, so that layer, not the whole build-up, is what lies on the frame's plane.

## Alternatives considered

- **Center the whole build-up** (D065 read literally): 10¼" each side for straw bale. The views would have to offset every framing piece from its axis or draw it outside its layer.

## What this does not decide

Layer placement for a later wall placement rule (for example walls outside the frame, D065's alternative). Any detailing claim at posts and beams (AC-08).
