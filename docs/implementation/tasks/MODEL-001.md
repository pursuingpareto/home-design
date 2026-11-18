# MODEL-001 — Snapshot schema, validation, and canonical serialization

**Status:** Implemented (2026-11-18) — see §13 for implementation notes and limitations  
**Owner module:** `model`  
**Slice:** VS-01  
**Depends on:** none (first implementation task)  
**Unblocks:** `TIMBER-001` (generator), `MODEL-003` (typed operation engine), `MODEL-004` (revision persistence), `GEOM-001`/`EST-001` (fingerprints)

> This file merges the task index's suggested `MODEL-001` (canonical units/coordinates) and `MODEL-002` (schemas). Units alone have nothing testable to show. `MODEL-002` is left free for the next task.

## 1. Objective and user-visible behavior

Provide a pure, deterministic Python library that:

1. Parses a VS-01 semantic snapshot from JSON bytes, strictly.
2. Validates it in four stages (syntactic, referential, geometric, domain) and returns stable machine-readable issues.
3. Produces the canonical snapshot bytes (D029, D030) and `sha256:` fingerprints.
4. Exports the snapshot JSON Schema, which is committed to the repository (D028).

There is **no user-visible behavior** yet. This is the foundation that later tasks use to accept, reject, persist, and fingerprint models. It establishes the reference behavior for AC-05 (semantic equivalence on reload), AC-06 (atomic rejection with actionable errors), and AC-09 (serialization round-trips).

## 2. Inputs and governing documents

- Fixture: [`fixture.snapshot.json`](../../reference-projects/vermont-timber-house/fixture.snapshot.json) (D025, field rename D033).
- Schema and invariants: [building-model.md](../../architecture/building-model.md) §2, §3, §6, §8, §9 (tests 1–3).
- Decisions: [D026](../../product/decisions/D026-canonical-units-identity-persistence.md) units, identity, finite numbers · [D028](../../product/decisions/D028-pydantic-authoritative-schema.md) Pydantic authority, committed JSON Schema · [D029](../../product/decisions/D029-canonical-json-rfc8785.md) RFC 8785 · [D030](../../product/decisions/D030-canonical-snapshot-entity-order.md) entity order, UUID form, semantic arrays · [D031](../../product/decisions/D031-vs01-unsupported-configurations.md) unsupported configurations · [D032](../../product/decisions/D032-vs01-numeric-bounds.md) footprint, grid, and roof bounds · [D033](../../product/decisions/D033-level-story-height.md) story height · [D034](../../product/decisions/D034-vs01-level-bounds.md) level bounds.
- Error envelope: [interfaces.md](../../architecture/interfaces.md) §7.

## 3. Scope

**In scope**

- Pydantic models for the snapshot envelope, `Building`, and the eight VS-01 entity kinds (`Footprint`, `Level`, `GableRoof`, `TimberGrid`, `FrameSystem`, `TimberMember`, `Section`, `Material`). Entity records are a union discriminated by `kind`.
- A strict JSON parser front end (§5.1).
- The four-stage validator (§5.3) and the detail-code catalog (§6).
- Canonicalization and fingerprint helpers (§5.4).
- JSON Schema export with a drift test (§5.5).
- Schema-version gate: accept `model_schema_version = 1` and entity `schema_version = 1` only.
- Shared cross-language test vectors (§7.3).

**Non-goals (later tasks)**

- Checking that members match `vs01-post-beam-1`, and member generation itself → `TIMBER-001`.
- Commands, candidate snapshots, previews → `MODEL-003`.
- PostgreSQL, revisions, idempotency → `MODEL-004`.
- HTTP, OpenAPI, TypeScript generation, authorization → API task. The Authorization validation level in building-model.md §6 belongs to the API layer, not this library.
- Artifacts (`plan2d`, `mesh3d`, schedule, estimate).
- Migration framework (only one schema version exists).
- Any frontend code.

## 4. Data contracts and invariants

### 4.1 Field presence and nulls

