# Reference House 001 — Vermont timber-frame house

**Fixture status:** VS-01 geometry and framing inventory confirmed ([D025](../../product/decisions/D025-reference-house-001-vs01-fixture.md)). Not an engineered or code-compliant building.

- Location: Vermont, USA; jurisdiction details and site loads to be configured, not assumed.
- Two stories; **1,728 sf** (864 sf per story).
- Three bedrooms, two bathrooms (narrative program only; rooms and walls are not VS-01 entities).
- Traditional heavy timber post-and-beam structure; VS-01 generates posts and beams only.
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

The fixture's IDs are fixed, arbitrary values; projects created from the template get their own IDs ([D041](../../product/decisions/D041-deterministic-id-minting.md)). Rule [`vs01-post-beam-1`](generation-rules.md) produces **58** members: 24 posts and 34 beams. Lengths on the schedule are reference-axis lengths, not fabrication cut lengths.

Complete snapshot: [`fixture.snapshot.json`](fixture.snapshot.json). Derived `plan2d` / `mesh3d` / `timber_schedule` / `preliminary_estimate` shapes are [artifacts.md](../../architecture/artifacts.md) (D027). Default estimate for this fixture is `UNAVAILABLE` (no price book).

## Still open for this house (not VS-01)

Loads, foundation details, connections, assemblies, MEP, cost data, and jurisdictional code editions. Do not invent them for engineering claims.
