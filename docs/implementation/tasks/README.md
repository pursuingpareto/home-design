# Implementation task index

Each task must contain:

- **ID / title / owner module**
- **Objective and user-visible behavior**
- **Inputs and dependencies**
- **Explicit scope and non-goals**
- **Data/API contracts and invariants**
- **Implementation guidance without prescribing incidental internals**
- **Acceptance criteria and automated tests**
- **Error handling, security, and migration considerations**
- **Definition of done:** passing tests, documentation updated, review completed, no unacknowledged stale artifacts.

Suggested first tasks: `MODEL-001` canonical units/coordinates; `MODEL-002` project/level/footprint schemas; `MODEL-003` typed operation engine; `MODEL-004` revision persistence; `TIMBER-001` deterministic post/beam generator; `GEOM-001` geometry adapter; `UI-001` synchronized 2D/3D; `EST-001` member schedule; `TEST-001` reference-house integration suite. Sequence and interfaces require a focused architecture pass before parallel implementation.

## Task status

| Task | Title | Status |
|---|---|---|
| [MODEL-001](MODEL-001.md) | Snapshot schema, validation, and canonical serialization (merges the suggested MODEL-001 and MODEL-002) | Done (2026-11-18) |
| [TIMBER-001](TIMBER-001.md) | Deterministic post/beam generator and generation-rule conformance | Done (2026-11-18) |
| [MODEL-003](MODEL-003.md) | Typed commands and candidate snapshots (closes gap M5) | Done (2026-11-18) |
| [MODEL-004](MODEL-004.md) | Revision persistence, concurrency, idempotency, and previews | Done (2026-11-19) |
| [ART-001](ART-001.md) | Artifact infrastructure: derivation, storage, status, manifest | Done (2026-11-19) |
| [GEOM-001](GEOM-001.md) | `plan2d` and `mesh3d` derivations (closes C1) | Done (2026-11-19) |
| [EST-001](EST-001.md) | `timber_schedule`, `preliminary_estimate`, and price books (closes C6, M9) | Done (2026-11-19) |
| [API-001](API-001.md) | HTTP API for VS-01 (routes, errors, development authentication, owner-only access) | Done (2026-11-19) |
| [UI-001](UI-001.md) | Browser client for VS-01 (2D/3D views, footprint edits with preview, schedule, price book, history) | Done (2026-11-19) |
| [UI-002](UI-002.md) | Browser editors for story heights, roof, grid, and sections (the remaining D043 commands) | Done (2026-11-19) |
| [TEST-001](TEST-001.md) | Reference-house integration suite, traceability matrix, golden fingerprints, and CI | Done (2026-11-19) |
| [MODEL-005](MODEL-005.md) | VS-02: schema version 2 (new roles, `Connection`, frame parameters), retire version 1, frame parameter commands; merges together with TIMBER-002 | Done (2026-11-19), with TIMBER-002 |
| [TIMBER-002](TIMBER-002.md) | VS-02: `vs02-frame-1` (sills, joists, principal rafters, purlins, knee braces), Reference House 001 v2 fixture, ECMAScript oracle | Done (2026-11-19), with MODEL-005 |
| CONN-001 | VS-02: connection generation per junction class, `SetConnectionType` | Not drafted (next) |
| ART-002 | VS-02: version 2 plan, mesh, schedule, and estimate payloads; "each" price-book rows | Not drafted |
| DEP-001 | VS-02: dependency selectors and exact `impacted_artifacts` (D056) | Not drafted |
| UI-003 | VS-02: browser support for the complete frame and connections | Not drafted |
| TEST-002 | VS-02: traceability, golden scenario, and the impact property for AC2-01 to AC2-09 | Not drafted |

The remaining candidate IDs still need task files. P1 gaps that block `TIMBER-001` and `MODEL-003` are listed in MODEL-001 §12.

## Suggested task file format

Use one Markdown file per task (`MODEL-001.md`, etc.) containing the objective, scope, dependencies, typed contracts, acceptance criteria, tests, and definition of done.
