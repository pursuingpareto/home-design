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

The remaining candidate IDs still need task files. P1 gaps that block `TIMBER-001` and `MODEL-003` are listed in MODEL-001 §12.

## Suggested task file format

Use one Markdown file per task (`MODEL-001.md`, etc.) containing the objective, scope, dependencies, typed contracts, acceptance criteria, tests, and definition of done.
