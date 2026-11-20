# D053 — Reference House 001 v2 design intent for VS-02

**Status:** Confirmed  
**Date:** 2026-11-19  
**Scope:** Values for the VS-02 members of Reference House 001 ([D052](D052-vs02-frame-members.md)). Approved as decision 3 of the [VS-02 scope proposal](../../implementation/acceptance-tests/vs-02.md) (§8). Extends [D025](D025-reference-house-001-vs01-fixture.md); every D025 value is unchanged.

## Decision

These are **illustrative proportions for a test house, not engineered sizes**. They carry no claim of structural adequacy (AC-08, FR-07). Sections are full-sawn, with actual equal to nominal. Imperial values are design intent; canonical values use 1 ft = 0.3048 m (D026).

| Parameter | Value | Canonical |
|---|---|---|
| `SILL` section | 8×8 | 0.2032 × 0.2032 m |
| `FLOOR_JOIST` section | 4×8, depth vertical | 0.1016 × 0.2032 m |
| Joist spacing | 24" on center, from each bay's west beam line | 0.6096 m |
| `PRINCIPAL_RAFTER` section | 8×10, depth perpendicular to the roof plane | 0.2032 × 0.2540 m |
| `PURLIN` section | 6×8 | 0.1524 × 0.2032 m |
| Purlins per slope | 2, at 1/3 and 2/3 of the 15' rafter slope | — |
| `KNEE_BRACE` section | 4×6 | 0.1016 × 0.1524 m |
| Brace leg length | 3'-0" | 0.9144 m |
| Braces enabled | Level 1 and eave planes; one at each end of every beam | — |
| Material, every new role | Eastern white pine; grade, density, and provenance `null` | As D025 |

**Inventory: 193 members:**

| Role | Count |
|---|---|
| Posts | 24 |
| Beams | 34 |
| Sills | 17 |
| Floor joists | 30 |
| Principal rafters | 8 |
| Purlins | 12 |
| Knee braces | 68 |

The VS-02 rule and fixture must reproduce exactly these counts.

## What this does not decide

- **How members bear on each other**, for example joists on top of beams or framed into them. This affects reference axes only, and is specified with the rule. *Resolved by [D058](D058-datum-reference-axes.md): axes lie on datums, and joists frame into beams.*
- **Connections.** Decision 4 of the proposal settles them.
- **Loads, foundations, and code compliance.** These remain open, as in D025.
