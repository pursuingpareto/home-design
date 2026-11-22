# Roadmap and status

The single status document for the project ([AGENTS.md](../../AGENTS.md), "Documentation maintenance"). Update it whenever a task's status changes. Decisions are in the [decision register](../product/decisions/README.md); each task file holds its own implementation notes.

**As of 2026-11-21:** VS-01 and VS-02 are complete. VS-02 delivered model schema version 2, the complete Reference House 001 v2 frame (193 members), its connections (312, D059) with `SetConnectionType`, the version 2 payloads that present them (ART-002, D060), dependency selectors with exact `impacted_artifacts` and reuse across revisions (DEP-001, D061), browser support for all of it (UI-003, D062), and traceability with payload size and time budgets (TEST-002, D063). VS-02b's scope is drafted and under review.

## Next steps

1. **In progress:** approve VS-02b's scope and acceptance criteria ([vs-02b.md](acceptance-tests/vs-02b.md), drafted 2026-11-21). Its proposals are under review: the judgment items one at a time, and the routine items together. Decided: proposal 1, perimeter infill walls with openings ([D064](../product/decisions/D064-vs02b-slice-boundary.md)), and proposal 2, generated in-plane walls in every perimeter bay ([D065](../product/decisions/D065-vs02b-wall-placement.md)). Proposal 3: generated wall framing owned by each wall, with kings and jacks by a width threshold ([D066](../product/decisions/D066-vs02b-wall-framing.md)). Proposal 4: layered definitions as snapshot records, fixed from the template ([D067](../product/decisions/D067-vs02b-assembly-definitions.md)). Proposal 5: one project-wide wall assembly, switched by a consequential `SetWallAssembly` ([D068](../product/decisions/D068-vs02b-wall-assembly-choice.md)). Proposal 6: user-placed rough openings, a framed-opening fit, routine commands ([D069](../product/decisions/D069-vs02b-openings.md)). Proposal 7, quantities and outputs, is next. No task files are drafted until the scope is approved.
2. ~~Add a ruleset on `main` that requires the four CI checks (`backend`, `vectors`, `frontend`, `e2e`) and blocks force pushes.~~ **Done** (2026-11-21, by the product owner). CI no longer runs on pushes to `main` ([TEST-001](tasks/TEST-001.md) §8, amended 2026-11-20), so the ruleset is what keeps an unchecked commit off `main`.

## Slices

**Status:** provisional sequencing; the vertical-slice strategy is confirmed.

- **VS-01:** Reference building, parametric frame, 2D/3D, persistence, preliminary schedule. *Complete (2026-11-19): all acceptance criteria traced and passing ([TEST-001](tasks/TEST-001.md)).*
- **VS-02:** Complete timber frame, connections, and dependency selectors ([D051](../product/decisions/D051-vs02-slice-boundary.md)). *Complete (2026-11-20): all acceptance criteria traced and passing ([vs-02-traceability.md](acceptance-tests/vs-02-traceability.md), [TEST-002](tasks/TEST-002.md)); [scope and acceptance criteria](acceptance-tests/vs-02.md).*
- **VS-02b:** Modular assemblies (straw bale and stud infill first), with walls and openings as needed, on the VS-02 frame. *Proposals 1–6 decided ([D064](../product/decisions/D064-vs02b-slice-boundary.md), [D065](../product/decisions/D065-vs02b-wall-placement.md), [D066](../product/decisions/D066-vs02b-wall-framing.md), [D067](../product/decisions/D067-vs02b-assembly-definitions.md), [D068](../product/decisions/D068-vs02b-wall-assembly-choice.md), [D069](../product/decisions/D069-vs02b-openings.md)): perimeter infill walls with user-placed openings, generated wall framing, fixed layered definitions, and one project-wide wall assembly; the rest of the scope and the acceptance criteria are under review ([vs-02b.md](acceptance-tests/vs-02b.md)).*
- **VS-03:** Natural-language AI proposals and human approval workflow.
- **VS-04:** Bounded engineering checks, cost and environmental estimates, alternatives.
- **VS-05:** Construction documentation and fabrication-oriented outputs.
- **VS-06:** Role-based collaboration, review comments, revision-aware professional verification.

