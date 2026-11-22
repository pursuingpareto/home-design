# D081 — Reference House 001 v3 template text: installation notes and unverified climate details

**Status:** Confirmed (implemented in VS-02b; [ASM-001](../../implementation/tasks/ASM-001.md) with [MODEL-006](../../implementation/tasks/MODEL-006.md))  
**Date:** 2026-11-22  
**Scope:** The `installation_note` and `unverified_climate_details` of the template's two assembly definitions. Approved as [ASM-001](../../implementation/tasks/ASM-001.md) §13 item 4, which answers the question [MODEL-006](../../implementation/tasks/MODEL-006.md) §13 left to ASM-001.  
**Extends:** [D072](D072-reference-house-001-v3-design-intent.md), which gave the build-ups and values but no text. Within [D067](D067-vs02b-assembly-definitions.md) (the fields) and [D071](D071-vs02b-thermal-moisture-values.md) (the details are shown with every figure, under the unverified-climate warning).

## Decision

This text is **illustrative, like D072's values**. Nothing in it is checked or claimed (AC-08). The climate details are items to verify, not recommendations.

### `straw-bale`

**`installation_note`:** "Straw bales laid flat in courses between the posts, from sill to beam, with a 1½" × 18" buck at every opening. Lime plaster outside and clay plaster inside, applied to the bales. Illustrative build-up for a test house, not a specification."

**`unverified_climate_details`**, in this order:

1. "Bale moisture protection at the sill: a raised base and a capillary break below the first course."
2. "Exterior lime plaster and its rain protection (overhangs, splash zone, or a rain screen) for the site's exposure."
3. "Plaster junctions at posts, beams, and bucks (cracking and air leakage)."
4. "Flashing and sill pans at window and door bucks."
5. "Bale moisture content at installation, and drying through both plasters."

### `stud-infill`

**`installation_note`:** "2×6 studs at 24" on center between the posts, one mid-height girt let in across them, and kings and headers at every opening (jacks above 4'-0"). Dense-pack cellulose between the studs, sheathing and wood siding outside, gypsum board inside. Illustrative build-up for a test house, not a specification."

**`unverified_climate_details`**, in this order:

1. "Water-resistive barrier and rain-screen gap behind the siding."
2. "Interior vapor control for the climate zone."
3. "Air barrier continuity where posts and beams interrupt the sheathing."
4. "Flashing and sill pans at rough openings."
5. "Dense-pack cellulose density and settling."

The strings are stored exactly as written above, without the surrounding quotation marks.

## Rationale

- Reference House 001 can then show D071's unverified-climate warning with real content, so AC2b-06 can be demonstrated.
- The details name what a designer must check for the site and climate. They state no value or performance.

## Alternatives considered

- **Empty notes and lists** until sourced details exist. Simpler, but then the warning has nothing to show for the reference house.

## What this does not decide

- Any sourced property value, which stays `null` (open question 6).
- Any code, energy, or moisture-performance claim (AC-08).
- How outputs present the text (`ART-003`, `UI-004`).
