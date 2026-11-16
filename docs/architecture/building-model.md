# Unified semantic building model — design specification

**Version:** 0.2 draft (2026-11-14)  
**Status:** Parametric semantic authority is confirmed (Decision 023); schema details below are **provisional engineering proposals**, not approved construction rules.  
**Scope:** First vertical slice (VS-01) plus explicit extension points.

## 1. Architectural invariants

1. A project revision contains an immutable, validated semantic model. A Three.js scene, CAD B-rep, mesh, drawing, and schedule are **derived artifacts**, never authoritative state.
2. Entities have persistent, opaque IDs; names and display order are not identifiers.
3. Operations target typed entities and run through one server-side validation and transaction path, whether initiated by UI, API, or future AI.
4. Every persisted quantity is dimensioned; no untyped floating-point values for lengths, areas, angles, or money.
5. All derived artifacts declare the source revision, generator version, and status.
6. Engineering approval is never inferred from a geometry or framing-generation success.
7. A reference to a deleted entity must not remain silently dangling.

## 2. Units, axes, and numeric policy (provisional)

- **Canonical geometry:** meters, right-handed Cartesian frame; +X east/right in plan, +Y north/up in plan, +Z vertically upward. Building-local origin at the southwest footprint corner at reference ground datum. Project may also carry a separate georeferenced site transform.
- **Angles:** radians in APIs and persistence; pitch may be entered as degrees or rise/run in UI.
- **Numeric encoding:** finite IEEE-754 double values at computational boundaries; validate against configured bounds and avoid comparing floats for semantic identity. Serialized JSON numeric fields must be finite. Engineering/calculation modules may use higher precision when justified.
- **Tolerance policy:** geometry adapters own numerical tolerance; initial target 1e-6 m for coordinate comparisons, subject to kernel proof-of-concept. Do **not** interpret this as construction/fabrication tolerance.
- **Displayed dimensions:** user-selectable imperial/metric, with conversion at the boundary. Material nominal sizes are labels distinct from actual dimensions.
- **Money:** integer minor currency units plus ISO 4217 currency code; never binary floating-point money.
- **Environmental metrics:** explicit quantity and scope (e.g. kgCO2e, A1–A3); unknown is not zero.

## 3. Core record contracts

All records include `id: UUID`, `kind: discriminator`, and `schema_version: positive integer`. A project snapshot contains `project_id`, `revision_id`, `parent_revision_id | null`, `created_at`, `entities`, and `model_schema_version`.

### 3.1 Entity types for VS-01

| Entity | Required fields | Relationships / invariants |
|---|---|---|
| `Building` | `id`, `name`, `footprint_id`, `level_ids[]`, `roof_id`, `frame_system_id` | Exactly one primary footprint in VS-01; references exist |
| `Footprint` | `id`, `origin_m: [x,y]`, `width_m`, `depth_m`, `rotation_rad` | Rectangle only; dimensions positive and bounded |
| `Level` | `id`, `index`, `elevation_m`, `clear_height_m` | Two ordered levels in VS-01; unique index; elevations strictly increasing |
| `GableRoof` | `id`, `ridge_axis: X|Y`, `pitch_rad`, `eave_overhang_m`, `ridge_offset_m` | Supported roof domain only; derived from footprint and upper level |
| `TimberGrid` | `id`, `x_fractions[]`, `y_fractions[]`, `generation_rule_version` | Sorted fractions from 0 to 1; endpoints present; regular grid VS-01 |
| `FrameSystem` | `id`, `grid_id`, `member_ids[]`, `generation_mode` | Member IDs reference existing `TimberMember` records |
| `TimberMember` | `id`, `member_role`, `start_m`, `end_m`, `section_id`, `material_id`, `generation_key` | Nonzero length; section/material exist; deterministic generation key |
| `Section` | `id`, `shape`, `actual_width_m`, `actual_depth_m`, `nominal_label` | Rectangular only in VS-01; actual dimensions positive |
| `Material` | `id`, `name`, `species?`, `grade?`, `density_kg_m3?`, `provenance?` | Unknown grade and properties explicitly nullable; not assumed |

