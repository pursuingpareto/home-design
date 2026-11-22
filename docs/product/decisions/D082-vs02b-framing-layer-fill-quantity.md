# D082 — VS-02b framing-layer fill: quantified net of framing, priced per square meter

**Status:** Confirmed (to be implemented in VS-02b, [ART-003](../../implementation/tasks/ART-003.md))  
**Date:** 2026-11-22  
**Scope:** How the assembly schedule and the estimate quantify the fill of a definition's framing layer (the straw bales, or the dense-pack cellulose between studs). Approved as [ART-003](../../implementation/tasks/ART-003.md) §12 item 1, answering the question [MODEL-006](../../implementation/tasks/MODEL-006.md) §13 left to ART-003 ("Noted for later task files").  
**Refines:** [D070](D070-vs02b-quantities-and-outputs.md), which quantifies "the framing layer … by its pieces", read with [D071](D071-vs02b-thermal-moisture-values.md), which makes the bales and the cellulose that layer's fill.

## Problem

Under D070 and D071 read together, the fill had no area, no volume, and no estimate line, although it is each wall's main material.

## Decision

- **The fill is quantified net of framing:** per wall, its area is the wall's net reference area less the face area of the wall's framing pieces (the face area of D071's framing fraction, with girt crossings counted once). Its volume is that area times the framing layer's thickness.
- **Aggregated and priced like the other layers:** a `layer_aggregates` row for the framing layer, and an estimate line `assembly.<label>.<layer>`, priced per square meter (`m2`) of that area. The line carries the fill's material name, because the stud infill framing layer is named `framing`.
- **The framing pieces stay quantified by their pieces** (`wallframing.` lines, D070).
- **An assumption line says so** (`FILL_NET_OF_FRAMING`): the fill is quantified as each wall's net area less its framing's face area, and bale counts are not given.
- **Reference House 001 v3:** 183.81 m² and 84.04 m³ of bales with the straw bale default (1.9% under the net area); with stud infill, 167.14 m² and 23.35 m³ of cellulose (10.8% under).

## Rationale

- The bales and the cellulose are priced and ordered by quantity; leaving them out would leave the straw bale wall's main cost unpriced.
- Deducting the framing's face area gives the fill the generated framing actually displaces, from the same pieces D071 already uses.

## Alternatives considered

- **The full net area,** like every other layer: simpler, one area for every line of a definition, but it overstates the fill by the framing fraction.
- **No fill quantity,** with an assumption line saying so: D070 read literally.

## What this does not decide

Bale counts (still not counted, D070). Any price or density value (open question 6). Nothing here is a takeoff for ordering or a cost quotation (AC-08, FR-10).
