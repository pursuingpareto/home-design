# AGENTS.md — Home Design Platform

## Project purpose

Build a web-first architectural design platform for homeowners, builders, and design professionals.

The platform combines parametric building modeling, timber-frame construction, AI-assisted design, cost estimation, environmental analysis, and construction documentation.

## Source of truth

The repository documentation is authoritative.

Before implementing a feature, read the relevant documents under:

- `docs/product/` — Product vision, principles, requirements, and decisions.
- `docs/architecture/` — System architecture and technical contracts.
- `docs/reference-projects/` — Reference buildings and test fixtures.
- `docs/implementation/` — Roadmap, tasks, and acceptance tests.

Do not invent requirements when documentation is ambiguous. Identify unresolved questions and propose solutions.

## Architectural principles

1. Maintain one authoritative semantic, parametric building model.
2. Derive geometry, rendering meshes, drawings, schedules, and estimates from that model.
3. Use validated, transactional model operations for all changes, including AI-generated changes.
4. Preserve stable identifiers, deterministic behavior, and dependency-aware updates.
5. Keep geometry, engineering, rendering, and AI integrations replaceable behind clear interfaces.
6. Distinguish preliminary analysis from professionally verified construction designs.
7. Never silently modify authoritative engineering data or claim unsupported code compliance.

## Development workflow

- Work in small, end-to-end vertical slices.
- Before coding, identify relevant requirements, dependencies, and acceptance criteria.
- Prefer the simplest implementation that satisfies the current milestone.
- Write automated tests for model operations and important invariants.
- Run relevant tests before declaring a task complete.
- Do not introduce major dependencies or architectural changes without explaining the tradeoffs.
- Keep changes focused and reviewable.

## Documentation maintenance

When implementation changes an architectural contract, update the relevant documentation.

When a new product or architecture decision is approved, record it in `docs/product/decisions/`.

Keep `docs/implementation/roadmap.md` and task status files consistent with actual progress.

Never silently redefine an established requirement to accommodate an implementation shortcut.

## Communication

Explain significant architectural decisions and tradeoffs.

Distinguish completed functionality, partially implemented functionality, and proposed future work.

When a task is complete, summarize changed files, tests performed, remaining limitations, and recommended next steps.