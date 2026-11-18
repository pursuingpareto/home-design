# D035 — Validation stages and detail-code catalog

**Status:** Confirmed  
**Date:** 2026-11-18  
**Scope:** Semantic snapshot validation and the error details it returns, for snapshots and for command candidates. Approved from [MODEL-001](../../implementation/tasks/MODEL-001.md) §9, item 1.  
**Amended by:** [D046](D046-conformance-validation-stage.md) — adds stage 5 (conformance, `VALIDATION_FAILED`), which runs only when stages 1–4 pass.

## Decision

### Stages

Validation runs in four ordered stages: **syntactic → referential → geometric → domain**.

- **Gating:** a stage runs only if every earlier stage passed. Within a stage, every issue is collected and reported.
- **One top-level code per stage:** stages 1–3 return `VALIDATION_FAILED`, and stage 4 returns `UNSUPPORTED_CONFIGURATION`. The top-level code of a failed validation is therefore always the code of the first stage that failed.
- **Datum checks run in stage 3:** the checks that `Footprint.origin_m = [0, 0]` ([D031](D031-vs01-unsupported-configurations.md)) and that Level 0 elevation is `0` ([D034](D034-vs01-level-bounds.md)) return `VALIDATION_FAILED`, so they belong in the geometric stage, not the domain stage.
- **Authorization:** checked by the API layer before validation (`UNAUTHORIZED`, `FORBIDDEN`). It is not a stage of the model validator.

### Detail codes

- The authoritative catalog is [building-model.md §6.1](../../architecture/building-model.md#61-detail-codes). Each detail code belongs to exactly one stage, and its top-level code follows from that stage.
- Detail codes are part of the public API contract:
  - **Adding** a code is backward compatible and may be done in a task with a documentation update.
  - **Renaming, removing, or moving a code to another stage** requires a new decision.
- The detail object keeps the shape in [interfaces.md §7](../../architecture/interfaces.md#7-error-contract): `path`, `code`, and an optional `value`. Human-readable messages are not part of the contract and may change freely.
- `OUT_OF_RANGE` (stage 3) means physically meaningless. `OUT_OF_SUPPORTED_RANGE` (stage 4) means well-formed but outside the VS-01 bounds. This keeps the existing interfaces.md example (`width_m: -1` → `OUT_OF_RANGE`) valid and follows the split in D031 and D032.

## Rationale

With gating, failures are easy to read: domain checks never run against malformed or dangling data, and each stage maps to one top-level code. The cost is that a snapshot with problems in several stages reports only the earliest stage's issues; fixing them may reveal more. Separate codes for physically meaningless values and unsupported values preserve the meaning of the two top-level codes.

## What this does not decide

- Path syntax, `related_paths`, and parser size limits (MODEL-001 §9, items 2, 3, 6; still pending).
- Detail codes for commands, previews, persistence, or artifacts. Those are added by their own tasks.