- Every field listed in building-model.md §3.1 is a **required key**. Fields marked `?` (the nullable `Material` properties) are required keys whose value may be `null`. They are never omitted. This keeps "unknown" explicit (D026) and makes the canonical bytes reproducible.
- Unknown fields are rejected (`UNKNOWN_FIELD`), never dropped (building-model.md §8).
- The `created_at` timestamp is an RFC 3339 string in UTC with a `Z` suffix (for example `2026-11-16T00:00:00Z`); fractional seconds are allowed.

### 4.2 Numbers

- Length, angle, and fraction fields accept any finite JSON number.
- Integer fields (`schema_version`, `model_schema_version`, `Level.index`) require an integral value within ±(2⁵³ − 1). `1.0` is accepted as `1` because the two have the same canonical form (D029).
- No coercion from strings (`"3.048"` is `WRONG_TYPE`).

### 4.3 Referential rules

| Rule | Detail code |
|---|---|
| IDs unique across `building` + `entities` | `DUPLICATE_ID` |
| Every `*_id` / `*_ids` reference resolves | `DANGLING_REFERENCE` |
| …to the expected kind | `WRONG_REFERENCE_KIND` |
| No `Building` inside `entities` | `BUILDING_IN_ENTITIES` |
| Every `Footprint`, `Level`, `GableRoof`, `TimberGrid`, `FrameSystem` is referenced by `building` or by the `FrameSystem` | `UNREFERENCED_ENTITY` |
| `FrameSystem.member_ids` contains exactly the set of `TimberMember` IDs | `MEMBER_SET_MISMATCH` |
| `generation_key` unique among members | `DUPLICATE_GENERATION_KEY` |
| `Building.level_ids` in ascending `Level.index`; `member_ids` in ascending `generation_key` (D030) | `ORDER_VIOLATION` |

`Section` and `Material` records may be unreferenced. They act as a project catalog, and a future `SetMemberSection` may need spare sections. (Approved: [D038](../../product/decisions/D038-field-presence-catalog-records.md).)

## 5. Behavior

### 5.1 Strict parsing

Before any model is built, the parser rejects:

