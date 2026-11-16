# D025 — Reference House 001 VS-01 fixture

**Status:** Confirmed  
**Date:** 2026-11-16  
**Scope:** VS-01 integration fixture only

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

This is not an engineered design, mill certificate, or jurisdictional load case. It does not confirm units/coordinate policy for the product (still provisional in architecture v0.2), connection types, assemblies, rooms, or later reference houses.

Canonical storage uses meters and `1 ft = 0.3048 m` because that is the current provisional model policy, not because D025 confirms that policy as a product-wide decision.
