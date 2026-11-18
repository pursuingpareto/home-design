# Decision register

**Status:** Confirmed product decisions D001–D042. Numbered decisions D001–D024 are retained from the discovery conversation.

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
- D030: [Canonical snapshot form and entity ordering](D030-canonical-snapshot-entity-order.md) — `entities` order has no meaning, canonical form sorts by `id`; lowercase UUIDs; other arrays' required orders are validated, not re-sorted.
- D031: [VS-01 unsupported footprint and roof configurations](D031-vs01-unsupported-configurations.md) — rotation, Y ridge, and ridge offset rejected as `UNSUPPORTED_CONFIGURATION`; origin must be `[0, 0]`.
- D032: [VS-01 numeric bounds](D032-vs01-numeric-bounds.md) — footprint 12'–80', bays 4'–24', 2–7 stations per axis, pitch 3/12–12/12, overhang 0'–3'; supported-range limits, not structural limits.
- D033: [`Level.story_height_m` replaces `clear_height_m`](D033-level-story-height.md) — floor to next datum (next level or eave plate); lower levels must match elevation gaps; true clear height becomes a derived value later. Amends D025 terminology only.
- D034: [VS-01 level datum and story-height bounds](D034-vs01-level-bounds.md) — exactly levels 0 and 1; Level 0 at elevation 0; story heights 8'–14'; supported-range limits, not code requirements.
- D035: [Validation stages and detail-code catalog](D035-validation-stages-detail-codes.md) — syntactic → referential → geometric → domain, each stage gating the next; stages 1–3 `VALIDATION_FAILED`, stage 4 `UNSUPPORTED_CONFIGURATION`; catalog in building-model.md §6.1.
- D036: [Error detail path syntax](D036-error-path-syntax.md) — dotted fields, `["…"]` for non-identifier keys, `entities[<id>]` with an `entities[#<index>]` fallback, zero-based indexes for other arrays.
- D037: [`related_paths` on error details](D037-error-related-paths.md) — optional, sorted, left out when empty; main and related fields mapped for each check that spans fields.
- D038: [Required keys, explicit nulls, and catalog records](D038-field-presence-catalog-records.md) — nullable fields are present as `null`, never omitted; `Section`/`Material` may be unreferenced; other kinds must be referenced.
- D039: [Per-role section and material defaults on `FrameSystem`](D039-frame-member-defaults.md) — `member_defaults` maps each role to `{section_id, material_id}`; must cover every role the rule generates (`MISSING_ROLE_DEFAULT`); pre-release correction of schema v1.
- D040: [`SetMemberSection` changes a role default](D040-setmembersection-role-default.md) — sets one role's section in `member_defaults` and regenerates that role; consequential; no per-member overrides in VS-01.
- D041: [Deterministic ID minting from the command](D041-deterministic-id-minting.md) — UUIDv5 over canonical `[purpose, project, actor, command_id, creation_key]`; preview equals commit; replay is deterministic; re-added keys get new IDs.
- D042: [Stable grid-line identities and generation keys](D042-stable-grid-line-ids.md) — `x_lines`/`y_lines` of `{id, fraction}` with IDs `x<n>`/`y<n>`; keys such as `frame/x0/y1/level-0/post` and `frame/axis-x/y0/x0-x1/plane-L1/beam`; amends D025/D030/D032/D037 wording.

**Next recommended work:** Write executable task files (`MODEL-001` onward) against D025–D042. Do not reopen D001–D042 to accommodate implementation shortcuts.

See [requirements](../requirements.md) for functional implications and [architecture](../../architecture/overview.md) for provisional implementation choices.
