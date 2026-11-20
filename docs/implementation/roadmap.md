# Vertical-slice implementation roadmap

**Status:** Provisional sequencing; vertical-slice strategy confirmed.

- **VS-01:** Reference building, parametric frame, 2D/3D, persistence, preliminary schedule. *Complete (2026-11-19): all acceptance criteria traced and passing ([TEST-001](tasks/TEST-001.md)).*
- **VS-02:** Complete timber frame, connections, and dependency selectors ([D051](../product/decisions/D051-vs02-slice-boundary.md)). *In progress: [scope and acceptance criteria](acceptance-tests/vs-02.md); MODEL-005 and TIMBER-002 done (complete frame, schema version 2); CONN-001 to TEST-002 remain.*
- **VS-02b:** Modular assemblies (straw bale and stud infill first), with walls and openings as needed, on the VS-02 frame.
- **VS-03:** Natural-language AI proposals and human approval workflow.
- **VS-04:** Bounded engineering checks, cost and environmental estimates, alternatives.
- **VS-05:** Construction documentation and fabrication-oriented outputs.
- **VS-06:** Role-based collaboration, review comments, revision-aware professional verification.

Cross-cutting foundations (authentication, authorization, data migrations, logging, testing, data provenance) are introduced as required, not postponed wholesale to later slices.
