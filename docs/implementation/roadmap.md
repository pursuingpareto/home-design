# Roadmap and status

The single status document for the project ([AGENTS.md](../../AGENTS.md), "Documentation maintenance"). Update it whenever a task's status changes. Decisions are in the [decision register](../product/decisions/README.md); each task file holds its own implementation notes.

**As of 2026-11-22:** VS-01 and VS-02 are complete. VS-02 delivered model schema version 2, the complete Reference House 001 v2 frame (193 members), its connections (312, D059) with `SetConnectionType`, the version 2 payloads that present them (ART-002, D060), dependency selectors with exact `impacted_artifacts` and reuse across revisions (DEP-001, D061), browser support for all of it (UI-003, D062), and traceability with payload size and time budgets (TEST-002, D063). VS-02b's scope and acceptance criteria are agreed (2026-11-21; [vs-02b.md](acceptance-tests/vs-02b.md), D064–D072). Its first merge, MODEL-006 with ASM-001 (2026-11-22), delivered model schema version 3 (assembly definitions, the wall system, walls, wall framing, and openings, with the fit rules), the wall rule `vs02b-walls-1`, the four wall commands, and Reference House 001 v3 (20 straw bale walls, 20 openings, 79 buck pieces; 246 pieces with stud infill). ART-003 (2026-11-22) delivered the fifth artifact, `assembly_schedule`, with D071's thermal figures, walls, openings, and wall framing in `plan2d` and `mesh3d`, the `assembly.` (per m²) and `wallframing.` (per m) estimate lines, their selectors, and the browser's interim support ([D082](../product/decisions/D082-vs02b-framing-layer-fill-quantity.md)–[D086](../product/decisions/D086-vs02b-wall-framing-ids-in-views.md)). The browser does not draw walls yet.

## Next steps

1. Draft `UI-004` in its own session: the browser's walls, wall framing, and openings in 2D and 3D with the "Wall layers" and "Wall framing" switches (D066), the assembly selector and the opening editor, the assembly schedule view, and thermal figures with their method and warnings ([vs-02b.md](acceptance-tests/vs-02b.md) §16). Then `TEST-003`. [`ART-003`](tasks/ART-003.md) is done (2026-11-22); its implementation notes list the measured impact table (two rows corrected from the prediction), the payload sizes and times for both families, and one D063 report for the product owner (the largest case's stud infill mesh is over half its ceiling).
2. ~~Add a ruleset on `main` that requires the four CI checks (`backend`, `vectors`, `frontend`, `e2e`) and blocks force pushes.~~ **Done** (2026-11-21, by the product owner). CI no longer runs on pushes to `main` ([TEST-001](tasks/TEST-001.md) §8, amended 2026-11-20), so the ruleset is what keeps an unchecked commit off `main`.

## Slices

**Status:** provisional sequencing; the vertical-slice strategy is confirmed.

- **VS-01:** Reference building, parametric frame, 2D/3D, persistence, preliminary schedule. *Complete (2026-11-19): all acceptance criteria traced and passing ([TEST-001](tasks/TEST-001.md)).*
- **VS-02:** Complete timber frame, connections, and dependency selectors ([D051](../product/decisions/D051-vs02-slice-boundary.md)). *Complete (2026-11-20): all acceptance criteria traced and passing ([vs-02-traceability.md](acceptance-tests/vs-02-traceability.md), [TEST-002](tasks/TEST-002.md)); [scope and acceptance criteria](acceptance-tests/vs-02.md).*
- **VS-02b:** Modular assemblies (straw bale and stud infill first), with walls and openings as needed, on the VS-02 frame. *Scope and acceptance criteria agreed (2026-11-21): perimeter infill walls with user-placed openings, generated wall framing, fixed layered definitions, one project-wide wall assembly, and a new assembly schedule with framing-corrected thermal figures ([vs-02b.md](acceptance-tests/vs-02b.md), [D064](../product/decisions/D064-vs02b-slice-boundary.md)–[D072](../product/decisions/D072-reference-house-001-v3-design-intent.md)). Tasks `MODEL-006` and `ASM-001` are done (2026-11-22, merged together), and so is `ART-003` (2026-11-22); `UI-004` and `TEST-003` are drafted one at a time after it.*
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
| [MODEL-006](tasks/MODEL-006.md) | VS-02b: schema version 3 (assembly definitions and layers, `WallSystem`, walls, wall framing, openings), validation with the girt and framed-opening fits, retire version 2, `SetWallAssembly` and the opening commands; merges together with ASM-001 | Done (2026-11-22; [D073](../product/decisions/D073-vs02b-wall-system-record.md)–[D077](../product/decisions/D077-vs02b-definition-supported-ranges.md)), with ASM-001 |
| [ASM-001](tasks/ASM-001.md) | VS-02b: wall rule `vs02b-walls-1` (walls, studs, girts, opening framing, bucks, keys, identity), the template definitions, sections, and materials, Reference House 001 v3 (20 walls, 20 openings, 79 buck pieces; 246 pieces with stud infill), ECMAScript oracle; merges together with MODEL-006 | Done (2026-11-22; [D078](../product/decisions/D078-vs02b-opening-framing-details.md)–[D081](../product/decisions/D081-reference-house-001-v3-template-text.md)), with MODEL-006 |
| [ART-003](tasks/ART-003.md) | VS-02b: `assembly_schedule` (walls, openings, wall framing, aggregates, assumptions, D071's thermal figures), walls and framing in `plan2d` and `mesh3d` for the two switches, `assembly.` (`m2`) and `wallframing.` (`m`) estimate lines, selectors, and the browser interim | Done (2026-11-22; [D082](../product/decisions/D082-vs02b-framing-layer-fill-quantity.md)–[D086](../product/decisions/D086-vs02b-wall-framing-ids-in-views.md)) |

## Current limitations

- The browser does not draw walls, wall framing, or openings, has no assembly schedule view, and has no wall controls (`UI-004`). It shows the assembly schedule's status, the estimate's wall lines, and their prices (D085).
- The stud infill house's payload sizes are measured and reported but not budget-gated, pending `TEST-003` (D086).

- The time budgets (D063) are regression ceilings for the in-process service and the e2e dev-server setup, not user-facing targets; no product performance target exists yet.
- Neither traceability matrix has an at-risk or quarantined row.

## Open items

- Hosting, the production identity provider, and operations (open question 8).
- Not to be reopened while unresolved: the exact CAD kernel, Vermont code editions, datasets, and drawing export formats. See [open questions](../product/open-questions.md).
