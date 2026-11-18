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

## 2. Units, axes, and numeric policy (confirmed, D026)

- **Canonical geometry:** meters, right-handed Cartesian frame; +X east/right in plan, +Y north/up in plan, +Z vertically upward. Building-local origin at the southwest footprint corner; Z = 0 is the first-floor reference, not grade (D025, D026; for VS-01, Level 0 elevation is exactly 0, [D034](../product/decisions/D034-vs01-level-bounds.md)). Project may also carry a separate georeferenced site transform.
- **Angles:** radians in APIs and persistence; pitch may be entered as degrees or rise/run in UI.
- **Numeric encoding:** finite IEEE-754 double values at computational boundaries; validate against configured bounds and avoid comparing floats for semantic identity. Serialized JSON numeric fields must be finite. Engineering/calculation modules may use higher precision when justified.
- **Tolerance policy:** geometry adapters own kernel-internal tolerance; published coordinate comparison epsilon is **1e-6 m** (D026). Do **not** interpret this as construction/fabrication tolerance.
- **Displayed dimensions:** user-selectable imperial/metric, with conversion at the boundary. Material nominal sizes are labels distinct from actual dimensions.
- **Money:** integer minor currency units plus ISO 4217 currency code; never binary floating-point money.
- **Environmental metrics:** explicit quantity and scope (e.g. kgCO2e, A1–A3); unknown is not zero.

## 3. Core record contracts

All records include `id: UUID`, `kind: discriminator`, and `schema_version: positive integer`. A project snapshot contains `model_schema_version`, `project_id`, `revision_id`, `parent_revision_id | null`, `created_at`, `building`, and `entities`.

- `building` is the snapshot's single `Building` record. VS-01 has exactly one building per snapshot, so this is a structural rule, not a validation check. A `Building` inside `entities` is rejected.
- `entities` holds every other entity record (the remaining rows of the table below).
- IDs are unique across `building` and `entities` combined, and references may point to records in either place.
- The order of `entities` has no semantic meaning. Hashing and comparison use the canonical snapshot (`entities` sorted by `id`, then RFC 8785). All other arrays have a semantic order, and required orders are validated, not re-sorted ([D030](../product/decisions/D030-canonical-snapshot-entity-order.md)).
- UUIDs are written as lowercase, hyphenated 8-4-4-4-12 hex; any other form is rejected ([D030](../product/decisions/D030-canonical-snapshot-entity-order.md)).
- Every field listed below is a required key. Fields marked `?` must be present and may be `null`; they are never omitted. Unknown keys are rejected ([D038](../product/decisions/D038-field-presence-catalog-records.md)).
- `Section` and `Material` records may be unreferenced (a project catalog). Every other kind must be referenced from `building` or the `FrameSystem` ([D038](../product/decisions/D038-field-presence-catalog-records.md)).

This matches the Reference House 001 fixture (D025). Supporting several buildings per project is a future schema change requiring a migration.

### 3.1 Entity types for VS-01

| Entity | Required fields | Relationships / invariants |
|---|---|---|
| `Building` | `id`, `name`, `footprint_id`, `level_ids[]`, `roof_id`, `frame_system_id` | Exactly one primary footprint in VS-01; references exist |
| `Footprint` | `id`, `origin_m: [x,y]`, `width_m`, `depth_m`, `rotation_rad` | Rectangle only; dimensions positive and bounded |
| `Level` | `id`, `index`, `elevation_m`, `story_height_m` | Two ordered levels in VS-01; unique index; elevations strictly increasing; `story_height_m` > 0 and, except on the top level, equal to the next level's elevation minus this one (1e-6 m); top level's story height locates the eave plate ([D033](../product/decisions/D033-level-story-height.md)) |
| `GableRoof` | `id`, `ridge_axis: X|Y`, `pitch_rad`, `eave_overhang_m`, `ridge_offset_m` | Supported roof domain only; derived from footprint and upper level |
| `TimberGrid` | `id`, `x_lines[]`, `y_lines[]`, `generation_rule_version` | Each line is `{id, fraction}` with a stable line ID (`x<n>` / `y<n>`, unique per axis); lines strictly ascending by fraction from 0 to 1; regular grid VS-01 ([D042](../product/decisions/D042-stable-grid-line-ids.md)) |
| `FrameSystem` | `id`, `grid_id`, `member_ids[]`, `generation_mode`, `member_defaults` | Member IDs reference existing `TimberMember` records; `member_defaults` maps each member role to `{section_id, material_id}` and must cover every role the generation rule generates ([D039](../product/decisions/D039-frame-member-defaults.md)) |
| `TimberMember` | `id`, `member_role`, `start_m`, `end_m`, `section_id`, `material_id`, `generation_key` | Nonzero length; section/material exist; deterministic generation key |
| `Section` | `id`, `shape`, `actual_width_m`, `actual_depth_m`, `nominal_label` | Rectangular only in VS-01; actual dimensions positive |
| `Material` | `id`, `name`, `species?`, `grade?`, `density_kg_m3?`, `provenance?` | Unknown grade and properties explicitly nullable; not assumed |

