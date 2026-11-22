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
| `Section` | `id`, `shape`, `actual_width_m`, `actual_depth_m`, `nominal_label` | Rectangular only in VS-01; actual dimensions positive; `nominal_label` unique within the snapshot ([D049](../product/decisions/D049-unique-section-labels.md)) |
| `Material` | `id`, `name`, `species?`, `grade?`, `density_kg_m3?`, `provenance?` | Unknown grade and properties explicitly nullable; not assumed |

`TimberMember.member_role` in VS-01 was `POST` or `BEAM`; version 2 roles are listed in §3.3. Unsupported member families must not be fabricated by the generator. `start_m` and `end_m` describe the member reference axis; physical cut length can differ once connection machining is introduced. VS-01 schedules label length as **reference-axis length, not fabrication cut length**.

### 3.2 Future extension types (not VS-01 deliverables)

`Wall`, `Opening`, `AssemblyDefinition`, `AssemblyInstance`, `Layer`, `Connection`, `MEPSystem`, `MEPElement`, `LoadCase`, `AnalysisResult`, `CostDataset`, `EnvironmentalDataset`, `Approval`, `DesignAlternative`. Reserve type namespaces and IDs; do not create empty pretend engineering objects in VS-01. (`Connection` arrives in version 2, §3.3; `Wall`, `Opening`, `AssemblyDefinition`, and `Layer` in version 3, §3.4, with `Layer` an object inside its definition.)

### 3.3 Version 2 records

Approved as [MODEL-005](../implementation/tasks/MODEL-005.md) §12 items 1–2 and implemented with [TIMBER-002](../implementation/tasks/TIMBER-002.md). Version 2 **replaces** version 1 ([D055](../product/decisions/D055-pre-release-schema-replacement.md)); version 1 snapshots are rejected with `UNSUPPORTED_SCHEMA_VERSION`.

