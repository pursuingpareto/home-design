# Reference House 001 — Vermont timber-frame house

**Fixture status:** version 2: VS-01 geometry ([D025](../../product/decisions/D025-reference-house-001-vs01-fixture.md)) with the VS-02 frame ([D053](../../product/decisions/D053-reference-house-001-v2-design-intent.md)). Not an engineered or code-compliant building.

- Location: Vermont, USA; jurisdiction details and site loads to be configured, not assumed.
- Two stories; **1,728 sf** (864 sf per story).
- Three bedrooms, two bathrooms (narrative program only; rooms and walls are not VS-01 entities).
- Traditional heavy timber frame: posts, beams, sills, floor joists, principal rafters with purlins, and knee braces (VS-02).
- Simple gable roof; conventional residential foundation (foundation not modeled in VS-01).
- Configurable straw bale or conventional stud-wall infill (later slices).
- Traditional joinery and modern connector options (later slices).

This is a recurring integration fixture, not the limit of the supported product.

## Accepted VS-01 dimensions

Imperial values are design intent. Canonical stored values use meters with `1 ft = 0.3048 m` ([D026](../../product/decisions/D026-canonical-units-identity-persistence.md)).

| Parameter | Intent | Canonical |
|---|---|---|
| Footprint | 36'-0" (X) × 24'-0" (Y) | `width_m` 10.9728, `depth_m` 7.3152, origin `[0, 0]`, rotation 0 |
| Bays | 3 × 2 equal 12'-0" bays | `x_lines` `x0`–`x3` at fractions `[0, 1/3, 2/3, 1]`, `y_lines` `y0`–`y2` at `[0, 0.5, 1]` ([D042](../../product/decisions/D042-stable-grid-line-ids.md)) |
| Level 0 | First floor at Z = 0, 10'-0" story height | `elevation_m` 0, `story_height_m` 3.048 |
| Level 1 | Second floor at 10'-0", 9'-0" story height to eave plate | `elevation_m` 3.048, `story_height_m` 2.7432 |
| Eave plane | 19'-0" | `z_eave` 5.7912 m |
| Roof | Gable, ridge along X, 9/12, 2'-0" eaves, centered | `ridge_axis` X, `pitch_rad` atan(0.75), `eave_overhang_m` 0.6096, `ridge_offset_m` 0 |
| Posts | 8×8 full-sawn | `actual_width_m` / `actual_depth_m` 0.2032 |
| Beams | 8×12 full-sawn; depth vertical | 0.2032 × 0.3048 |
| Material | Eastern white pine | Grade, density, and provenance unknown (`null`) |
| Member defaults | Posts 8×8, beams 8×12, both eastern white pine | `FrameSystem.member_defaults` `POST` / `BEAM` ([D039](../../product/decisions/D039-frame-member-defaults.md)) |

Z = 0 is the **first-floor reference**, not grade. Ridge height for derived roof geometry: `y = 3.6576 m`, `z = 8.5344 m`, with pitch measured on the 12'-0" wall-to-ridge run.

## Inventory

The fixture's IDs are fixed values; projects created from the template get their own IDs ([D041](../../product/decisions/D041-deterministic-id-minting.md)). Rule [`vs02-frame-1`](generation-rules.md) produces **193** members, stored as exact generator output:

| Role | Section | Count |
|---|---|---|
| Posts | 8×8 | 24 |
| Beams | 8×12 | 34 |
| Sills | 8×8 | 17 |
| Floor joists (24" on center) | 4×8 | 30 |
| Principal rafters | 8×10 | 8 |
| Purlins (2 per slope) | 6×8 | 12 |
| Knee braces (3'-0" legs, both planes) | 4×6 | 68 |

Lengths on the schedule are reference-axis lengths ([D058](../../product/decisions/D058-datum-reference-axes.md)), not fabrication cut lengths. The fixture and the packaged template are built by `uv run python -m homedesign.timber.fixture` and drift-checked in CI ([TIMBER-002](../../implementation/tasks/TIMBER-002.md) §7). The fixture holds 518 records: 13 authored records, 193 members, and **312** connections ([CONN-001](../../implementation/tasks/CONN-001.md), [D059](../../product/decisions/D059-vs02-junction-rules-connection-type-command.md)): 68 post-beam, 12 post-sill, 136 brace, 60 joist-beam, 4 rafter-peak, 8 rafter-foot, and 24 purlin-rafter, all with their D054 default types. Joints that no junction class covers, the Level 1 post splices and the sill joints at grid stations, get no record and are not counted.

Complete snapshot: [`fixture.snapshot.json`](fixture.snapshot.json). Derived `plan2d` / `mesh3d` / `timber_schedule` / `preliminary_estimate` shapes are [artifacts.md](../../architecture/artifacts.md) (D027; version 2 payloads, [D060](../../product/decisions/D060-vs02-artifact-payloads.md)). All four but the estimate carry the 193 members and 312 connections; the plan has four planes (`level-0`, `level-1`, `eave`, `roof`). Default estimate for this fixture is `UNAVAILABLE` (no price book), with ten lines: three connection types counted "each" and seven timber lines in meters.

## VS-02 design intent (in the fixture)

VS-02 adds sills, floor joists, principal rafters, purlins, and knee braces ([D052](../../product/decisions/D052-vs02-frame-members.md)), with the values in [D053](../../product/decisions/D053-reference-house-001-v2-design-intent.md). Under [D055](../../product/decisions/D055-pre-release-schema-replacement.md), the v2 fixture replaced the VS-01 fixture; older snapshots are not supported. It adds four sections (4×8, 8×10, 6×8, 4×6), the frame parameters, and the D054 connection types per junction class.

## VS-02b design intent (approved, not yet implemented)

Version 3 adds perimeter infill walls with openings ([D072](../../product/decisions/D072-reference-house-001-v3-design-intent.md), [D081](../../product/decisions/D081-reference-house-001-v3-template-text.md)), generated by [`vs02b-walls-1`](wall-rules.md) ([ASM-001](../../implementation/tasks/ASM-001.md), with [MODEL-006](../../implementation/tasks/MODEL-006.md)). Until that merge, the fixture above stays version 2.

- **Definitions:** `straw-bale` (the default: lime plaster 1½", straw bales 18", clay plaster 1"; 1½" × 18" bucks) and `stud-infill` (siding ¾", sheathing ½", 2×6 at 24" with dense-pack cellulose, gypsum board ½"; one mid-height girt; 2×8 headers; jacks above 4'-0"). Every property value is `null`.
- **Openings:** one 3'-0" × 6'-8" door centered in the middle Level 0 south bay; one 5'-0" × 4'-0" window in each outer Level 0 south bay; one 3'-0" × 4'-0" window in each of the other 17 walls. All windows have their sill at 3'-0".
- **Inventory:** 20 walls; 2,016 sf net reference wall area; 79 buck pieces with straw bale; 246 pieces with stud infill. The frame is unchanged at 193 members and 312 connections. The fixture grows from 518 records to 651.

## Still open for this house (not VS-01)

Loads, foundation details, connections, assemblies, MEP, cost data, and jurisdictional code editions. Do not invent them for engineering claims.