`TimberMember.member_role` in VS-01: `POST`, `BEAM`, `FLOOR_JOIST` (only if generated), `RAFTER` (only if generated). Unsupported member families must not be fabricated by the generator. `start_m` and `end_m` describe the member reference axis; physical cut length can differ once connection machining is introduced. VS-01 schedules label length as **reference-axis length, not fabrication cut length**.

### 3.2 Future extension types (not VS-01 deliverables)

`Wall`, `Opening`, `AssemblyDefinition`, `AssemblyInstance`, `Layer`, `Connection`, `MEPSystem`, `MEPElement`, `LoadCase`, `AnalysisResult`, `CostDataset`, `EnvironmentalDataset`, `Approval`, `DesignAlternative`. Reserve type namespaces and IDs; do not create empty pretend engineering objects in VS-01.

## 4. Canonical snapshot

The VS-01 golden snapshot is [Reference House 001](../reference-projects/vermont-timber-house/fixture.snapshot.json) (D025). Complete snapshots must pass referential validation. Do not use abbreviated examples as fixtures.

## 5. Identity and deterministic regeneration

Generated framing uses a stable `generation_key` built from stable grid-line IDs, such as `frame/x1/y2/level-0/post` ([D042](../product/decisions/D042-stable-grid-line-ids.md)). On regeneration, preserve the ID when the semantic generation key still exists; create a new ID for new keys, derived deterministically from the command ([D041](../product/decisions/D041-deterministic-id-minting.md)); retire IDs for removed keys. Never reassign a retired ID to a different member. `UndoToRevision` restores records with their original IDs, which returns each ID to the same member ([D044](../product/decisions/D044-undo-to-revision.md)). The generated member's geometry and attributes may change without changing its ID. Explicitly distinguish user-authored and generated entities and record rule versions. In VS-01 every member is generated and takes its section and material from its role's `FrameSystem.member_defaults` (D039); per-member overrides are deferred ([D040](../product/decisions/D040-setmembersection-role-default.md)). A change that invalidates a generation key reports an entity removal and dependent artifact invalidation.

## 6. Validation levels

