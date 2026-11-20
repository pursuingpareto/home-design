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

## Collaboration workflow (agreed with the product owner, 2026-11-19)

- **Proposals:** task files present numbered proposals. Mark each one **Routine** (it follows from approved decisions and documents) or **Your judgment** (product behavior, a new requirement, or a real tradeoff). Routine items may be approved together; judgment items are discussed one at a time.
- **Standing approvals:**
  - Test-only changes need no approval.
  - Once the work is done and `scripts/check.sh` passes, commit and fast-forward `main` without asking. The fast-forward goes through CI (next item).
- **CI before `main` moves:** commit on a branch, push it, and open a pull request. When its CI passes, fast-forward `main` to the branch (`git merge --ff-only`) and push `main`, so `main` gets the exact commits CI checked. Never force-push, and never enable auto-merge.
- **One session per task:** start each task (drafting or implementing) in a fresh session. The task file, the decisions, and `docs/implementation/roadmap.md` are the handoff, so a task file must stand on its own.
- **Local processes:** stop servers this repository's tools started (for example a leftover `scripts/dev.sh` server) without asking.

## Documentation maintenance

When implementation changes an architectural contract, update the relevant documentation.

When a new product or architecture decision is approved, record it in `docs/product/decisions/`.

`docs/implementation/roadmap.md` is the single status document: the next steps, the slices, and every task's status. Update it whenever a task's status changes, and keep task files' own status lines consistent with it. Do not add other status files.

Never silently redefine an established requirement to accommodate an implementation shortcut.

## Communication

Explain significant architectural decisions and tradeoffs.

Distinguish completed functionality, partially implemented functionality, and proposed future work.

When a task is complete, summarize changed files, tests performed, remaining limitations, and recommended next steps.