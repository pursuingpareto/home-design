# Current project status

**As of 2026-11-16:** Specification and fixture work only. No application code in `frontend/`, `backend/`, or `tests/`.

## Complete

- Product decisions D001–D032.
- Architecture v0.2 drafts (entity schemas remain engineering detail, not construction rules).
- VS-01 scope and acceptance criteria.
- Reference House 001 VS-01 golden snapshot and `vs01-post-beam-1` generation rules (D025).
- Canonical meters/+Z-up/radians, UUIDs, JSONB snapshots, and optimistic concurrency (D026).
- VS-01 artifact DTOs: plan, mesh, timber schedule, gated estimate (D027).
- Pydantic models as the authoritative schema, with committed JSON Schema export and generated TypeScript clients (D028).
- RFC 8785 canonical JSON for hashing, comparison, and determinism tests (D029).
- Canonical snapshot form: `entities` sorted by `id`, lowercase UUIDs (D030).
- VS-01 rejects rotated footprints, Y-axis ridges, and offset ridges; origin fixed at `[0, 0]` (D031).
- VS-01 numeric bounds for footprint, bays, grid, pitch, and overhang (D032); level-height bounds pending.

## Incomplete

- Application implementation.
- Hosting, identity provider, and production operations.
- Executable task files.
- Engineering, assemblies, AI, collaboration, and documentation slices.
