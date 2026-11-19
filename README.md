# Home Design Platform

**Specification version:** 0.2 architecture draft (product decisions through D050) · **Status:** Working draft · **Date:** 2026-11-16

A tool-independent, version-controlled specification for a web-first, parametric home-design platform specializing initially in Vermont heavy-timber post-and-beam houses.

## Start here

1. [Product vision](docs/product/vision.md) and [principles](docs/product/principles.md)
2. [User workflows](docs/product/workflows.md) and [requirements](docs/product/requirements.md)
3. [Architecture overview](docs/architecture/overview.md), [building model](docs/architecture/building-model.md), [dependencies](docs/architecture/dependencies.md), [artifacts](docs/architecture/artifacts.md), and [interfaces](docs/architecture/interfaces.md)
4. [Reference House 001](docs/reference-projects/vermont-timber-house/README.md)
5. [Roadmap](docs/implementation/roadmap.md), [VS-01 scope and acceptance criteria](docs/implementation/acceptance-tests/vs-01.md), and [task index](docs/implementation/tasks/README.md)
6. [Decision register](docs/product/decisions/README.md) and [open decisions](docs/product/open-questions.md)

## Run the app locally

Requirements: [uv](https://docs.astral.sh/uv/), Node 22 or later, and PostgreSQL (optional; see `--memory`).

```bash
scripts/dev.sh            # API + web app; projects saved in the local PostgreSQL database "homedesign"
scripts/dev.sh --memory   # no database needed; projects are lost when you stop
```

Open http://localhost:5173 and sign in with `dev-token`. Press Ctrl+C to stop both servers. The script installs dependencies when needed, creates and migrates the database, and keeps a local preview key in `.dev/` (git-ignored). `scripts/dev.sh --help` lists the options.

## Status and conventions

- **Confirmed:** Product direction agreed with the product owner; see the decision register.
- **Provisional:** Proposed implementation details or milestones subject to evaluation.
- **Open:** Decisions requiring research or further discussion.
- Requirements use stable `FR-XX` identifiers; acceptance criteria use `AC-XX`; tasks use module-prefixed IDs.
- Documents describe intended behavior, **not an implemented or professionally approved building system**.

## Repository layout

`docs/` contains the working specification. `backend/` contains the Python backend and HTTP API (see [backend/README.md](backend/README.md)), and `frontend/` the VS-01 browser client (see [frontend/README.md](frontend/README.md)). `tests/vectors/` holds language-neutral test vectors and the golden scenario record. Run every check with `scripts/check.sh`; GitHub Actions runs the same checks on pushes to `main` and on pull requests (`.github/workflows/ci.yml`). The [VS-01 traceability matrix](docs/implementation/acceptance-tests/vs-01-traceability.md) maps each acceptance criterion to its tests.

## Safety boundary

Structural adequacy, jurisdictional compliance, and professional sign-off must not be inferred from renderings, preliminary schedules, or unverified calculations. Any engineering claims must be scoped, traceable, and reviewed as applicable.

## Architecture deep-dive (v0.2)

The [building model](docs/architecture/building-model.md), [dependency engine](docs/architecture/dependencies.md), and [module/API interfaces](docs/architecture/interfaces.md) now contain provisional schemas, operation protocols, status transitions, and acceptance tests. These are design contracts for review, not yet running code.
