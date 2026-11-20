# D063 — VS-02 traceability form, payload size budgets, and time budgets

**Status:** Confirmed; to be implemented by [TEST-002](../../implementation/tasks/TEST-002.md) (VS-02)  
**Date:** 2026-11-20  
**Scope:** How VS-02's acceptance criteria are traced and kept in step with their source, and the first size and time budgets. Approved from [TEST-002](../../implementation/tasks/TEST-002.md) §12, items 6–8. The routine items 1–5 are specified in the task file. Item 9, UI-003's four flagged choices, is decided separately.  
**Builds on:** [TEST-001](../../implementation/tasks/TEST-001.md) §4 (the VS-01 matrix, its reference forms, and the flake policy), and [D061](D061-vs02-selector-contents.md) (the impact property ships with DEP-001; `TEST-002` traces it).

## Decision

### The VS-02 traceability matrix (item 6)

- **A separate document,** `docs/implementation/acceptance-tests/vs-02-traceability.md`. The VS-01 matrix stays as it is and is still enforced.
- **One row per criterion bullet** of [vs-02.md](../../implementation/acceptance-tests/vs-02.md) §12.1 (`AC2-02.1`, `AC2-02.2`, …). A criterion without bullets is one row. That gives 17 rows.
- **Plus the VS-02 contract checks:** artifacts.md §10, "Version 2 reconciliation" (`ART2-1` to `ART2-3`), and dependencies.md §8, "VS-02 examples" (`DEP2-1` to `DEP2-4`). That gives 24 rows in all.
- **Checked against the IDs and the wording.** `test_traceability.py` derives the IDs from the sources, with a count guard. It also compares each row's criterion text with the source bullet, ignoring whitespace and link URLs. So a reworded criterion fails the check until its row and tests are reviewed again. The reference forms, `N/A —` rows, and quarantine marker are TEST-001's.

### Payload size budgets (item 7)

Sizes are RFC 8785 canonical bytes of each artifact payload, which are deterministic. The checks are gated in CI with no tolerance:

- **Reference House 001 v2:** each payload at most **256 KiB** (262,144 bytes).
- **The largest supported case** (TIMBER-002 §5.3: 7 × 7 stations, 80' × 80', 12" joists, 4 purlins, both brace planes): each payload at most **2 MB** (2,000,000 bytes).

### Time budgets (item 8)

These ceilings catch order-of-magnitude regressions; they are not user-facing targets. Each is the median of 5 runs, gated in CI, with no retries:

| Check | Ceiling |
|---|---|
| Preview, reference house, `SetFootprintDimensions` (in-process, in-memory store) | 1 s |
| Preview, largest case, width edit | 5 s |
| Commit with derivation of all four artifacts, largest case | 5 s |
| Browser (Playwright, the e2e dev-server setup): created house until 2D, 3D, and the schedule are shown | 10 s |
| Browser: Preview pressed until the confirmation dialog shows | 3 s |

- Each check prints its measurement.
- **If any CI measurement exceeds half its ceiling, the implementation stops and reports to the product owner rather than raising the ceiling.**
- The browser ceilings describe the dev-server e2e setup, not a production build.

## Rationale

- **Per bullet:** criteria such as AC2-08 have bullets that are proven by different tests. One row per criterion could pass while a bullet had no test.
- **Wording checked:** an approved criterion must not be silently narrowed under a row whose tests no longer prove it (AGENTS.md, "Never silently redefine an established requirement"). Edits to §12.1 are rare, so the duplicated text costs little.
- **Size ceilings:** the golden record pins the scenario's payloads exactly, but nothing bounded the largest case. Today's payloads sit at 66% (reference house) and 57% (largest case) of their ceilings, which leaves room for VS-02b.
- **Generous time ceilings:** shared CI runners vary by several times, and the flake policy forbids retries. At 5–10× today's timings, a ceiling still catches an accidental quadratic step, a lost reuse, or a render loop.

## Alternatives considered

- **Matrix:**
  - one row per criterion, as VS-01;
  - VS-02 sections in the VS-01 file;
  - IDs only, with no wording check.
- **Sizes:**
  - no budget, relying on the golden record's reviewed diffs;
  - the largest case only;
  - tighter ceilings, about 1.25× today.
- **Times:**
  - backend ceilings only, with browser timings reported but not gated;
  - report only, with no ceiling;
  - user-facing targets, which would need a production-build e2e job.

## What this does not decide

- Product performance targets for users: none exist yet. These ceilings are regression guards.
- UI-003's four flagged choices (TEST-002 item 9).
- Budgets for VS-02b's new payloads, beyond these per-payload ceilings.
