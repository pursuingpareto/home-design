# Interfaces and contracts — design specification

**Version:** 0.2 draft · **Status:** Proposed API contracts for VS-01; subject to implementation review.

## 1. Ownership and boundaries

- `project`: identity, authorization, current head, revision persistence.
- `model`: schema, typed operations, candidate snapshots, validation.
- `timber`: deterministic member generation and stable generation keys.
- `geometry`: derive 2D/3D render data from semantic snapshots; never mutate authoritative model.
- `dependencies`: preview impacted outputs, invalidate, schedule, and track artifact freshness.
- `estimating`: preliminary quantities and cost using explicit dated price inputs.
- `ai` (future): produces typed proposed operations; has no direct persistence access.

No module may write another module's private tables. Cross-module communication uses typed calls or durable events; one application-level command handler owns transactions.

## 2. Command envelope

```json
{
  "command_id": "b8f9d645-5a10-4eb5-b2ca-38ce46e5d4aa",
  "project_id": "b9531a91-9f14-49b9-8b1e-7eac1960c770",
  "base_revision_id": "ab4c88f3-f5e9-47dd-8ee0-4c7a19a0b6cf",
  "type": "SetFootprintDimensions",
  "args": {"width_m": 13, "depth_m": 9}
}
```

Actor identity is derived from authenticated server context, not trusted from the client body. `command_id` is an idempotency key scoped to project and actor. A repeated key with a different payload (compared in canonical form, [D029](../product/decisions/D029-canonical-json-rfc8785.md)) returns `IDEMPOTENCY_CONFLICT`.

VS-01 command set: `CreateReferenceProject`, `SetFootprintDimensions`, `SetLevelElevations`, `SetGableRoofParameters`, `SetTimberGrid`, `SetMemberSection` (only where supported), and `UndoToRevision` (if implemented; otherwise explicitly deferred). Commands use full typed arguments, not generic JSON patch paths.

## 3. Preview contract

`POST /api/v1/projects/{project_id}/commands/preview`

Request: command envelope. Response (illustrative):

```json
{
  "preview_id": "c5325c6c-2b62-4f45-87ab-7b289f1a4fbb",
  "base_revision_id": "ab4c88f3-f5e9-47dd-8ee0-4c7a19a0b6cf",
  "command_hash": "sha256:...",
  "confirmation_required": true,
  "changes": [{"entity_kind":"Footprint", "entity_id":"9b19e6a8-77a6-43e6-b6bd-9bd5a1167d3d", "field":"width_m", "before":12, "after":13}],
  "impacted_artifacts": ["plan2d", "mesh3d", "timber_schedule", "preliminary_estimate"],
  "warnings": ["Structural adequacy has not been assessed"],
  "expires_at": "2026-11-14T18:00:00Z"
}
```

The preview does not modify project head or create a revision. `command_hash` is SHA-256 over the RFC 8785 canonical serialization ([D029](../product/decisions/D029-canonical-json-rfc8785.md)) of the command and base revision. `expires_at` is server-issued, not client-chosen.

## 4. Commit contract

`POST /api/v1/projects/{project_id}/commands/commit`

Body: `{ "command": <command envelope>, "preview_id": "..." }` for consequential edits; routine edits may omit preview only if server policy allows. Server revalidates all preconditions and commits atomically.

Success: HTTP 201 with `{ "revision_id": "...", "parent_revision_id": "...", "operation_id": "...", "artifact_statuses": {...} }`. Idempotent retry returns the same committed revision (HTTP 200 or 201, consistently documented). A successful commit does **not** imply all derived artifacts are ready.

## 5. Read endpoints

| Method/path | Purpose |
|---|---|
| `POST /api/v1/projects` | Create reference project |
| `GET /api/v1/projects/{id}` | Metadata, permissions, head revision |
| `GET /api/v1/projects/{id}/revisions/{rev}` | Immutable semantic snapshot |
| `GET /api/v1/projects/{id}/artifacts?revision_id=...` | Artifact status manifest |
| `GET /api/v1/projects/{id}/artifacts/{type}?revision_id=...` | Derived 2D, 3D, schedule, or estimate |
| `GET /api/v1/projects/{id}/revisions` | Ordered revision history |

Artifact envelopes, payloads, and HTTP status mapping are specified in [artifacts.md](artifacts.md) (D027). `{type}` is one of `plan2d`, `mesh3d`, `timber_schedule`, `preliminary_estimate`. Return 202 while computing; do not serve stale data as current. Browser 2D/3D views must consume derived data tagged to the same revision.

