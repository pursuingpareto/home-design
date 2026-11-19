# Current project status

**As of 2026-11-19:** Specification work through D050. Application code in `backend/` (the model, commands, timber generator, persistence, artifacts, geometry, estimating, and the HTTP API: `MODEL-001` through `API-001`) and `frontend/` (the browser client, `UI-001`), with shared vectors in `tests/vectors/`.

## Complete

- Product decisions D001–D050.
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
- `MODEL-001` implemented: Pydantic schema, four-stage validator, RFC 8785 canonicalization and fingerprints, committed JSON Schema, cross-language JCS vectors.
- Per-role section and material defaults on `FrameSystem` (D039), applied to the fixture, schema, validator, and tests; `SetMemberSection` changes a role default (D040).
- Deterministic UUIDv5 ID minting from the command (D041).
- Stable grid-line IDs and line-based generation keys (D042), applied to the fixture, rule, schema, validator, and tests.

## Incomplete

- Hosting, identity provider, and production operations.
- `MODEL-003` implemented: typed commands, deterministic ID minting (D041), candidate snapshots with diff, classification, no-op handling, undo, and template creation; command JSON Schema exported.
- `TIMBER-001` implemented: `vs01-post-beam-1` generator, rule registry, and stage 5 conformance (D046); inventory matches an independent ECMAScript implementation byte for byte.
- `MODEL-004` implemented: `ProjectService` over in-memory and PostgreSQL stores, with immutable revisions, optimistic concurrency, idempotent retries, an audit log, and signed preview tokens (D047).
- `ART-001` implemented: derivation registry, envelope and manifest, `artifacts` storage, derive-after-commit with lazy recompute, real `artifact_statuses`.
- `GEOM-001` implemented: `plan2d` and `mesh3d` derived for every revision (D048 roof planes), matching an independent ECMAScript implementation.
- `EST-001` implemented: `timber_schedule`, gated `preliminary_estimate` (never a fabricated total), and versioned per-project price books; all four VS-01 artifacts are derived for every revision; 383 tests passing.
- `API-001` implemented: the VS-01 HTTP API at `/api/v1` (FastAPI), with strict bodies, the error envelope, request IDs, development bearer tokens and owner-only access (D050), and a committed OpenAPI document; 436 tests passing. The three contract points found during implementation (405, 415, unknown routes) are approved (API-001 §13).
- `UI-001` implemented: the VS-01 browser client in `frontend/` (React, TypeScript, Three.js, SVG) with synchronized 2D and 3D views, footprint edits through preview and confirmation, undo, the schedule, the estimate, a price-book form, and the project list route; 439 backend, 34 frontend, and 8 browser end-to-end tests passing. VS-01's user-visible acceptance criteria are covered end to end.
- `UI-002` implemented: tabbed browser editors for every D043 command (story heights, roof applied directly with undo, a grid editor that reuses line IDs, sections per role), with cross-tab error pointers; 439 backend, 51 frontend, and 14 browser end-to-end tests passing. Every editable VS-01 parameter can now be changed in the browser.
- Engineering, assemblies, AI, collaboration, and documentation slices.
