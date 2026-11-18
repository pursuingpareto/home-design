# D025 — Reference House 001 VS-01 fixture

**Status:** Confirmed  
**Date:** 2026-11-16  
**Scope:** VS-01 integration fixture only  
**Amended by:** [D033](D033-level-story-height.md) — "clear height" below means **story height** (`Level.story_height_m`); values unchanged.

## Decision

Reference House 001 is the VS-01 golden fixture. Exact geometry, grid, roof, sections, generation rules, and the complete semantic snapshot are recorded under [vermont-timber-house](../../reference-projects/vermont-timber-house/).

## Summary of accepted values

- Rectangle **36'-0" × 24'-0"** (`10.9728 m` × `7.3152 m`); two stories; **1,728 sf** total floor area.
- Equal **3 × 2** bays of 12'-0".
- Level 0: elevation `0 m`, clear height 10'-0". Level 1: elevation 10'-0", clear height 9'-0". Z = 0 is first-floor reference, not grade.
- Gable roof, ridge along X, **9/12** pitch, 2'-0" eaves, centered ridge.
- Generated **posts and beams only** (`vs01-post-beam-1`): 24 posts, 34 beams.
- Posts 8×8, beams 8×12, full-sawn actual = nominal. Material eastern white pine with unknown grade and density.

## What this does not decide

This is not an engineered design, mill certificate, or jurisdictional load case. It does not decide connection types, assemblies, rooms, or later reference houses.

Canonical meters and `1 ft = 0.3048 m` follow [D026](D026-canonical-units-identity-persistence.md).