`TimberMember.member_role` in VS-01: `POST`, `BEAM`, `FLOOR_JOIST` (only if generated), `RAFTER` (only if generated). Unsupported member families must not be fabricated by the generator. `start_m` and `end_m` describe the member reference axis; physical cut length can differ once connection machining is introduced. VS-01 schedules label length as **reference-axis length, not fabrication cut length**.

### 3.2 Future extension types (not VS-01 deliverables)

`Wall`, `Opening`, `AssemblyDefinition`, `AssemblyInstance`, `Layer`, `Connection`, `MEPSystem`, `MEPElement`, `LoadCase`, `AnalysisResult`, `CostDataset`, `EnvironmentalDataset`, `Approval`, `DesignAlternative`. Reserve type namespaces and IDs; do not create empty pretend engineering objects in VS-01.

## 4. Canonical snapshot

The VS-01 golden snapshot is [Reference House 001](../reference-projects/vermont-timber-house/fixture.snapshot.json) (D025). Complete snapshots must pass referential validation. Do not use abbreviated examples as fixtures.

## 5. Identity and deterministic regeneration

Generated framing uses a stable `generation_key` such as `frame/grid-x-1/grid-y-2/level-0/post`. On regeneration, preserve the ID when the semantic generation key still exists; create a new ID for new keys; retire IDs for removed keys. Never reassign a retired ID to a different member. The generated member's geometry and attributes may change without changing its ID. Explicitly distinguish user-authored and generated entities and record rule versions. A change that invalidates a generation key reports an entity removal and dependent artifact invalidation.

## 6. Validation levels

- **Syntactic:** required fields, enums, schema versions, finite numbers, UUID syntax.
- **Referential:** every referenced ID exists and is of the expected type; no duplicate IDs.
- **Geometric:** valid dimensions, roof pitch in supported domain, nonzero member axes, valid level ordering, grid fractions sorted/unique.
- **Domain:** only supported VS-01 configurations; do not assert structural adequacy or building-code compliance.
- **Authorization:** caller has rights to perform requested operation on project/revision.

Validation returns stable machine-readable codes and field paths, with human-readable messages. Failures do not create a new revision.

## 7. Revision and storage policy (provisional)

Treat revisions as immutable snapshots or reconstructible event checkpoints; initial implementation may use PostgreSQL JSONB snapshots plus an append-only operation/audit table. Transactionally persist a revision and its operation record. A revision has exactly one parent in VS-01; branching and merge semantics are deferred. Optimistic concurrency requires `base_revision_id` equal to the project's current head; conflicts return `REVISION_CONFLICT`, never silently overwrite.

## 8. Migration rules

Each record has a schema version. Persist a top-level model schema version. Migrations must be deterministic, tested with golden fixtures, and preserve stable IDs. Reject unsupported future schema versions explicitly. Do not silently discard unknown data.

## 9. VS-01 model acceptance tests

1. Complete reference-house snapshot validates and round-trips without semantic loss.
2. Negative/NaN/infinite footprint dimensions and unsupported roof geometry are rejected.
3. Missing material, section, or building reference is rejected with an actionable path.
4. Width change produces a new revision and preserves member IDs for unchanged generation keys.
5. Same snapshot + same generator version yields byte-equivalent canonical schedules after deterministic ordering.
6. Every member's endpoints lie in the expected model coordinate system; schedule totals reconcile with member inventory.
7. Invalid operation and stale base revision leave project head and stored model unchanged.

## 10. Open decisions

VS-01 reference-house dimensions, bays, sections, roof, and post/beam generation rules are confirmed ([D025](../product/decisions/D025-reference-house-001-vs01-fixture.md)). Still open: precision/tolerance with geometry kernel testing; whether framing rules are embedded or plug-in modules; storage representation after performance experiments. See [open questions](../product/open-questions.md).
