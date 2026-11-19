# System architecture

**Status:** Provisional technical design; product architectural principles are confirmed.

**Style:** Web-first modular monolith, with asynchronous workers for computationally expensive tasks. Preserve boundaries so components can be extracted later.

**Provisional stack:** React + TypeScript; Three.js for 3D rendering; SVG/Canvas for 2D editing; Python + FastAPI; PostgreSQL; Python background workers; evaluate OpenCascade and alternatives for exact geometry; provider-neutral AI integration.

**Chosen in implementation tasks:**

- Python tooling: uv, with a locked environment.
- Schemas: Pydantic v2, authoritative per D028.
- Database access: psycopg 3 (synchronous), with **plain numbered SQL migrations** applied by a small in-repo runner. There is no ORM: the schema relies on triggers, partial unique indexes, and row locks that are clearest in SQL ([MODEL-004](../implementation/tasks/MODEL-004.md) §10, item 3).
- HTTP API: **FastAPI**, which generates OpenAPI from the Pydantic models (D028); **uvicorn** as the server; **httpx** as a development dependency for the test client. Services are synchronous, because psycopg is, and handlers run them in a thread pool ([API-001](../implementation/tasks/API-001.md) §11, item 1).

**Core modules:**

1. `project`: project metadata, permissions, revisions, persistence.
2. `model`: semantic entities, constraints, typed operations, validation.
3. `dependencies`: dependency graph, invalidation, recomputation scheduling.
4. `geometry`: exact geometric derivation and render-mesh adapters.
5. `timber`: framing members, connection semantics, member schedules.
6. `assemblies`: reusable layer definitions and quantity calculations.
7. `analysis`: bounded engineering analyses with evidence and status.
8. `estimating`: costs, environmental calculations, assumptions and provenance.
9. `alternatives`: branches, comparison, proposed operations.
10. `documents`: drawing and schedule generation.
11. `ai`: intent parsing, proposal generation, constrained tool invocation.
12. `collaboration`: review, comments, approvals, access control.

**Invariant:** The authoritative building model is not a Three.js scene graph, render mesh, or opaque CAD file. Geometry libraries are replaceable adapters.

## Safety, reliability, and data requirements

- Professional approval is a recorded, authorized, revision-specific event; automated checks are not equivalent.
- Code and jurisdiction rules must be versioned by location, applicability, adoption date, and amendment; exact Vermont requirements require verification against authoritative sources.
- Calculation engines report applicability limits, assumptions, method versions, and evidence.
- Cost and carbon datasets record source, geography, date, unit, lifecycle boundary, and uncertainty.
- Permission checks and validation occur server-side; AI suggestions cannot bypass them.
- Backups, migration testing, observability, and audit logs are required before production use.
