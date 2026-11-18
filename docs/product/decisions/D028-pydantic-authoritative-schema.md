# D028 — Pydantic models as the authoritative schema definition

**Status:** Confirmed  
**Date:** 2026-11-18  
**Scope:** How the semantic snapshot, command, and artifact DTO schemas are defined, exported, and consumed. Applies from `MODEL-001` onward.

## Decision

- The authoritative machine-readable definition of the semantic snapshot, entity records, command envelopes/arguments, and artifact DTOs is a set of **Pydantic models in the Python backend** (the `model` module and, for artifacts, their owner modules).
- **JSON Schema** for the snapshot and entity records is exported from those models and **committed to the repository**. A contract test fails when the committed export differs from what the models produce, so the language-neutral contract cannot drift silently.
- The committed JSON Schema is tested against the Reference House 001 fixture ([D025](D025-reference-house-001-vs01-fixture.md)).
- The HTTP API publishes **OpenAPI** generated from the same models. TypeScript types and clients are generated from that OpenAPI, consistent with [interfaces.md](../../architecture/interfaces.md) §6.
- Rules that span several fields or records, and that JSON Schema cannot express, live in one server-side Python validation layer: referential integrity, level ordering, grid invariants, supported-configuration (domain) checks, and generation-rule conformance. The frontend does not reimplement them. It may run purely advisory checks for interactivity, but the server result is authoritative.
- Validation failures, whether from Pydantic or the domain validators, are reported only as the stable error codes and field paths of the [error contract](../../architecture/interfaces.md#7-error-contract). Library-specific error types and messages are not part of the API.

## Rationale and tradeoffs

- **For:** It matches the provisional Python backend (D022) and the planned OpenAPI → TypeScript client. Server-side validation has a single source. Generating the schema avoids maintaining Python and TypeScript definitions by hand.
- **Against:** The schema's source lives in one language. The committed JSON Schema export and its contract tests keep the specification readable and usable without Python, as D024 requires.
- **Rejected alternative:** Hand-written JSON Schema as the source, with Python and TypeScript generated from it. It is more language-neutral, but cross-record rules would still be coded in Python, and generated Pydantic models are awkward to extend.

## What this does not decide

- Exact Python, Pydantic, or code-generator versions; these are pinned in the implementation.
- Where in the repository the JSON Schema export is committed (to be fixed by `MODEL-001`).
- Canonical JSON serialization for fingerprints and hashes (still open).
- Whether D022's other provisional stack choices (React, Three.js, FastAPI, PostgreSQL drivers) are confirmed.
