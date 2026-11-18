# Decision register

**Status:** Confirmed product decisions D001–D029. Numbered decisions D001–D024 are retained from the discovery conversation.

- D001: Hybrid 2D/3D/AI design environment.
- D002–003: Heavy timber post-and-beam is the initial structural specialty.
- D004–005: Multi-jurisdiction future; Vermont first.
- D006: Automated engineering with professional verification.
- D007: Traditional and engineered connections.
- D008: Modular assemblies, straw bale and stud-wall infill.
- D009: Balanced homeowner and builder MVP.
- D010: Two-story reference house.
- D011: Design freedom, buildability, transparency.
- D012: AI collaborator default; assistant and generative modes available.
- D013: Natural-language design intent with precise visual controls.
- D014: Cost-aware optimization and alternatives.
- D015: Environmental impact first-class.
- D016: Side-by-side alternatives first, interactive optimization later.
- D017: Role-based collaboration; real-time editing later.
- D018: Hybrid automatic/previewed dependency-aware changes.
- D019: Web-first application.
- D020: Hybrid semantic-model + external geometry technology architecture.
- D021: Vertical-slice delivery.
- D022: Suitability-first stack selection; provisional TypeScript/React/Python/PostgreSQL.
- D023: Parametric semantic definitions as the source of truth.
- D024: Tool-independent repository-based specifications.
- D025: [Reference House 001 VS-01 fixture](D025-reference-house-001-vs01-fixture.md) — 36'×24' two-story rectangle, 3×2 bays, 9/12 gable, posts and beams only.
- D026: [Canonical units, identity, snapshots, and concurrency](D026-canonical-units-identity-persistence.md) — meters, +Z up, radians, UUIDs, JSONB snapshots, optimistic concurrency.
- D027: [VS-01 derived artifact DTOs](D027-vs01-artifact-dtos.md) — plan2d, mesh3d, timber_schedule, preliminary_estimate; gated costs; preliminary suitability.
- D028: [Pydantic models as the authoritative schema definition](D028-pydantic-authoritative-schema.md) — committed JSON Schema export, OpenAPI → generated TypeScript, cross-record rules server-side only.
- D029: [Canonical JSON serialization](D029-canonical-json-rfc8785.md) — RFC 8785 (JCS) for fingerprints, command hashes, idempotency comparison, and determinism tests.

**Next recommended work:** Write executable task files (`MODEL-001` onward) against D025–D029. Do not reopen D001–D029 to accommodate implementation shortcuts.

See [requirements](../requirements.md) for functional implications and [architecture](../../architecture/overview.md) for provisional implementation choices.
