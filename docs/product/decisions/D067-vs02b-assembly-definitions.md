# D067 — VS-02b assembly definitions: layered snapshot records, fixed from the template

**Status:** Confirmed  
**Date:** 2026-11-21  
**Extended by:** [D071](D071-vs02b-thermal-moisture-values.md): the framing layer has a framing material and a fill, each with its own nullable conductivity.  
**Scope:** What a VS-02b assembly definition records, and where definitions live. Approved as proposal 4 of the [VS-02b scope proposal](../../implementation/acceptance-tests/vs-02b.md) (§9), within [D064](D064-vs02b-slice-boundary.md), with the framing layer of [D066](D066-vs02b-wall-framing.md).

## Decision

- **Content:** an `AssemblyDefinition` has:
  - a family, `STRAW_BALE` or `STUD_INFILL`, and a label unique within the project;
  - an ordered list of layers, from exterior to interior;
  - a short installation note (text, not checked);
  - a list of climate-specific details to flag as unverified (FR-05).
- **Layers:** each `Layer` has a material, a thickness, a function (for example finish, sheathing, insulation, framing), and nullable property values, each with provenance (proposal 8 of the scope proposal).
- **Framing layer** (D066):
  - stud infill: the stud section and spacing, the girt count and section, the header section, and the jack threshold width;
  - straw bale: its girt count (0) and its buck section.
- **Snapshot records,** copied from the template into each project, like `Section` and `Material`: catalog records that may be unreferenced ([D038](D038-field-presence-catalog-records.md)). The model stays the single source (principle 4), and every output names the revision whose definitions it used (principle 6).
- **Fixed in VS-02b:** the template's two definitions only. Users cannot author or edit definitions or layers yet. "Reusable" (FR-05) means reused by every wall in the project; a library shared across projects comes later.
- **Materials** are `Material` records, as for timber, with unknown properties `null` ([D025](D025-reference-house-001-vs01-fixture.md)).

## Rationale

- Definitions carry quantities, sections, and property values that users will later edit, so they belong in the authoritative model, not in a global catalog.
- Snapshot records reuse existing rules (catalog records, references, canonical form) and keep every output traceable to a revision.
- Fixed definitions keep VS-02b's command surface small; authoring needs its own validation rules.

## Alternatives considered

- **A global versioned catalog,** like `vs02-connections-1`, referenced by key: suits representational keys, not editable quantitative data.
- **User-authored definitions now:** FR-05's full intent, but it needs build-up validation rules and doubles the command surface.

## What this does not decide

Field names, detail codes, and record versions (MODEL-006). How a wall's definition is chosen (proposal 5). Property values and what is computed from them (proposal 8). The build-ups and values for Reference House 001 v3 (proposal 9).
