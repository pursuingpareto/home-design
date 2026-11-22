# D072 — Reference House 001 v3 design intent for VS-02b

**Status:** Confirmed  
**Date:** 2026-11-21  
**Extended by:** [D081](D081-reference-house-001-v3-template-text.md): the two definitions' installation notes and unverified climate details.  
**Scope:** The values the VS-02b fixture needs: wall definitions, their framing, the default assembly, and openings. Approved as proposal 9 of the [VS-02b scope proposal](../../implementation/acceptance-tests/vs-02b.md) (§14), as revised for [D066](D066-vs02b-wall-framing.md)–[D071](D071-vs02b-thermal-moisture-values.md). Extends [D025](D025-reference-house-001-vs01-fixture.md) and [D053](D053-reference-house-001-v2-design-intent.md); every value there is unchanged.

## Decision

These are **illustrative values for a test house, not a specification**. Nothing about them is checked or claimed (AC-08): no structural, fire, energy-code, or moisture performance. Imperial values are design intent; canonical values use 1 ft = 0.3048 m and 1 in = 0.0254 m (D026). Dimensional lumber is given by nominal size with its actual dimensions.

| Item | Value |
|---|---|
| Default wall assembly | Straw bale; stud infill as the alternative ([D068](D068-vs02b-wall-assembly-choice.md)) |
| Straw bale build-up, exterior to interior | Lime plaster 1½"; straw bales laid flat 18" (the fill); clay plaster 1" |
| Straw bale framing | Girts: 0. Bucks: 1½" × 18", spruce-pine-fir |
| Stud infill build-up, exterior to interior | Wood siding ¾"; sheathing ½"; framing layer 5½" (2×6 studs with dense-pack cellulose fill); gypsum board ½" |
| Stud infill framing | Studs 2×6 (1½" × 5½"), 24" on center, spruce-pine-fir. Girts: 1 per wall, at mid-height, 2×6. Headers: 2×8 (1½" × 7¼"), one piece. Jack threshold width: 4'-0" |
| Materials | One `Material` per layer and framing material: lime plaster, straw, clay plaster, wood siding, sheathing, spruce-pine-fir, dense-pack cellulose, gypsum board. Every property `null` |
| Thermal and moisture values | `null` (no sourced values supplied; open question 6). The reference house shows framing fractions and no U-values ([D071](D071-vs02b-thermal-moisture-values.md)) |
| Openings (rough openings, [D069](D069-vs02b-openings.md)) | One 3'-0" × 6'-8" door, centered in the middle Level 0 bay of the south wall. One 5'-0" × 4'-0" window, sill at 3'-0", centered in each outer Level 0 bay of the south wall. One 3'-0" × 4'-0" window, sill at 3'-0", centered in each of the other 17 walls |

**Resulting inventory:**

- 20 walls ([D065](D065-vs02b-wall-placement.md)), all straw bale by default;
- 1 door and 19 windows; the two 5'-0" windows exceed the jack threshold, the rest do not;
- 2,280 sf (211.8189312 m²) gross and 264 sf (24.52640256 m²) of rough openings, so **2,016 sf (187.29252864 m²)** of net reference wall area;
- wall framing: **79 buck pieces** with the straw bale default (3 for the door, 4 for each window); with stud infill, about 250 pieces, with the exact count specified with the rule and reconciled in tests;
- the timber frame unchanged: 193 members and 312 connections.

Every opening fits D069: kings clear the 3' brace legs (outer faces 4'-4½" from the posts for 3'-0" openings, 3'-3" for the 5'-0" windows with jacks), headers stay below the upper planes, and mid-height girts lie below the brace feet and are cut at every opening.

## What this does not decide

- Exact canonical values and key formats (MODEL-006, ASM-001). Exact stud-infill piece counts are derived from these values by the rule.
- Any sourced thermal, moisture, cost, or environmental value. These stay `null` until supplied with a source.
- Loads, foundations, and code compliance, which remain open, as in D025 and D053.