Cross-cutting foundations (authentication, authorization, data migrations, logging, testing, data provenance) are introduced as required, not postponed wholesale to later slices.

## Tasks

The [task index](tasks/README.md) describes what a task file contains.

| Task | Title | Status |
|---|---|---|
| [MODEL-001](tasks/MODEL-001.md) | Snapshot schema, validation, and canonical serialization (merges the suggested MODEL-001 and MODEL-002) | Done (2026-11-18) |
| [TIMBER-001](tasks/TIMBER-001.md) | Deterministic post/beam generator and generation-rule conformance | Done (2026-11-18) |
| [MODEL-003](tasks/MODEL-003.md) | Typed commands and candidate snapshots (closes gap M5) | Done (2026-11-18) |
| [MODEL-004](tasks/MODEL-004.md) | Revision persistence, concurrency, idempotency, and previews | Done (2026-11-19) |
| [ART-001](tasks/ART-001.md) | Artifact infrastructure: derivation, storage, status, manifest | Done (2026-11-19) |
| [GEOM-001](tasks/GEOM-001.md) | `plan2d` and `mesh3d` derivations (closes C1) | Done (2026-11-19) |
| [EST-001](tasks/EST-001.md) | `timber_schedule`, `preliminary_estimate`, and price books (closes C6, M9) | Done (2026-11-19) |
| [API-001](tasks/API-001.md) | HTTP API for VS-01 (routes, errors, development authentication, owner-only access) | Done (2026-11-19) |
| [UI-001](tasks/UI-001.md) | Browser client for VS-01 (2D/3D views, footprint edits with preview, schedule, price book, history) | Done (2026-11-19) |
| [UI-002](tasks/UI-002.md) | Browser editors for story heights, roof, grid, and sections (the remaining D043 commands) | Done (2026-11-19) |
| [TEST-001](tasks/TEST-001.md) | Reference-house integration suite, traceability matrix, golden fingerprints, and CI | Done (2026-11-19) |
| [MODEL-005](tasks/MODEL-005.md) | VS-02: schema version 2 (new roles, `Connection`, frame parameters), retire version 1, frame parameter commands; merges together with TIMBER-002 | Done (2026-11-19), with TIMBER-002 |
| [TIMBER-002](tasks/TIMBER-002.md) | VS-02: `vs02-frame-1` (sills, joists, principal rafters, purlins, knee braces), Reference House 001 v2 fixture, ECMAScript oracle | Done (2026-11-19), with MODEL-005 |
| [CONN-001](tasks/CONN-001.md) | VS-02: connection generation per junction class (312 connections for Reference House 001 v2), preview connection diff, `SetConnectionType` | Done (2026-11-20; [D059](../product/decisions/D059-vs02-junction-rules-connection-type-command.md)) |
| [ART-002](tasks/ART-002.md) | VS-02: version 2 plan, mesh, schedule, and estimate payloads; "each" price-book rows | Done (2026-11-20; [D060](../product/decisions/D060-vs02-artifact-payloads.md)) |
| [DEP-001](tasks/DEP-001.md) | VS-02: dependency selectors and exact `impacted_artifacts` (D056) | Done (2026-11-20; [D061](../product/decisions/D061-vs02-selector-contents.md)) |
| [UI-003](tasks/UI-003.md) | VS-02: browser support for the complete frame and connections (roles and markers in 2D and 3D, the Frame tab, connection types, schedule tables, the confirmation dialog) | Done (2026-11-20; [D062](../product/decisions/D062-vs02-browser-connections.md)) |
| [TEST-002](tasks/TEST-002.md) | VS-02: traceability and the golden scenario's new commands for AC2-01 to AC2-09 (the if-and-only-if impact property shipped with DEP-001, D061), the sequences' reach, and budgets | Done (2026-11-20; [D063](../product/decisions/D063-vs02-traceability-and-budgets.md)) |

## Current limitations

- The time budgets (D063) are regression ceilings for the in-process service and the e2e dev-server setup, not user-facing targets; no product performance target exists yet.
- Neither traceability matrix has an at-risk or quarantined row.

## Open items

- Hosting, the production identity provider, and operations (open question 8).
- Not to be reopened while unresolved: the exact CAD kernel, Vermont code editions, datasets, and drawing export formats. See [open questions](../product/open-questions.md).