- **Model schema version:** `model_schema_version` is 2.
- **Record versions are per kind:** a kind's `schema_version` changes only when its own shape changes. In version 2, `TimberMember` and `FrameSystem` are at 2, `Connection` starts at 1, and every other kind stays at 1. Each value is still checked exactly (stage 1).
- **Member roles:** `POST`, `BEAM`, `SILL`, `FLOOR_JOIST`, `PRINCIPAL_RAFTER`, `PURLIN`, `KNEE_BRACE` ([D052](../product/decisions/D052-vs02-frame-members.md)). The reserved `RAFTER` role is removed; a common-rafter role returns only when a rule generates one.
- **`FrameSystem`** gains three required fields:
  - `parameters`: the frame generation parameters, a strict object with five required fields (MODEL-005 §5, approved as §12 item 2):

    | Field | Reference house ([D053](../product/decisions/D053-reference-house-001-v2-design-intent.md)) | Stage 3 | Stage 4 supported range (inclusive) |
    |---|---|---|---|
    | `joist_spacing_m` | 0.6096 (24") | > 0 | 0.3048–1.2192 m (12"–48") |
    | `purlins_per_slope` | 2 (integer) | ≥ 0 | 0–4 |
    | `knee_brace_leg_m` | 0.9144 (3'-0") | > 0 | 0.4572–1.2192 m (1'-6"–4'-0"), and the brace-fit rule |
    | `knee_braces_level_1` | `true` | — | — |
    | `knee_braces_eave` | `true` | — | — |

    These are supported-range limits for the generator, not structural limits (as D032). **Brace fit:** when either brace plane is enabled, `2 × knee_brace_leg_m` must not exceed the shortest bay on either axis (+1e-6 m). It is checked on the full candidate, so a grid or footprint change can be rejected for the braces it would produce. The leg maximum (4') is below the minimum story height (8', D034), so braces always fit their posts. Zero purlins, or both brace planes off, are valid; the role's `member_defaults` entry is still required (D039). A bay may have no joists if the spacing is not less than the bay;
  - `connection_ids[]`: every `Connection` record, ascending by `generation_key` (as `member_ids`, D030);
  - `connection_defaults`: maps each junction class to a connection type, covering every class the rule generates ([D054](../product/decisions/D054-vs02-connection-catalog.md); as `member_defaults`, D039/D040).
- **`Connection`** (new kind): `id`, `junction_class`, `connection_type`, `member_ids: [receiving, entering]` (exactly two `TimberMember` IDs), `location_m: [x, y, z]`, `generation_key`.
  - Junction classes: `post-beam`, `post-sill`, `brace`, `joist-beam`, `rafter-peak`, `rafter-foot`, `purlin-rafter`.
  - Types: `PEGGED_MORTISE_TENON`, `BRIDLE`, `HOUSED_DOVETAIL`, `STEEL_KNIFE_PLATE`, `JOIST_HANGER`; allowed pairs per the D054 catalog.
  - Connections are generated, like members. Their IDs are minted from `"generation/" + generation_key` (D041), so generation keys are unique across members and connections together.
  - **Generation key** ([CONN-001](../implementation/tasks/CONN-001.md) §5): the generation key is `connection/{junction_class}/{receiving member key}/{entering member key}`, so it never collides with member keys (which start with `frame/`) and survives exactly when both members survive and still meet. Connections regenerate whenever members do: a surviving key keeps its ID and its `member_ids`, a new key gets a minted ID, and a removed key is retired and never reused.
  - No capacity, fastener, or machining fields (D054).
- **Schema file:** the snapshot schema is exported as `schemas/snapshot.v2.schema.json`. The command, artifact, and OpenAPI files keep their `v1` names, which follow the API version (interfaces.md §8).


### 3.4 Version 3 records (VS-02b amendment, not yet implemented)

Approved as [MODEL-006](../implementation/tasks/MODEL-006.md) §13 (2026-11-21), with decisions [D073](../product/decisions/D073-vs02b-wall-system-record.md)–[D077](../product/decisions/D077-vs02b-definition-supported-ranges.md); to be implemented with `ASM-001`, on one branch. Version 3 **replaces** version 2 (D055); version 2 snapshots are rejected with `UNSUPPORTED_SCHEMA_VERSION`. MODEL-006 §4 has the full field tables and examples.

- **Model schema version:** `model_schema_version` is 3. `Building` moves to record version 2; the new kinds start at 1; every other kind is unchanged. The timber frame (`FrameSystem`, `TimberMember`, `Connection`, `vs02-frame-1`) is unchanged ([D066](../product/decisions/D066-vs02b-wall-framing.md)).
- **`Building.wall_system_id`** references the single **`WallSystem`** ([D073](../product/decisions/D073-vs02b-wall-system-record.md)): `generation_rule_version` (the registered wall rule, `vs02b-walls-1`), `default_assembly_definition_id` (D068), `wall_ids[]` (ascending `generation_key`), and `opening_ids[]` (ascending ID).
- **`AssemblyDefinition`** (catalog record; [D067](../product/decisions/D067-vs02b-assembly-definitions.md)): `family` (`STRAW_BALE` | `STUD_INFILL`), `label` (a slug, unique), `installation_note`, `unverified_climate_details[]`, and `layers[]`, exterior to interior.
  - **Layers are objects inside the definition** ([D074](../product/decisions/D074-vs02b-embedded-layers.md)): `name` (a slug, unique within the definition), `function` (`FINISH` | `SHEATHING` | `INSULATION` | `FRAMING`), `material_id` (the fill, on the framing layer), `thickness_m`, the three declared values, and `framing?`. Exactly one layer is `FRAMING`, and only it has `framing`.
  - **Declared values** ([D075](../product/decisions/D075-vs02b-declared-property-values.md)): `thermal_conductivity_w_m_k?`, `thermal_resistance_m2_k_w?`, `vapor_permeance_kg_pa_s_m2?`, each `{value, source, date, note?}` in SI; at most one thermal field per layer; the framing layer declares conductivities only. Unknown is `null`, never 0.
  - **Framing:** `STUD` (`framing_material_id`, `framing_thermal_conductivity_w_m_k?`, `stud_section_id`, `stud_spacing_m`, `girt_count`, `girt_section_id?`, `header_section_id`, `jack_threshold_width_m`) for stud infill; `BUCK` (`framing_material_id`, `framing_thermal_conductivity_w_m_k?`, `buck_section_id`, `girt_count` = 0) for straw bale. Kings, jacks, cripples, and rough sills take the stud section ([D076](../product/decisions/D076-vs02b-framed-opening-geometry.md)). Supported ranges: stud spacing 12"–48", girt count 0–4 ([D077](../product/decisions/D077-vs02b-definition-supported-ranges.md)).
- **`Wall`** (generated; [D065](../product/decisions/D065-vs02b-wall-placement.md)): `generation_key`, `level_id`, `start_m`, `end_m` (the lower edge in the reference plane, post axis to post axis), `height_m`, `assembly_definition_id` (equal to the default), and `framing_ids[]` (ascending `generation_key`).
- **`WallFramingPiece`** (generated, one record per piece; D066): `generation_key`, `piece_kind` (`STUD`, `GIRT`, `KING`, `JACK`, `HEADER`, `ROUGH_SILL`, `CRIPPLE`, `BUCK_JAMB`, `BUCK_HEAD`, `BUCK_SILL`), `opening_id?`, `start_m`, `end_m`, `section_id`, `material_id`. Listed by exactly one wall; no connection records.
- **`Opening`** (user-authored; [D069](../product/decisions/D069-vs02b-openings.md)): `opening_kind` (`WINDOW` | `DOOR`), `wall_id`, rough-opening `width_m` and `height_m`, `sill_height_m` (0 for a door), and `offset_m` from the wall's start post axis. No generation key; the ID is minted from the command (D041).
- **Generation keys** are unique across members, connections, walls, and wall framing together; wall and framing IDs are minted from `"generation/" + generation_key` (D041). Key formats are set by `ASM-001`.
- **Fit** (stage 4; MODEL-006 §5, D076): every framed opening lies inside its wall's reference rectangle, does not meet or lie above a knee-brace axis in its wall, and does not overlap another along the wall ([D079](../product/decisions/D079-vs02b-no-stacked-openings.md)); with stud infill, girts lie below the brace feet. Checked on the full candidate snapshot.
- **`AssemblyInstance`** stays reserved and unused.
- **Schema file:** `schemas/snapshot.v3.schema.json` replaces `snapshot.v2.schema.json`.

## 4. Canonical snapshot

The VS-01 golden snapshot is [Reference House 001](../reference-projects/vermont-timber-house/fixture.snapshot.json) (D025). Complete snapshots must pass referential validation. Do not use abbreviated examples as fixtures.

## 5. Identity and deterministic regeneration

Generated framing uses a stable `generation_key` built from stable grid-line IDs, such as `frame/x1/y2/level-0/post` ([D042](../product/decisions/D042-stable-grid-line-ids.md)). On regeneration, preserve the ID when the semantic generation key still exists; create a new ID for new keys, derived deterministically from the command ([D041](../product/decisions/D041-deterministic-id-minting.md)); retire IDs for removed keys. Never reassign a retired ID to a different member. `UndoToRevision` restores records with their original IDs, which returns each ID to the same member ([D044](../product/decisions/D044-undo-to-revision.md)). The generated member's geometry and attributes may change without changing its ID. Explicitly distinguish user-authored and generated entities and record rule versions. In VS-01 every member is generated and takes its section and material from its role's `FrameSystem.member_defaults` (D039); per-member overrides are deferred ([D040](../product/decisions/D040-setmembersection-role-default.md)). A change that invalidates a generation key reports an entity removal and dependent artifact invalidation.

## 6. Validation levels

Validation runs in five ordered stages ([D035](../product/decisions/D035-validation-stages-detail-codes.md); stage 5 added by [D046](../product/decisions/D046-conformance-validation-stage.md)). A stage runs only if every earlier stage passed; within a stage, all issues are reported. Each stage maps to one top-level error code ([interfaces.md §7](interfaces.md#7-error-contract)).

| Stage | Checks | Top-level code |
|---|---|---|
| 1 Syntactic | Required fields present, no unknown fields, types, enums, schema versions, finite numbers, canonical lowercase UUIDs (D030), integers within ±(2⁵³ − 1) (D029), no duplicate keys, timestamps | `VALIDATION_FAILED` |
| 2 Referential | Every referenced ID exists and is of the expected kind; no duplicate IDs; no `Building` in `entities`; every `Footprint`, `Level`, `GableRoof`, `TimberGrid`, and `FrameSystem` is referenced, while `Section` and `Material` may be unreferenced (D038); `FrameSystem.member_ids` is exactly the set of members; `member_defaults` references resolve and cover every role the rule generates (D039); unique generation keys; unique section labels (D049); `Building.level_ids` in ascending `Level.index` and `member_ids` in ascending `generation_key` (D030). *Version 2:* each `Connection` references two distinct `TimberMember` records; `FrameSystem.connection_ids` is exactly the set of connections, in ascending `generation_key`; `connection_defaults` covers every junction class the rule generates; generation keys are unique across members and connections together (§3.3). *Version 3 (not yet implemented):* the `WallSystem` is referenced by the building and lists exactly the walls and openings; each wall lists its framing pieces, and every piece belongs to exactly one wall; unique definition labels and layer names; keys unique across all four generated kinds (§3.4) | `VALIDATION_FAILED` |
| 3 Geometric | Positive, finite dimensions; pitch in (0, π/2); overhang ≥ 0; grid line fractions strictly ascending with endpoints 0 and 1; strictly increasing level elevations; story-height consistency (D033); datums: `Footprint.origin_m = [0, 0]` (D031) and Level 0 elevation `0` (D034); nonzero member axes. *Version 2:* joist spacing and brace leg > 0, purlins per slope ≥ 0 (§3.3) | `VALIDATION_FAILED` |
| 4 Domain | Supported VS-01 configurations only: D031 unsupported values; D032 and D034 bounds, checked on the full candidate snapshot (so a footprint change can be rejected for the bay lengths it produces); exactly two levels; supported generation rule and mode; member roles allowed by that rule. *Version 2:* frame parameter bounds and the brace-fit rule; every `connection_defaults` entry and `Connection.connection_type` is allowed for its junction class by the D054 catalog (§3.3). *Version 3 (not yet implemented):* one framing layer per definition, matching its family; definition supported ranges (D077); door sills at 0; the framed-opening and girt fits (§3.4, D076); a registered wall rule. Never asserts structural adequacy or code compliance | `UNSUPPORTED_CONFIGURATION` |
| 5 Conformance | Members are exactly what the generation rule produces: same keys, roles, sections and materials (from `member_defaults`), and endpoints within 1e-6 m per coordinate (D046). *Version 2:* connections are exactly what the rule produces: same keys, junction classes, members, and types (from `connection_defaults`), and locations within 1e-6 m per coordinate. *Version 3 (not yet implemented):* walls and wall framing are exactly what the wall rule produces, compared after members and connections conform. Runs only when stages 1–4 pass | `VALIDATION_FAILED` |

Authorization (the caller's rights on the project or revision) is checked by the API layer before validation (`UNAUTHORIZED`, `FORBIDDEN`). It is not a stage of the model validator.

Validation returns stable machine-readable codes and field paths, with human-readable messages; the messages are not part of the contract. Failures do not create a new revision.

### 6.1 Detail codes

Rows marked *Version 2* come from [MODEL-005](../implementation/tasks/MODEL-005.md) §12 item 3. The connection conformance codes are reachable from fixture mutations since `vs02-frame-1` generates connections ([CONN-001](../implementation/tasks/CONN-001.md)).

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
| `UNKNOWN_KIND` | 1 | `kind` is not a VS-01 entity kind (*version 2:* not a version 2 kind; `Connection` is known) |
| `UNSUPPORTED_SCHEMA_VERSION` | 1 | `model_schema_version` or record `schema_version` is not supported |
| `DUPLICATE_ID` | 2 | Two records share an ID |
| `DANGLING_REFERENCE` | 2 | A referenced ID does not exist |
| `WRONG_REFERENCE_KIND` | 2 | A referenced ID exists but is the wrong kind |
| `BUILDING_IN_ENTITIES` | 2 | A `Building` record appears in `entities` (§3) |
| `UNREFERENCED_ENTITY` | 2 | A record that must be referenced is not |
| `MEMBER_SET_MISMATCH` | 2 | `FrameSystem.member_ids` differs from the set of `TimberMember` records |
| `DUPLICATE_GENERATION_KEY` | 2 | Two members share a `generation_key`. *Version 2:* the scope is members and connections together, because IDs are minted from keys (D041); `path` is the later record's key, `related_paths` the first's |
| `ORDER_VIOLATION` | 2 | An array with a required order is out of order (D030) |
| `DUPLICATE_LINE_ID` | 2 | A grid line ID repeats within an axis; `path` is each later occurrence's `id`, `related_paths` the first occurrence's (D042, D037) |
| `DUPLICATE_SECTION_LABEL` | 2 | Two sections share a `nominal_label`; `path` is each later section's label (by `id` order), `related_paths` the first's (D049, D037) |
| `DUPLICATE_PRICE_KEY` | 2 | A price-book row key repeats; `path` is the later row's `key`, `related_paths` the first's (price-book validation, EST-001) |
| `PRICE_UNIT_MISMATCH` | 2 | A price-book row's `unit` does not match its key family: `timber.` keys need `m`, `connection.` keys need `each`; `path` is the row's `unit`, `related_paths` its `key`, `value` the unit (price-book validation, [ART-002](../implementation/tasks/ART-002.md) §7.3) |
| `MISSING_ROLE_DEFAULT` | 2 | `FrameSystem.member_defaults` lacks an entry for a role the generation rule generates (D039) |
| `SELF_CONNECTION` | 2 | *Version 2.* A `Connection` lists the same member twice; `path` is `member_ids[1]`, `related_paths` `member_ids[0]` |
| `CONNECTION_SET_MISMATCH` | 2 | *Version 2.* `FrameSystem.connection_ids` differs from the set of `Connection` records |
| `MISSING_CONNECTION_DEFAULT` | 2 | *Version 2.* `FrameSystem.connection_defaults` lacks an entry for a junction class the rule generates; `value` names the class (D054) |
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
| `MISSING_GENERATED_CONNECTION` | 5 | *Version 2.* The rule generates a connection key that no record has; `path` is the frame's `connection_ids`, `value` the key |
| `UNEXPECTED_CONNECTION` | 5 | *Version 2.* A connection's key is not generated by the rule; `path` is its `generation_key` |
| `CONNECTION_GEOMETRY_MISMATCH` | 5 | *Version 2.* `location_m` differs from the rule by more than 1e-6 m in any coordinate |
| `CONNECTION_ASSIGNMENT_MISMATCH` | 5 | *Version 2.* `junction_class`, `member_ids`, or `connection_type` differs from the rule; for `connection_type`, `related_paths` is the class's `connection_defaults` field (D037) |


**Version 3 codes** (approved as [MODEL-006](../implementation/tasks/MODEL-006.md) §13 item 9, not yet implemented; they join the table above with the implementation, which a test keeps equal to `codes.py`):

- stage 1: `INVALID_SLUG`, `INVALID_DATE`;
- stage 2: `WALL_SET_MISMATCH`, `OPENING_SET_MISMATCH`, `FRAMING_SET_MISMATCH`, `DUPLICATE_ASSEMBLY_LABEL`, `DUPLICATE_LAYER_NAME`;
- stage 4: `FRAMING_LAYER_COUNT`, `OPENING_OUTSIDE_WALL`, `OPENING_CROSSES_BRACE`, `OPENINGS_OVERLAP`, `GIRT_CROSSES_BRACE`;
- stage 5: `MISSING_GENERATED_WALL`, `UNEXPECTED_WALL`, `WALL_GEOMETRY_MISMATCH`, `WALL_ASSIGNMENT_MISMATCH`, `MISSING_GENERATED_FRAMING`, `UNEXPECTED_FRAMING`, `FRAMING_GEOMETRY_MISMATCH`, `FRAMING_ASSIGNMENT_MISMATCH`;
- widened: `DUPLICATE_GENERATION_KEY` (all four generated kinds) and `ZERO_LENGTH_MEMBER` (wall framing pieces and walls).

Paths and related paths are in MODEL-006 §5.2 and §6.

## 7. Revision and storage policy (confirmed, D026)

Persist each revision as an immutable PostgreSQL JSONB snapshot plus an append-only operation/audit table. Transactionally persist a revision and its operation record. A revision has exactly one parent in VS-01; branching and merge semantics are deferred. Optimistic concurrency requires `base_revision_id` equal to the project's current head; conflicts return `REVISION_CONFLICT`, never silently overwrite.

Storage schema ([MODEL-004](../implementation/tasks/MODEL-004.md) §5, approved as §10 item 4):

- **`projects`** holds the head revision and its `head_sequence`. Only these head fields ever change.
- **`revisions`** holds `project_id`, `parent_revision_id`, and a per-project `sequence` starting at 1 (unique, for readable positions and ordered history). It also holds `model_schema_version`, the snapshot as **JSONB**, and its canonical **fingerprint**, which is checked on every read.
- **`operations`** is the append-only audit log, with one row per commit attempt, ordered by an identity column `log_position`.
- **`artifacts`** holds derived data, keyed by (`revision_id`, `artifact_type`, `input_fingerprint`) ([ART-001](../implementation/tasks/ART-001.md) §5, approved as §8 item 2). Each row stores the generator ID and version, status (`CURRENT`, `UNAVAILABLE`, or `FAILED`), payload, error, warnings, and generation time. Rows are recomputable and may be deleted; they are **not** append-only. A write for an existing key keeps the first row, because results are deterministic. An index on (`project_id`, `artifact_type`, `input_fingerprint`) serves reuse: a revision copies a stored row of another revision of the same project when the fingerprints match ([DEP-001](../implementation/tasks/DEP-001.md) §7).
- **`schema_migrations`** records applied SQL migrations.
- **Idempotency** is enforced by partial unique indexes: (`project_id`, `actor_id`, `command_id`) for committed or no-op rows, and (`actor_id`, `command_id`) for project creation.
- **Immutability:** triggers reject `UPDATE` and `DELETE` on `revisions` and `operations`.
- **Numbers:** JSONB keeps each number as the exact decimal Python writes (shortest round-trip form), so doubles read back bit-identical. `-0` reads back as `0`, which RFC 8785 already treats as equal (D029).

## 8. Migration rules

Each record has a schema version. Persist a top-level model schema version. Migrations must be deterministic, tested with golden fixtures, and preserve stable IDs. Reject unsupported future schema versions explicitly. Do not silently discard unknown data.

**Pre-release exception ([D055](../product/decisions/D055-pre-release-schema-replacement.md); [MODEL-005](../implementation/tasks/MODEL-005.md) §8, approved as §12 item 5):** version 2 replaces version 1 with no migration.

- **One rule:** `vs01-post-beam-1` is deleted, and `vs02-frame-1` is the only registered rule. The supported-range constants live in `model/limits.py` (formerly `model/vs01.py`).
- **One fixture:** the fixture and the packaged template become Reference House 001 v2. The v1 fixture is removed from the tree and kept only in git history.
- **Stored-data guard:** the migration runner refuses a database that holds any revision with `model_schema_version` below 2. It names the database and the fix, and deletes nothing.
- **Reset:** `scripts/dev.sh --reset` drops, recreates, and migrates the local development database. The test database is already recreated on every run.

**Version 3 (VS-02b amendment, not yet implemented; [MODEL-006](../implementation/tasks/MODEL-006.md) §9):** version 3 replaces version 2 the same way. The fixture and template become Reference House 001 v3 (`ASM-001`); the guard, which refuses any revision below the current model schema version, now refuses version 2 databases; `scripts/dev.sh --reset` is the fix.

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
