# D070 — VS-02b quantities and outputs: reference areas, an assembly schedule, framing per piece

**Status:** Confirmed  
**Refined by:** [D082](D082-vs02b-framing-layer-fill-quantity.md): the framing layer's fill is quantified net of framing and priced per m².  
**Date:** 2026-11-21  
**Scope:** How VS-02b measures wall quantities, which artifact reports them, how the views show walls, and how the estimate prices them. Approved as proposal 7 of the [VS-02b scope proposal](../../implementation/acceptance-tests/vs-02b.md) (§12), as revised for [D066](D066-vs02b-wall-framing.md) and [D069](D069-vs02b-openings.md).  
**Implemented:** [ART-003](../../implementation/tasks/ART-003.md) (2026-11-22).  
**Amends:** [D027](D027-vs01-artifact-dtos.md) and artifacts.md §1 and §3 (a fifth artifact type; the manifest's "all four" becomes five), and artifacts.md §8.2 (price-book units gain `m2`).

## Decision

- **Reference area:** a wall's gross area is its bay length between grid stations times its story height between datums. Rough-opening areas are subtracted to give its net area. It is a **reference area, not an installed area**: member faces, braces, and the framing around openings are not deducted. The output says so.
- **Layer quantities:** each non-framing layer's area is the wall's net area, and its volume is that area times the layer's thickness. The framing layer is quantified by its pieces.
- **Wall framing quantities:** one row per piece (D066), with its key, wall, kind (stud, girt, king, jack, header, rough sill, cripple, buck jamb, buck head, buck sill), section, and reference-axis length. Aggregates give the **count and total length per kind and section**.
- **A new artifact, `assembly_schedule`,** owned by the `assemblies` module:
  - one row per wall: key, story, elevation side, definition, and gross, opening, and net areas;
  - one row per opening: kind, rough-opening size, wall, and whether it has jacks;
  - one row per wall framing piece;
  - aggregates: area per definition; area and volume per definition and non-framing layer; framing count and length per kind and section; opening counts per kind;
  - its assumptions, and the property figures of proposal 8.

  The timber schedule stays about the heavy-timber frame.
- **Views:** `plan2d` shows each wall as an outline of its total thickness on its story's plane, with gaps at openings, and wall framing in plan. `mesh3d` shows wall layers as boxes with rectangular voids, and each wall framing piece as a box of its section. Both tag wall layers and wall framing separately, for D066's two switches. New payload fields and a new generator version.
- **Estimate:**
  - one line per definition and non-framing layer, key `assembly.<label>.<layer>`, priced per square meter of net area (unit `m2`);
  - one line per framing kind and section, key `wallframing.<kind>.<section label>`, priced per meter of reference-axis length (unit `m`), with counts shown beside the lengths;
  - the price book's units gain `m2`; `PRICE_UNIT_MISMATCH` covers an `assembly.` key without `m2` and a `wallframing.` key without `m`. Unpriced lines stay unpriced, never 0.
- **Openings are not priced** in VS-02b: windows and doors are products, and no product data exists. An assumption line says so.
- **Not counted:** bale counts, plates, let-in notches, and fastenings. Assumption lines say so.

## Rationale

- Reference areas and reference-axis lengths keep quantities independent of member sections, as for the frame.
- A separate artifact keeps each module's output its own and makes impact exact: a wall edit need not touch the timber schedule.
- Per-piece rows with per-meter pricing give the builder a takeoff without implying precut lengths that the model does not know.

## Alternatives considered

- **Clear area between member faces:** depends on member sections.
- **Walls and wall framing in `timber_schedule`.**
- **Wall framing priced per piece** (`each`): lengths are reference-axis lengths, so a per-piece price would hide length differences.
- **Price per definition** (one line per square meter of assembly).

## What this does not decide

Payload field names, generator IDs and versions, selectors, and exact ordering (ART-003). Property figures (proposal 8). Budgets for the new payloads beyond D063's ceilings (proposal 15). Nothing here is a construction document or a cost quotation (AC-08, FR-10).
