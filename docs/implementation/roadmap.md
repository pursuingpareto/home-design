# Roadmap and status

The single status document for the project ([AGENTS.md](../../AGENTS.md), "Documentation maintenance"). Update it whenever a task's status changes. Decisions are in the [decision register](../product/decisions/README.md); each task file holds its own implementation notes.

**As of 2026-11-20:** VS-01 is complete. VS-02 is in progress: model schema version 2, the complete Reference House 001 v2 frame (193 members), and its connections (312, D059) with `SetConnectionType` are done. Version 2 payloads (ART-002, specified and approved), dependency selectors, browser support, and traceability remain.

## Next steps

1. Implement [ART-002](tasks/ART-002.md) in a fresh session. Its §12 proposals are approved; items 8–10 are [D060](../product/decisions/D060-vs02-artifact-payloads.md). Its §10 lists what each derivation reads, as input for `DEP-001`.
2. Then `DEP-001`, `UI-003`, and `TEST-002`, in the order of [vs-02.md](acceptance-tests/vs-02.md) §12.2.
3. Optional: make the CI workflow required for merges to `main` (a GitHub repository setting).

## Slices

**Status:** provisional sequencing; the vertical-slice strategy is confirmed.

- **VS-01:** Reference building, parametric frame, 2D/3D, persistence, preliminary schedule. *Complete (2026-11-19): all acceptance criteria traced and passing ([TEST-001](tasks/TEST-001.md)).*
- **VS-02:** Complete timber frame, connections, and dependency selectors ([D051](../product/decisions/D051-vs02-slice-boundary.md)). *In progress: [scope and acceptance criteria](acceptance-tests/vs-02.md); MODEL-005, TIMBER-002, and CONN-001 done.*
- **VS-02b:** Modular assemblies (straw bale and stud infill first), with walls and openings as needed, on the VS-02 frame.
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
| [ART-002](tasks/ART-002.md) | VS-02: version 2 plan, mesh, schedule, and estimate payloads; "each" price-book rows | Approved, not started (2026-11-20; [D060](../product/decisions/D060-vs02-artifact-payloads.md)) — **next** |
| DEP-001 | VS-02: dependency selectors and exact `impacted_artifacts` (D056) | Not drafted |
| UI-003 | VS-02: browser support for the complete frame and connections | Not drafted |
| TEST-002 | VS-02: traceability, golden scenario, and the impact property for AC2-01 to AC2-09 | Not drafted |

## Current limitations (until the remaining VS-02 tasks)

- Connections are generated but not shown: no markers, schedule counts, or "each" estimate lines (`ART-002`), and no browser display or type editor (`UI-003`).
- The 2D plan shows posts and beams only (`ART-002`; [artifacts.md §5](../architecture/artifacts.md)).
- The browser has no Frame tab; new roles render in one neutral color (`UI-003`).
- Every committing command marks all four artifacts stale (`DEP-001`).

## Open items

- Hosting, the production identity provider, and operations (open question 8).
- Not to be reopened while unresolved: the exact CAD kernel, Vermont code editions, datasets, and drawing export formats. See [open questions](../product/open-questions.md).
