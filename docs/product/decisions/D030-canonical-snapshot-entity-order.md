# D030 — Canonical snapshot form and entity ordering

**Status:** Confirmed  
**Date:** 2026-11-18  
**Scope:** The semantic snapshot as input to fingerprints, comparisons, and determinism tests. Builds on [D029](D029-canonical-json-rfc8785.md).  
**Amended by:** [D042](D042-stable-grid-line-ids.md) — grid fractions are now `x_lines[k].fraction` / `y_lines[k].fraction`; values unchanged.

## Decision

- The order of the snapshot's `entities` array **has no semantic meaning**. Two snapshots whose records are identical, listed in a different order, are the same model.
- The **canonical snapshot** is the snapshot with `entities` sorted ascending by `id`, then serialized with RFC 8785 (D029). Wherever the specification hashes or compares "the snapshot", it means the canonical snapshot. That includes artifact `input_fingerprint` inputs ([artifacts.md](../../architecture/artifacts.md) §2.3), golden-fixture comparisons, and the round-trip test.
- **UUID text form:** every UUID (record IDs, references, and the project and revision IDs) must be written as lowercase, hyphenated 8-4-4-4-12 hex. Syntactic validation rejects any other form instead of rewriting it, so that sorting by `id` is well-defined and IDs compare as plain strings. Because the strings are ASCII, sorting by code unit and sorting by byte give the same order.
- Snapshots may be stored and transmitted with `entities` in any order. Writing them in canonical order is encouraged but not required. The fixture file keeps its current layout, grouped by kind.

## Arrays whose order is semantic

Only `entities` is reordered when canonicalizing. All other arrays keep their order. Where the specification requires a particular order, a snapshot that violates it is **rejected by validation, not re-sorted**:

| Array | Required order |
|---|---|
| `Building.level_ids` | ascending `Level.index` |
| `FrameSystem.member_ids` | ascending referenced `TimberMember.generation_key` ([generation rules](../../reference-projects/vermont-timber-house/generation-rules.md)) |
| `TimberGrid.x_fractions`, `y_fractions` | strictly ascending, from 0 to 1 inclusive |
| Coordinate tuples (`origin_m`, `start_m`, `end_m`, …) | positional `[x, y]` / `[x, y, z]` |

New array fields must declare whether their order is semantic. Undeclared arrays are treated as semantic.

## Rationale

Sorting by `id` is the simplest rule that every implementation can reproduce, and it never rejects a valid snapshot just because of how it is ordered. Without it, implementations could produce identical models with different fingerprints, and stored artifacts would wrongly look stale. The rejected alternative was a required fixed order (by kind, then by `generation_key` or index). It is easier to read, but every snapshot would have to be validated against the order, making snapshots more fragile. The canonical form exists for hashing, not for reading.

## What this does not decide

- Whether `revision_id` is part of artifact fingerprint inputs (still open, C5).
- The order of artifact payload arrays; artifacts.md defines those for each artifact.