- Invalid UTF-8 or invalid JSON → `MALFORMED_JSON`.
- Duplicate object keys at any depth → `DUPLICATE_KEY` (D029, I-JSON).
- `NaN`, `Infinity`, `-Infinity` tokens, and numeric literals that overflow a double → `NON_FINITE_NUMBER`. (Python's standard `json` module accepts `NaN` by default, so this must be configured explicitly.)
- Payloads larger than a configurable limit (default **4 MiB**) or nested more deeply than **32** levels → `PAYLOAD_LIMIT_EXCEEDED`. The fixture is about 33 KB, and the largest snapshot D032 allows (7 × 7 stations, 266 members) is well under 1 MiB.

### 5.2 Paths

**Approved** ([D036](../../product/decisions/D036-error-path-syntax.md)). Path syntax is specified in [interfaces.md §7](../../architecture/interfaces.md#7-error-contract) and D036. Tests must cover each path form: identifier fields, quoted keys (via `UNKNOWN_FIELD`), entities by ID, entities by position (duplicate or malformed IDs), and array indexes.

### 5.3 Validation stages

Stages run in order (syntactic → referential → geometric → domain), and **each later stage runs only if all earlier stages passed**. Within a stage, every issue is collected and reported. The stage contents and their top-level codes are specified in [building-model.md §6](../../architecture/building-model.md#6-validation-levels) ([D035](../../product/decisions/D035-validation-stages-detail-codes.md)). For this task, stage 1 also covers the parser checks in §5.1 and the timestamp format in §4.1, and stage 4 checks `generation_rule_version = "vs01-post-beam-1"`, `generation_mode = "DETERMINISTIC_RULE"`, and member roles limited to `POST` and `BEAM`.

**Result:** `valid: bool`, `code: null | VALIDATION_FAILED | UNSUPPORTED_CONFIGURATION`, `issues[]`. Each issue has:

- `path` — the field it concerns;
- `code` — a detail code from §6;
- `message` — human-readable, not part of the contract;
- `value` — the offending value, present only when it is a finite scalar;
- `related_paths` — present only for issues that span several fields, such as a bay-length violation (footprint and grid) or a story-height mismatch (both levels).

Issues are sorted by `(path, code)` in code-unit order, so output is reproducible. `related_paths` follows [D037](../../product/decisions/D037-error-related-paths.md): entries unique, sorted, never repeating `path`, left out when empty, and assigned per the D037 mapping. Tests must cover each row of that mapping.

Validation is a pure function: no I/O, no clock, no randomness, and no dependence on the order of `entities`. **It never raises** for any input. Unexpected internal errors are a bug and must be covered by tests (§7.4).

### 5.4 Canonicalization and fingerprints

- `canonical_json(value) -> bytes` — RFC 8785 over any I-JSON value.
- `canonical_snapshot(snapshot) -> bytes` — the snapshot with `entities` sorted by `id`, then `canonical_json` (D030). It is defined only for snapshots that pass syntactic validation.
- `fingerprint(value) -> str` — `"sha256:" + lowercase hex(SHA-256(canonical_json(value)))`.

**Round-trip guarantee:** for any snapshot `S` that passes validation, `canonical_snapshot(parse(dump(S)))` equals `canonical_snapshot(S)`. For the fixture, `canonical_snapshot(parse(fixture bytes))` equals the canonical form of the raw fixture JSON with `entities` sorted by `id`. Every double survives the round trip unchanged.

### 5.5 JSON Schema export

- The snapshot JSON Schema is exported from the Pydantic models to **`docs/architecture/schemas/snapshot.v1.schema.json`**. It lives under `docs/` because it is the language-neutral contract (D024, D028).
- A test fails if the committed file differs from a fresh export, so schema changes show up in review.
- The exported schema covers stage 1 only. Stages 2–4 are documented in this file and in building-model.md, not encoded in JSON Schema (D028).

## 6. Detail-code catalog

**Approved** ([D035](../../product/decisions/D035-validation-stages-detail-codes.md)). The catalog is maintained in [building-model.md §6.1](../../architecture/building-model.md#61-detail-codes) and is not repeated here. The mutation table in §7.2 gives at least one test for each code.

## 7. Acceptance criteria and automated tests

### 7.1 Fixture

1. The fixture parses and validates with `valid: true` and zero issues.
2. The round-trip guarantee in §5.4 holds for the fixture.
3. Shuffling `entities` (several fixed seeds) yields identical canonical bytes and fingerprints (D030).
4. The fixture's canonical fingerprint is recorded as a golden value in the test suite. A change means the fixture or the canonicalization changed, and needs a decision.
5. The fixture validates against the committed JSON Schema using an independent JSON Schema validator, not Pydantic. This shows the exported schema stands on its own.

### 7.2 Mutation table

Each case applies one mutation to the fixture and asserts the exact top-level code, detail code, and path (plus `related_paths` where noted). This covers building-model.md §9 tests 2–3 and AC-06.

| # | Mutation | Expected |
|---|---|---|
| 1 | `width_m: -1` | VF · `OUT_OF_RANGE` · `entities[<footprint>].width_m` |
| 2 | `width_m: NaN` (raw token) | VF · `NON_FINITE_NUMBER` |
| 3 | `width_m: 1e400` | VF · `NON_FINITE_NUMBER` |
| 4 | `width_m: 30` | UC · `OUT_OF_SUPPORTED_RANGE` · `…width_m` |
| 5 | `width_m: 23` (bays 7.67 m) | UC · `OUT_OF_SUPPORTED_RANGE` · grid `x_lines`, related `…width_m` |
| 6 | member `section_id` → random UUID | VF · `DANGLING_REFERENCE` |
| 7 | member `section_id` → the material's ID | VF · `WRONG_REFERENCE_KIND` |
| 8 | delete `building.footprint_id` | VF · `MISSING_FIELD` · `building.footprint_id` |
| 9 | two entities share an ID | VF · `DUPLICATE_ID` |
| 10 | one ID uppercased (both the record and its references) | VF · `INVALID_UUID` |
| 11 | `x_lines` fractions out of order | VF · `NOT_STRICTLY_ASCENDING` · `…x_lines[2].fraction` |
| 12 | `y_lines` fractions `[0, 0.5]` | VF · `GRID_ENDPOINT_MISSING` |
| 13 | `model_schema_version: 2` | VF · `UNSUPPORTED_SCHEMA_VERSION` |
| 14 | extra field on `Footprint` | VF · `UNKNOWN_FIELD` |
| 15 | duplicate JSON key | VF · `DUPLICATE_KEY` |
| 16 | Level 0 `story_height_m: 3.0` | VF · `STORY_HEIGHT_MISMATCH`, related to Level 1 elevation |
| 17 | `origin_m: [1, 0]` | VF · `DATUM_MISMATCH` |
| 18 | `rotation_rad: 0.1` | UC · `UNSUPPORTED_VALUE` |
| 19 | `ridge_axis: "Y"` | UC · `UNSUPPORTED_VALUE` |
| 20 | `pitch_rad: atan(2)` / `pitch_rad: 0` | UC · `OUT_OF_SUPPORTED_RANGE` / VF · `OUT_OF_RANGE` |
| 21 | member `end_m = start_m` | VF · `ZERO_LENGTH_MEMBER` |
| 22 | one ID removed from `member_ids` | VF · `MEMBER_SET_MISMATCH` |
| 23 | two `member_ids` swapped | VF · `ORDER_VIOLATION` |
| 24 | `Building` copied into `entities` | VF · `BUILDING_IN_ENTITIES` |
| 25 | Level 1 `story_height_m` = 15' | UC · `OUT_OF_SUPPORTED_RANGE` |
| 26 | `schema_version: 9007199254740992` | VF · `INTEGER_OUT_OF_RANGE` |
| 27 | `Material.grade` key removed | VF · `MISSING_FIELD` |
| 28 | `width_m: -1` **and** `rotation_rad: 0.1` | VF only (stage gating; the domain issue is not reported) |
| 29 | `width_m` = 3.6576 − 5e-7 (lower D032 bound, inside the epsilon) | accepted |
| 30 | `width_m` = 3.6576 − 2e-6 (outside the epsilon; bays still in range) | UC · `OUT_OF_SUPPORTED_RANGE` · `…width_m` only |
| 31 | document truncated mid-object | VF · `MALFORMED_JSON` · `""` |
| 32 | input over the size limit / nested past the depth limit | VF · `PAYLOAD_LIMIT_EXCEEDED` · `""` |
| 33 | `width_m: "36"` | VF · `WRONG_TYPE` |
| 34 | `ridge_axis: "Z"` | VF · `INVALID_ENUM` |
| 35 | `created_at: "yesterday"` | VF · `INVALID_TIMESTAMP` · `created_at` |
| 36 | an entity with `kind: "Wall"` | VF · `UNKNOWN_KIND` |
| 37 | a second, unreferenced `Footprint` | VF · `UNREFERENCED_ENTITY` |
| 38 | two members given the same `generation_key` | VF · `DUPLICATE_GENERATION_KEY` |
| 39 | a third `Level` (index 2, consistent elevations and story heights, added to `level_ids`) | UC · `ENTITY_COUNT` · `building.level_ids` |
| 40 | one member's role changed to `RAFTER` | UC · `UNSUPPORTED_VALUE` |

### 7.3 Canonical JSON conformance

- Pass the RFC 8785 examples, including its number-serialization samples.
- Shared vectors at **`tests/vectors/jcs/`**: input JSON → expected canonical bytes → expected fingerprint. They must include fixture doubles (`0.6435011087932844`, `3.6575999999999995`, `0.3333333333333333`), `-0`, `1.0`, a large integer at 2⁵³ − 1, and non-ASCII strings. A later TypeScript implementation must pass the same files.

### 7.4 Robustness and determinism

- Property-based tests: arbitrary JSON values and random fixture mutations never cause an unhandled exception. The result is always `valid` or a structured failure (interfaces.md §9 test 8).
- Repeated validation of the same input returns identical result bytes, issue order included.
- The schema drift test (§5.5) passes.

## 8. Implementation guidance (not prescriptive)

- **Location:** a Python package under `backend/` (suggested `backend/src/homedesign/model/`), with tests under `backend/tests/`. Shared vectors live in the top-level `tests/vectors/`.
- **Runtime dependencies:** Pydantic v2 (D028). For JCS, use an RFC 8785 library, for example the `rfc8785` package on PyPI, or a small implementation of our own. *(Chosen: in-house; see §13.)*
  - Tradeoff: a library is less code to maintain, but it is an outside dependency.
  - An in-house implementation is roughly 100 lines, but number formatting is easy to get wrong.
  - Either way, the vectors in §7.3 are the arbiter.
  - **Do not** use the `canonicaljson` package. It implements Matrix's canonical JSON, not RFC 8785.
- **Development dependencies:** `pytest`, an independent JSON Schema validator (for example `jsonschema`), and `hypothesis` for property tests.
- Pin versions in a lockfile, and record the Python version (3.12 or later suggested) in the package metadata.
- Keep Pydantic error types internal: map them to §6 codes at the library boundary (D028).
- Use `float` for all lengths and angles. Use no `Decimal` and no unit libraries; units are carried by field names (`_m`, `_rad`), as building-model.md §1 requires.

## 9. Proposals approved by the product owner

1. ~~The detail-code catalog and the mapping from stage to top-level code.~~ **Approved: [D035](../../product/decisions/D035-validation-stages-detail-codes.md)**; building-model.md §6 updated.
2. ~~Path syntax: entities addressed by ID, with a positional fallback.~~ **Approved: [D036](../../product/decisions/D036-error-path-syntax.md)**; interfaces.md §7 updated.
3. ~~Adding the optional `related_paths` field to error details.~~ **Approved: [D037](../../product/decisions/D037-error-related-paths.md)**; interfaces.md §7 updated.
4. ~~Allowing `Section` and `Material` records to be unreferenced; all other kinds must be referenced.~~ **Approved: [D038](../../product/decisions/D038-field-presence-catalog-records.md)**; building-model.md §3 and §6 updated.
5. ~~Nullable fields are required keys that are never omitted (§4.1).~~ **Approved: [D038](../../product/decisions/D038-field-presence-catalog-records.md).**
6. ~~Parser limits of 4 MiB and nesting depth 32 (§5.1).~~ **Approved** (task-level default; the API layer may set its own request limits later).
7. ~~Committed locations: `docs/architecture/schemas/snapshot.v1.schema.json` and `tests/vectors/jcs/`.~~ **Approved.**


## 10. Error handling, security, migration

- Inputs are untrusted. Strict parsing, size and depth limits, no `eval`, and no dynamic imports keyed by `kind`.
- Messages never echo more than the offending scalar value, and never include stack traces.
- Only schema version 1 is accepted. A future version is rejected explicitly (`UNSUPPORTED_SCHEMA_VERSION`), never best-effort parsed.

## 11. Definition of done

- All tests in §7 pass in CI (or locally, if CI does not exist yet, with the command documented in `backend/README.md`).
- The JSON Schema export is committed, and the drift test passes.
- The JCS vectors are committed under `tests/vectors/jcs/`.
- building-model.md §6 and interfaces.md §7 are updated for every approved §9 item. The task index and current-status.md are updated.
- No file outside `backend/`, `tests/vectors/`, `docs/` changes.
- Changed files, tests run, limitations, and next steps are summarized (AGENTS.md).

## 12. Known adjacent issues (not fixed by this task)

- ~~building-model.md §5 example key mismatch.~~ Resolved by [D042](../../product/decisions/D042-stable-grid-line-ids.md), which replaced both the key format and the example.
- Open P1 gaps that this task does not need: section and material defaults for generated members (M1), ID minting and the retired-ID ledger (M2), positional grid keys (C4), command argument schemas (M5).

## 13. Implementation notes (2026-11-18)

**Delivered:** `backend/src/homedesign/model/` (schema, strict parser, four-stage validator, D036 paths, D037 `related_paths`, RFC 8785, fingerprints, schema export). Also `docs/architecture/schemas/snapshot.v1.schema.json` and `tests/vectors/jcs/`. Toolchain: Python 3.12 via uv, Pydantic 2.14, versions locked in `backend/uv.lock`.

**Tests:** 114 pytest tests at completion, all passing (122 after D039 added `member_defaults`, 126 after D042 added grid-line IDs):
- the fixture, round trip, entity-shuffle invariance, and golden fingerprint;
- independent JSON Schema validation and the schema drift check;
- all 40 rows of the mutation table, plus D036 path forms and D037 mapping rows;
- the JCS vectors and properties;
- never-raises properties on arbitrary values, bytes, and fixture mutations;
- the catalog-doc sync test.

A further ad hoc fuzz run of 20,000 random fixture mutations produced no exceptions.

**Choices made during implementation:**

- **JCS is implemented in-house** (`jcs.py`, about 100 lines, no dependency). Its correctness is checked against vectors produced by an ECMAScript engine (`generate.mjs`, using Node's `JSON.stringify` and UTF-16 key sorting). RFC 8785 is defined in terms of those algorithms. The engine's fingerprint for Reference House 001 matches the Python implementation byte for byte (`sha256:f0d8e036…`, 23,085 bytes).
- **Coordinates** are modeled as fixed-length JSON arrays (`minItems` = `maxItems` = 2 or 3). Pydantic's strict mode rejects JSON arrays for tuple types.
- **`Building` in the `entities` union:** `Building` is accepted at the type level so that stage 2 reports `BUILDING_IN_ENTITIES` instead of `UNKNOWN_KIND`. The exported JSON Schema therefore admits it, and stage 2 rejects it.
- **Parser problems:** duplicate keys, non-finite literals, and lone surrogates are collected along with the Pydantic errors in stage 1. A Pydantic error at a path that has already been reported is suppressed, so each problem is reported once.
- **Unlisted members:** `MEMBER_SET_MISMATCH` reports one issue for the frame system's `member_ids`, with every unlisted member in `related_paths`.
- **Duplicate level indices:** these are reported by the strict ordering check on `Building.level_ids` (`ORDER_VIOLATION`). Negative indices are `OUT_OF_RANGE` (stage 3), and indices other than exactly 0 and 1 are `UNSUPPORTED_VALUE` (stage 4).
- **Generation mode and rule version:** `FrameSystem.generation_mode` and `TimberGrid.generation_rule_version` are free strings in the schema, so an unknown value is `UNSUPPORTED_VALUE` (stage 4), not `INVALID_ENUM`.

**Later change:** [D039](../../product/decisions/D039-frame-member-defaults.md) added `FrameSystem.member_defaults` and the stage-2 code `MISSING_ROLE_DEFAULT`. The fixture, exported schema, golden fingerprint (`sha256:ab02e225…`, 23,333 bytes, still matching the ECMAScript engine), and tests were updated in the same change. [D042](../../product/decisions/D042-stable-grid-line-ids.md) then replaced `x_fractions`/`y_fractions` with `x_lines`/`y_lines` and added `INVALID_LINE_ID` (stage 1) and `DUPLICATE_LINE_ID` (stage 2); the golden fingerprint is now `sha256:588f54c4…` (23,404 bytes), again matching the ECMAScript engine.

**Limitations:**

- ~~Members are not checked against `vs01-post-beam-1`.~~ **Resolved by [TIMBER-001](TIMBER-001.md)** (stage 5 conformance, D046). That conformance check belongs to `TIMBER-001`.
- Messages are English-only and not part of the contract.
- Regenerating the JCS vectors requires Node; running the tests does not.
- No TypeScript implementation exists yet. When one is added, it must pass `tests/vectors/jcs/vectors.json`.

