# D090 — VS-02b budgets: the stud infill house, a named largest case for walls, and time budgets

**Status:** Confirmed; to be implemented by [TEST-003](../../implementation/tasks/TEST-003.md) (VS-02b)  
**Date:** 2026-11-23  
**Scope:** The size and time budgets for VS-02b's payloads and flows. Approved from [TEST-003](../../implementation/tasks/TEST-003.md) §13, judgment items 9–11. The routine items 1–8 (the traceability matrix and its check, the contract checks as bullets, the golden steps, the sequences, and how sizes are reported) are specified in the task file. Item 12, UI-004's twelve flagged choices, is decided separately.  
**Builds on:** [D063](D063-vs02-traceability-and-budgets.md) (per-payload ceilings, time ceilings, and the stop-and-report rule), vs-02b.md §6 routine item 15 (D063's ceilings apply to every payload), [D077](D077-vs02b-definition-supported-ranges.md) (openings have no size bounds beyond > 0 and the fit), and [D086](D086-vs02b-wall-framing-ids-in-views.md) (the stud infill gate left to `TEST-003`).

## Decision

### The stud infill house is gated (item 9)

- Reference House 001 v3 with stud infill (after `SetWallAssembly`) is a gated size case, at the reference house's ceiling: each payload at most **256 KiB** (262,144 bytes).
- The largest cases are gated with stud infill as well as with straw bale, at **2 MB** (2,000,000 bytes).
- Reported under D063's rule: the stud infill reference house's `mesh3d` is 219,188 bytes, **84%** of its ceiling.

### A named largest case for walls (item 10)

- **Openings have no bounds** beyond positive size and the fit (D077), so walls have no largest supported case. A valid snapshot (the largest frame with 26 one-inch windows per wall) measured 2,441,533 bytes for `mesh3d` and 2,834,791 for `assembly_schedule`, over the 2 MB ceiling.
- **The named wall case:**
  - D063's largest frame (7 × 7 stations over 80' × 80', 12" joists, 4 purlins, both brace planes), with 1'-6" brace legs;
  - stud infill with D077's densest framing: studs at 12", 4 girts;
  - a centered 3'-0" × 4'-0" window, sill 3'-0", in every wall.

  Measured: 48 walls, 48 openings, 1,239 pieces; largest payload `mesh3d` at 1,268,294 bytes (63%), reported under D063's rule.
- It is gated at **2 MB** in both families, beside D063's case, which stays as it is.
- **It is a named case, not a bound.** The 2 MB ceiling guards the wall payloads against regressions; it does not limit what a user can build. The roadmap says so.
- **Bounds on openings** (a minimum rough-opening size, or a maximum per wall) are raised as a separate product question, for a task of its own.

### Time budgets (item 11)

Each is the median of 5 runs, gated in CI, with no retries, and D063's stop-and-report rule above half a ceiling:

| Check | Ceiling |
|---|---|
| Preview, the named wall case, width edit (replaces D063's largest-case preview) | 5 s |
| Commit with all five artifacts derived, the named wall case (replaces D063's largest-case commit) | 5 s |
| Preview, the named wall case, `SetWallAssembly` | 5 s |
| Preview, reference house, `SetOpening` | 1 s |
| Browser: Create until both views, the timber schedule, and the assembly schedule | 10 s |
| Browser: the stud infill house reloaded until both views | 10 s |
| Browser: Preview pressed until the `SetWallAssembly` dialog | 3 s |

- D063's reference-house preview and its two browser checks are unchanged.
- The browser ceilings describe the dev-server e2e setup, not a production build, as D063's do.
- Expected against half: the named wall case's commit is estimated at about 48% in CI (1,612 ms locally, with CI about 1.5× slower). If CI measures more than half, the implementation stops and reports.

## Rationale

- **Stud infill gated:** one command reaches it from every project, and D008's comparison has two assemblies. A ceiling that checks only one leaves the other unbounded. Being at 84% makes the next growth in the mesh a reviewed choice.
- **A named case:** D063's largest case keeps only 10 openings and the fixture's framing, so it barely exercises the wall payloads. Without opening bounds there is no true maximum, and saying so is better than implying one. One window per wall matches D072's pattern.
- **Time checks on the named case:** it is the heaviest named regeneration. The browser checks reuse D063's ceilings, so no new number is introduced for them.

## Alternatives considered

- **Stud infill:** reported only, as before; a separate, higher ceiling.
- **Largest case:** D063's case only; two windows per wall; bounding openings first, which would block VS-02b on a product change.
- **Times:** backend checks on D063's case only; browser timings reported only.

## What this does not decide

- Bounds on openings (an open item in the roadmap).
- UI-004's twelve flagged choices (TEST-003 item 12).
- Product performance targets for users: none exist yet.
