# D048 — Gable roof planes pass through the wall line at the eave plate

**Status:** Confirmed  
**Date:** 2026-11-19  
**Scope:** Derived roof geometry in `mesh3d` (and any later roof derivation) for VS-01 gable roofs. Approved from [GEOM-001](../../implementation/tasks/GEOM-001.md) §7, item 1. Closes C1.  
**Amends:** [D027](D027-vs01-artifact-dtos.md) (corrects the artifacts.md §6 example). [D025](D025-reference-house-001-vs01-fixture.md)'s values are unchanged.

## Problem

The confirmed `mesh3d` example placed the roof surfaces' overhang edge at the eave plate height (`z_eave` = 5.7912 m) and the ridge at 8.5344 m. Over the 4.2672 m horizontal run from the overhang edge to the ridge, that is a slope of 7.71/12, not the confirmed 9/12 (D025).

## Decision

- **Roof planes:** each roof plane contains the line where the wall meets the eave plate (`y = origin_y` or `y = origin_y + depth_m`, at `z = z_eave`) and rises toward the ridge at exactly `pitch_rad`. Over the overhang it continues **below** `z_eave`:

  ```text
  z_ridge = z_eave + (depth_m / 2) · tan(pitch_rad)
  z_edge  = z_eave − eave_overhang_m · tan(pitch_rad)
  ```

- **Reference House 001:** `z_ridge` = **8.5344 m** (unchanged; D025 and the reference README's "pitch measured on the 12'-0" wall-to-ridge run") and `z_edge` = **5.334 m**.
- **The `mesh3d` envelope:** `z_eave_m` remains the eave plate height (5.7912 m). Only the surface rings' outer vertices use `z_edge`.
- **The plan:** `plan2d` is unaffected, because its roof plan has no heights.

## Rationale

This keeps every confirmed value: the 9/12 pitch, the 8.5344 m ridge, and the 2'-0" overhang. It also matches how a gable roof is framed, with the rafter plane bearing on the plate line and extending past the wall. The rejected alternative (keep the edge at `z_eave` and raise the ridge to 8.9916 m) would have contradicted D025's confirmed ridge height.

## What this does not decide

- Roof thickness, fascia, rafters, or any structural roof members (out of scope for `vs01-post-beam-1`).
- How the reference axis of the eave beams relates to the roof plane. That stays display-only in VS-01.
