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

Task status lives in the [roadmap](../roadmap.md#tasks), the single status document.

## Suggested task file format

Use one Markdown file per task (`MODEL-001.md`, etc.) containing the objective, scope, dependencies, typed contracts, acceptance criteria, tests, and definition of done. Mark each proposal **Routine** or **Your judgment** ([AGENTS.md](../../../AGENTS.md), "Collaboration workflow"). A task file must stand on its own: it is the handoff to the session that implements it.
