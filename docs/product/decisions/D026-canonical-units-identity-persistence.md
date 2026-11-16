# D026 — Canonical units, identity, snapshots, and concurrency

**Status:** Confirmed  
**Date:** 2026-11-16  
**Scope:** Product-wide model, API, and VS-01 persistence contracts. Changing any item below requires a new decision, migrations, and fixture updates.

## Decision

The architecture v0.2 numeric, identity, snapshot, and concurrency defaults are accepted as authoritative, not provisional.

### Units, axes, and angles

- Canonical geometry is **meters** in a right-handed frame: **+X east/right in plan**, **+Y north/up in plan**, **+Z vertically upward**.
- Building-local origin is the southwest footprint corner. For Reference House 001, Z = 0 is the first-floor reference (D025), not grade. A project may carry a separate georeferenced site transform later.
- Conversion: **1 ft = 0.3048 m** exactly. Display may be imperial or metric; conversion happens at the UI/import boundary. Nominal size labels are not actual dimensions.
- APIs and persistence store angles in **radians**. UI may accept degrees or rise/run (for example 9/12).
- Money, when present: integer minor units plus ISO 4217 code. Environmental quantities keep explicit unit and scope; unknown is not zero.

### Numeric encoding and comparison

- Computational boundaries use finite IEEE-754 doubles. JSON numeric fields must be finite. Do not use float equality for semantic identity.
- Geometry adapters own kernel-internal tolerance. The published **coordinate comparison epsilon is 1e-6 m**. This is not construction or fabrication tolerance and is not a structural allowance.

### Identity

- Entity, project, revision, command, and operation identifiers are **opaque UUIDs**. Names and display order are not identifiers.

### Persistence and concurrency

- Each committed revision is an **immutable JSON snapshot** persisted as **PostgreSQL JSONB**, plus an **append-only operation/audit table**.
- Persist snapshot and operation record in one transaction. VS-01 revisions have exactly one parent; branching and merge are deferred.
- Writers send `base_revision_id` equal to the project head. Mismatch returns `REVISION_CONFLICT` (409) and must not overwrite. Idempotent retries use `command_id` as specified in the command envelope.

## What this does not decide

- Exact CAD kernel, Three.js, or other adapter libraries (D022 stack remains suitability-first).
- Hosting, identity provider, backups, and production security (open question 8).
- Whether later slices add event-sourced rebuild *in addition to* snapshots; replacing snapshot authority requires a new decision.
- Engineering precision, mill tolerances, or code-compliant dimensions.