Validation runs in five ordered stages ([D035](../product/decisions/D035-validation-stages-detail-codes.md); stage 5 added by [D046](../product/decisions/D046-conformance-validation-stage.md)). A stage runs only if every earlier stage passed; within a stage, all issues are reported. Each stage maps to one top-level error code ([interfaces.md §7](interfaces.md#7-error-contract)).

| Stage | Checks | Top-level code |
|---|---|---|
| 1 Syntactic | Required fields present, no unknown fields, types, enums, schema versions, finite numbers, canonical lowercase UUIDs (D030), integers within ±(2⁵³ − 1) (D029), no duplicate keys, timestamps | `VALIDATION_FAILED` |
| 2 Referential | Every referenced ID exists and is of the expected kind; no duplicate IDs; no `Building` in `entities`; every `Footprint`, `Level`, `GableRoof`, `TimberGrid`, and `FrameSystem` is referenced, while `Section` and `Material` may be unreferenced (D038); `FrameSystem.member_ids` is exactly the set of members; `member_defaults` references resolve and cover every role the rule generates (D039); unique generation keys; `Building.level_ids` in ascending `Level.index` and `member_ids` in ascending `generation_key` (D030) | `VALIDATION_FAILED` |
| 3 Geometric | Positive, finite dimensions; pitch in (0, π/2); overhang ≥ 0; grid line fractions strictly ascending with endpoints 0 and 1; strictly increasing level elevations; story-height consistency (D033); datums: `Footprint.origin_m = [0, 0]` (D031) and Level 0 elevation `0` (D034); nonzero member axes | `VALIDATION_FAILED` |
| 4 Domain | Supported VS-01 configurations only: D031 unsupported values; D032 and D034 bounds, checked on the full candidate snapshot (so a footprint change can be rejected for the bay lengths it produces); exactly two levels; supported generation rule and mode; member roles allowed by that rule. Never asserts structural adequacy or code compliance | `UNSUPPORTED_CONFIGURATION` |
| 5 Conformance | Members are exactly what the generation rule produces: same keys, roles, sections and materials (from `member_defaults`), and endpoints within 1e-6 m per coordinate (D046). Runs only when stages 1–4 pass | `VALIDATION_FAILED` |

Authorization (the caller's rights on the project or revision) is checked by the API layer before validation (`UNAUTHORIZED`, `FORBIDDEN`). It is not a stage of the model validator.

Validation returns stable machine-readable codes and field paths, with human-readable messages; the messages are not part of the contract. Failures do not create a new revision.

### 6.1 Detail codes

Each detail code belongs to one stage, and the stage determines its top-level code. Adding a code is backward compatible. Renaming, removing, or moving a code to another stage requires a decision (D035). Checks that span several fields report the main field as `path` and the other contributing fields as `related_paths`, using the mapping in [D037](../product/decisions/D037-error-related-paths.md).

| Detail code | Stage | Meaning |
|---|---|---|
| `MALFORMED_JSON` | 1 | Not valid UTF-8 JSON |
| `DUPLICATE_KEY` | 1 | An object key appears more than once (D029) |
| `NON_FINITE_NUMBER` | 1 | `NaN`, `Infinity`, or a literal that overflows a double (D026) |
| `PAYLOAD_LIMIT_EXCEEDED` | 1 | Input exceeds the configured size or nesting limit |
| `MISSING_FIELD` | 1 | A required key is absent |
| `UNKNOWN_FIELD` | 1 | A key not defined by the schema (never silently dropped, §8) |
| `WRONG_TYPE` | 1 | Value of the wrong JSON type; no coercion from strings |
| `INVALID_ENUM` | 1 | Value outside the schema's enumeration |
| `INVALID_UUID` | 1 | Not a lowercase, hyphenated UUID (D030) |
| `INVALID_TIMESTAMP` | 1 | Not an RFC 3339 UTC timestamp |
| `INVALID_LINE_ID` | 1 | Grid line ID is not `x<n>` in `x_lines` or `y<n>` in `y_lines` (D042) |
| `INTEGER_OUT_OF_RANGE` | 1 | Integer field non-integral or outside ±(2⁵³ − 1) (D029) |
| `UNKNOWN_KIND` | 1 | `kind` is not a VS-01 entity kind |
| `UNSUPPORTED_SCHEMA_VERSION` | 1 | `model_schema_version` or record `schema_version` is not supported |
| `DUPLICATE_ID` | 2 | Two records share an ID |
| `DANGLING_REFERENCE` | 2 | A referenced ID does not exist |
| `WRONG_REFERENCE_KIND` | 2 | A referenced ID exists but is the wrong kind |
| `BUILDING_IN_ENTITIES` | 2 | A `Building` record appears in `entities` (§3) |
| `UNREFERENCED_ENTITY` | 2 | A record that must be referenced is not |
| `MEMBER_SET_MISMATCH` | 2 | `FrameSystem.member_ids` differs from the set of `TimberMember` records |
| `DUPLICATE_GENERATION_KEY` | 2 | Two members share a `generation_key` |
| `ORDER_VIOLATION` | 2 | An array with a required order is out of order (D030) |
| `DUPLICATE_LINE_ID` | 2 | A grid line ID repeats within an axis; `path` is each later occurrence's `id`, `related_paths` the first occurrence's (D042, D037) |
| `MISSING_ROLE_DEFAULT` | 2 | `FrameSystem.member_defaults` lacks an entry for a role the generation rule generates (D039) |
| `OUT_OF_RANGE` | 3 | Physically meaningless value: non-positive length, pitch outside (0, π/2), negative overhang |
| `NOT_STRICTLY_ASCENDING` | 3 | Grid fractions or level elevations not strictly increasing |
| `GRID_ENDPOINT_MISSING` | 3 | Grid fractions do not start at 0 and end at 1 |
| `STORY_HEIGHT_MISMATCH` | 3 | A non-top level's story height differs from the elevation gap to the next level (D033) |
| `DATUM_MISMATCH` | 3 | Footprint origin is not `[0, 0]`, or Level 0 elevation is not `0` (D031, D034) |
| `ZERO_LENGTH_MEMBER` | 3 | Member axis length ≤ 1e-6 m |
| `OUT_OF_SUPPORTED_RANGE` | 4 | Well-formed value outside the VS-01 bounds (D032, D034) |
| `UNSUPPORTED_VALUE` | 4 | Well-formed value VS-01 does not handle: rotation, Y ridge, ridge offset (D031), unsupported generation rule or mode, disallowed member role |
| `ENTITY_COUNT` | 4 | Unsupported number of records of a kind, such as not exactly two levels (D034) |
| `MISSING_GENERATED_MEMBER` | 5 | The rule generates a key that no member has; `path` is the frame's `member_ids`, `value` the key (D046) |
| `UNEXPECTED_MEMBER` | 5 | A member's key is not generated by the rule; `path` is its `generation_key` (D046) |
| `MEMBER_GEOMETRY_MISMATCH` | 5 | `start_m` or `end_m` differs from the rule by more than 1e-6 m in any coordinate (D046) |
| `MEMBER_ASSIGNMENT_MISMATCH` | 5 | `member_role`, `section_id`, or `material_id` differs from the rule; for section and material, `related_paths` is the role's `member_defaults` field (D046, D037) |

## 7. Revision and storage policy (confirmed, D026)

Persist each revision as an immutable PostgreSQL JSONB snapshot plus an append-only operation/audit table. Transactionally persist a revision and its operation record. A revision has exactly one parent in VS-01; branching and merge semantics are deferred. Optimistic concurrency requires `base_revision_id` equal to the project's current head; conflicts return `REVISION_CONFLICT`, never silently overwrite.

## 8. Migration rules

Each record has a schema version. Persist a top-level model schema version. Migrations must be deterministic, tested with golden fixtures, and preserve stable IDs. Reject unsupported future schema versions explicitly. Do not silently discard unknown data.

## 9. VS-01 model acceptance tests

1. Complete reference-house snapshot validates and round-trips without semantic loss; canonical bytes before and after the round trip are identical (D029).
2. Negative/NaN/infinite footprint dimensions (`VALIDATION_FAILED`) and out-of-range or unsupported footprint, grid, and roof configurations (`UNSUPPORTED_CONFIGURATION`, D031/D032) are rejected.
3. Missing material, section, or building reference is rejected with an actionable path.
4. Width change produces a new revision and preserves member IDs for unchanged generation keys.
5. Same snapshot + same generator version yields byte-equivalent canonical schedules (RFC 8785, [D029](../product/decisions/D029-canonical-json-rfc8785.md)) after deterministic ordering.
6. Every member's endpoints lie in the expected model coordinate system; schedule totals reconcile with member inventory.
7. Invalid operation and stale base revision leave project head and stored model unchanged.

## 10. Open decisions

VS-01 reference-house geometry is confirmed ([D025](../product/decisions/D025-reference-house-001-vs01-fixture.md)). Units, axes, radians, UUIDs, JSONB snapshots, and optimistic concurrency are confirmed ([D026](../product/decisions/D026-canonical-units-identity-persistence.md)). Derived plan/mesh/schedule/estimate DTOs are confirmed ([D027](../product/decisions/D027-vs01-artifact-dtos.md)). Framing rules are plug-in modules in a registry keyed by `generation_rule_version` ([interfaces.md §1](interfaces.md#1-ownership-and-boundaries); TIMBER-001). Still open: exact geometry kernel. See [open questions](../product/open-questions.md).