## 6. Typed module-level interfaces (Python-like pseudocode)

```python
class ModelService(Protocol):
    def validate(self, snapshot: BuildingSnapshot) -> ValidationResult: ...
    def propose(self, snapshot: BuildingSnapshot, command: ModelCommand) -> CandidateChange: ...

class TimberGenerator(Protocol):
    def generate(self, snapshot: BuildingSnapshot, previous: MemberInventory | None) -> MemberInventory: ...

class DependencyService(Protocol):
    def impacts(self, changed_keys: set[str]) -> ImpactReport: ...
    def invalidate(self, revision_id: UUID, impacted: ImpactReport) -> None: ...

class GeometryAdapter(Protocol):
    def derive_plan(self, snapshot: BuildingSnapshot) -> Artifact: ...
    def derive_mesh(self, snapshot: BuildingSnapshot) -> Artifact: ...

class ScheduleService(Protocol):
    def timber_schedule(self, inventory: MemberInventory) -> Artifact: ...
```

Interfaces are illustrative. Schema definition is confirmed by [D028](../product/decisions/D028-pydantic-authoritative-schema.md): Pydantic models are authoritative, JSON Schema for the snapshot is exported and committed, and the OpenAPI generated from the same models produces the TypeScript clients. Cross-record and domain validation runs only on the server; the frontend does not duplicate it.

## 7. Error contract

```json
{
  "error": {
    "code": "VALIDATION_FAILED",
    "message": "Footprint width must be greater than zero",
    "details": [{"path":"args.width_m", "code":"OUT_OF_RANGE", "value":-1}],
    "request_id": "..."
  }
}
```

Stable codes: `VALIDATION_FAILED` (422), `UNSUPPORTED_CONFIGURATION` (422), `UNAUTHORIZED` (401), `FORBIDDEN` (403), `NOT_FOUND` (404), `REVISION_CONFLICT` (409), `IDEMPOTENCY_CONFLICT` (409), `PREVIEW_EXPIRED` (409), `DERIVATION_FAILED` (500/503 as appropriate). No internal stack traces in API responses.

Detail `code` values for model validation are cataloged in [building-model.md §6.1](building-model.md#61-detail-codes); each belongs to one validation stage, which determines whether the top-level code is `VALIDATION_FAILED` or `UNSUPPORTED_CONFIGURATION` ([D035](../product/decisions/D035-validation-stages-detail-codes.md)).

Detail `path` syntax ([D036](../product/decisions/D036-error-path-syntax.md)): paths start at the root of the validated document (`""` is the whole document). Fields are joined with `.` (`args.width_m`, `building.footprint_id`), and keys that are not identifiers use `["…"]`. Snapshot entities are addressed by ID (`entities[<id>].width_m`), or by position (`entities[#12]`) when the ID is missing, malformed, or duplicated. Other arrays use zero-based indexes (`x_fractions[2]`).

A detail may include an optional `related_paths` array listing other fields that contribute to the issue, such as the footprint width behind a bay-length violation. Entries are unique, sorted, and never repeat `path`, and the array is left out when empty ([D037](../product/decisions/D037-error-related-paths.md)). Each detail is `{"path", "code", "value"?, "related_paths"?}`; `message` text on the envelope is human-readable and not part of the contract.

## 8. Concurrency, security, and compatibility

- Every read/write is project-scoped and authorization-checked on server.
- Use optimistic concurrency on project head (D026) and a transactional outbox for derivation jobs.
- Never accept arbitrary executable expressions, geometry scripts, or SQL from AI/client as commands.
- API version prefix `/api/v1`; model schema versions independent of API version.
- Schema changes require backward-compatible readers or explicit migrations, contract tests, and fixture upgrades.
- Audit record includes actor, command, previous/new revision, timestamp, and result; protect sensitive project content.

## 9. Contract test matrix

1. OpenAPI validates example requests/responses; generated TS client compiles.
2. Valid preview has no database side effects.
3. Confirmed commit changes project head exactly once.
4. Two concurrent commits against one base revision yield exactly one winner; loser receives 409.
5. Idempotent retry does not duplicate revisions or derivation jobs.
6. Unauthorized project access cannot read snapshots or artifacts.
7. Derived plan, mesh, and schedule all identify matching source revision.
8. Unsupported geometry returns structured error, never an unhandled exception or invented output.

## 10. Deferred contracts

Professional approval signatures, alternative branches/merges, IFC export, engineering load cases, natural-language proposals, multi-user live editing, and detailed connection machining are not VS-01 endpoints. Add them via separate versioned design documents.
