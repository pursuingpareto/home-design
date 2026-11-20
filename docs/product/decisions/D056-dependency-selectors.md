# D056 — Dependency selectors: impact by comparing input fingerprints

**Status:** Confirmed; implemented ([DEP-001](../../implementation/tasks/DEP-001.md), VS-02)  
**Date:** 2026-11-19  
**Scope:** How artifacts declare their inputs, how a preview determines impacted artifacts, and when an artifact is re-derived. Approved as decision 6 of the [VS-02 scope proposal](../../implementation/acceptance-tests/vs-02.md) (§11), within [D051](D051-vs02-slice-boundary.md).  
**Amends, when VS-02 implements it:**
- [artifacts.md §2.3](../../architecture/artifacts.md#23-fingerprint) (the fingerprint input);
- [interfaces.md §3](../../architecture/interfaces.md#3-preview-contract) (`impacted_artifacts`);
- [dependencies.md §2 and §6](../../architecture/dependencies.md) (the graph and the cache).

**Refined by:** [D061](D061-vs02-selector-contents.md) ([DEP-001](../../implementation/tasks/DEP-001.md), approved 2026-11-20). Item 4's lists are the coarse view: selections hold exactly what each builder reads, after its own projections. So there is no grid in any selection, the plan reads plan `x, y` only, the mesh reads section dimensions, the schedule reads lengths, and the estimate reads the schedule's aggregate lists. AC2-04 governs.

## Decision

1. **Selectors.** Every derivation declares a pure **selector** that extracts, from the canonical snapshot, exactly the records and fields it reads, in canonical form. The input fingerprint hashes:
   - the selection;
   - `generator_id`, `generator_version`, and `model_schema_version`;
   - any external inputs, such as the price book.

   It **no longer includes `revision_id`** or the whole snapshot.
2. **Computed impact.** A preview computes every artifact's fingerprint for the base and for the candidate. `impacted_artifacts` lists **exactly** the types whose fingerprints differ, and may be empty. There is no separately maintained dependency graph: the selectors are the graph.
3. **Reuse.** After a commit, an artifact whose fingerprint did not change is reused. The new revision gets its own envelope: its own `source_revision_id` and `head`, status `CURRENT`, and the cached payload keyed by `(type, generator_version, fingerprint)`. Only impacted artifacts are derived. Payloads never embed revision IDs.
4. **Version 2 selectors:**
   - `plan2d`: footprint, grid, levels, roof, member axes and roles, and connection locations and types.
   - `mesh3d`: everything `plan2d` reads, plus member sections.
   - `timber_schedule`: members, sections, materials, and connections.
   - `preliminary_estimate`: the schedule's aggregates and connection counts, plus the price book.

   Exact field lists are specified in the VS-02 task files.
5. **Verification.** Property-based tests assert that an artifact is impacted **if and only if** its payload for the new revision differs from the base's. A reused payload must equal a fresh derivation.
6. **Unchanged:**
   - AC-07: every envelope names its own revision, and stale results are never served as current.
   - Synchronous derivation after commit, and lazy recompute on read (dependencies.md §6). Asynchronous workers stay out of VS-02.

## Rationale

- **Exact:** comparing fingerprints is exact by construction, and cannot drift from what derivations actually read.
- **Honest previews:** previews stop over-reporting impact. For example, adding an unused section impacts nothing (FR-12).
- **Less work:** unchanged artifacts are reused instead of re-derived.
- **Mistakes are caught:** the if-and-only-if test catches a selector that misses an input.

## Alternatives considered

A static, field-level dependency graph declared separately from the derivations. This is more machinery, it can drift from the code, and it gains nothing at VS-02's scale.
