# Current project status

**As of 2026-11-18:** Specification work through D046. First application code: `MODEL-001` (snapshot schema, validation, canonical serialization) in `backend/`, with shared vectors in `tests/vectors/`. No API, persistence, or frontend yet.

## Complete

- Product decisions D001–D046.
- Architecture v0.2 drafts (entity schemas remain engineering detail, not construction rules).
- VS-01 scope and acceptance criteria.
- Reference House 001 VS-01 golden snapshot and `vs01-post-beam-1` generation rules (D025).
- Canonical meters/+Z-up/radians, UUIDs, JSONB snapshots, and optimistic concurrency (D026).
- VS-01 artifact DTOs: plan, mesh, timber schedule, gated estimate (D027).
- Pydantic models as the authoritative schema, with committed JSON Schema export and generated TypeScript clients (D028).
- RFC 8785 canonical JSON for hashing, comparison, and determinism tests (D029).
- Canonical snapshot form: `entities` sorted by `id`, lowercase UUIDs (D030).
- VS-01 rejects rotated footprints, Y-axis ridges, and offset ridges; origin fixed at `[0, 0]` (D031).
- VS-01 numeric bounds for footprint, bays, grid, pitch, and overhang (D032).
- `Level.clear_height_m` renamed to `story_height_m`, with a consistency check against elevations (D033).
- Level datum (Level 0 at elevation 0) and story-height bounds of 8'–14' (D034).
- Validation stages and detail-code catalog (D035); error path syntax (D036); `related_paths` (D037); required keys and catalog records (D038).
- `MODEL-001` implemented: Pydantic schema, four-stage validator, RFC 8785 canonicalization and fingerprints, committed JSON Schema, cross-language JCS vectors; 126 tests passing.
- Per-role section and material defaults on `FrameSystem` (D039), applied to the fixture, schema, validator, and tests; `SetMemberSection` changes a role default (D040).
- Deterministic UUIDv5 ID minting from the command (D041).
- Stable grid-line IDs and line-based generation keys (D042), applied to the fixture, rule, schema, validator, and tests.

## Incomplete

- Hosting, identity provider, and production operations.
- `MODEL-003` task file ready (all proposals approved: D043–D045; interfaces.md §2–4 and §7.1; dependencies.md §4.1). Gap M5 and all P1 gaps are closed. Implementation is blocked on `TIMBER-001`, whose task file is ready (all proposals approved; stage 5 conformance is D046).
- Task files beyond `MODEL-003`.
- Engineering, assemblies, AI, collaboration, and documentation slices.
