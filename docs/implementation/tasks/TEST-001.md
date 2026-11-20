# TEST-001 — Reference-house integration suite, traceability, and CI

**Status:** Done (2026-11-19) — passing locally and on GitHub Actions; see §12  
**Owner module:** tests and tooling: `backend/tests/`, `tests/vectors/`, `.github/workflows/`, `scripts/`  
**Slice:** VS-01  
**Depends on:** `MODEL-001` through `UI-002` (all done)  
**Unblocks:** declaring VS-01 complete (AC-09); safe iteration on VS-02  
**Touches:** no product behavior. Hosting and deployment stay open (open question 8).

## 1. Objective

VS-01's behavior is implemented and tested piece by piece: 439 backend tests, 51 frontend tests, and 14 browser end-to-end tests. Three things are still missing before VS-01 can be called done:

1. **Proof of coverage.** Nothing shows that every acceptance criterion (AC-01 to AC-09) and every architecture contract test list has an automated test. Nothing stops a test from being deleted or renamed without anyone noticing.
2. **Whole-house invariants across many edits.** Today's tests check one command at a time. AC-09 asks for "operations and invariants … including deterministic replay": the plan, mesh, schedule, and estimate must stay consistent with the model after any sequence of accepted edits, and every rejected edit must leave the project unchanged.
3. **Automation.** Every suite runs only when someone remembers to run it locally. Nothing protects `main`.

After this task:
- every VS-01 criterion maps to named tests, and a test enforces the map;
- a reference-house scenario and a property-based sequence check whole-house invariants after every step;
- a golden file catches any unintended change to generated output;
- one local command, and a GitHub Actions workflow, run every suite.

## 2. Inputs and governing documents

- [VS-01 acceptance criteria](../acceptance-tests/vs-01.md): AC-01 to AC-09, and the four expanded contract lists it names.
- Contract test lists:
  - [building-model.md §9](../../architecture/building-model.md#9-vs-01-model-acceptance-tests) (7 tests);
  - [dependencies.md §8](../../architecture/dependencies.md#8-vs-01-examples-and-tests) (8 events);
  - [artifacts.md §10](../../architecture/artifacts.md#10-acceptance-tests-additions-to-vs-01) (8 tests);
  - [interfaces.md §9](../../architecture/interfaces.md#9-contract-test-matrix) (8 tests).
- Determinism decisions: D029 (RFC 8785), D030 (canonical order), D041 (deterministic IDs), D042 (stable line IDs), D045 (no-ops).
- AGENTS.md: "Run relevant tests before declaring a task complete"; "Never silently modify authoritative engineering data".

## 3. Scope

**In scope**

- A traceability matrix and a test that enforces it (§4).
- A scripted reference-house scenario with a shared invariant checker (§5).
- Golden fingerprints for that scenario, with a drift check (§6).
- Property-based command sequences using the same checker (§7).
- A local `scripts/check.sh` and a GitHub Actions workflow running every suite (§8).

**Non-goals**

- New product behavior, or changes to any API or payload.
- Deployment, preview environments, release automation, or branch-protection settings. Branch protection is a repository setting that the owner turns on.
- Code-coverage percentages as a gate. The traceability matrix is the coverage contract.
- Performance, load, or visual-regression testing.

## 4. Traceability matrix (proposal 1)

A new document, `docs/implementation/acceptance-tests/vs-01-traceability.md`, has one row per item:

- AC-01 to AC-09;
- building-model §9 tests 1–7;
- dependencies §8 events;
- artifacts §10 tests 1–8;
- interfaces §9 tests 1–8.

Each row lists the automated tests that cover the item, written as stable references:

- pytest: `backend/tests/test_api.py::test_vs01_flow`;
- Vitest: `frontend/tests/pairing.test.ts › pairViews (artifacts.md §4, §10 test 6)`;
- Playwright: `frontend/e2e/vs01.spec.ts › AC-01: …`.

**Not-applicable rows** carry a reason instead of tests:

- dependencies §8 "Change display color only": VS-01 has no display-only command;
- dependencies §8 "Old worker finishes after new worker": VS-01 has no workers. Superseded results are prevented by fingerprint matching, and the ART-001 lazy-recompute tests cover that, so they are listed as the closest guarantee.

**Enforcement:** a pytest test, `backend/tests/test_traceability.py`, parses the matrix and checks that:

- every item in the five source lists has a row, so a criterion added to a source document fails until it is mapped;
- every row has at least one test or a not-applicable reason;
- every referenced test exists:
  - pytest functions are found by name in the file;
  - Vitest and Playwright tests are found by their exact `describe`/`it`/`test` titles in the file.

**Gaps found while building the matrix** are filled by §5–§7, or listed as open with a reason. They are never silently dropped.

## 5. Reference-house scenario and invariant checker (proposal 2)

**Checker:** `backend/tests/integration/invariants.py` is a single function, `check_revision(client, project_id, revision_id)`, that reads everything over HTTP and asserts every whole-house invariant:

| Invariant | Source |
|---|---|
| The snapshot validates, and its canonical bytes round-trip | building-model §9.1, D029 |
| Plan, mesh, and schedule member IDs equal the snapshot's `TimberMember` IDs | artifacts §10.3, AC-03 |
| All four envelopes share `source_revision_id`; every `CURRENT` one is `preliminary`, with every claim `false` | AC-07, AC-08, artifacts §10.7 |
| Plan dimensions and the mesh footprint, level heights, and eave match the semantic records within 1e-6 m | AC-01, artifacts §10.2 |
| Schedule counts and totals reconcile with the inventory and with `length_m` | AC-04 |
| Estimate quantities equal schedule aggregates; missing prices never give a total of 0 | artifacts §10.4, §10.8 |

**Transition checks** compare consecutive revisions:
- member IDs are preserved for every surviving `generation_key` (building-model §9.4, D042);
- the head moved exactly once per committed, non-no-op command.

After a rejection, the head, the snapshot bytes, and the artifact manifest are unchanged (AC-06, building-model §9.7).

**Scenario:** `backend/tests/integration/test_reference_house.py` runs one project through the HTTP API, on both stores, with a fixed clock and fixed command IDs. It runs every D043 command at least once, and the checker runs after every step:

1. Create; set a complete price book.
2. Width 40' (preview, confirm).
3. Grid X to four bays, keeping `x1` and `x2`.
4. Width 76', now accepted. Then 100', rejected with no change.
5. Story heights 10' and 10'.
6. Roof 10/12, routine.
7. Add section `10x12`, then set BEAM to it. The estimate becomes partial, with the old price row unused.
8. Retry a commit (replayed), then a stale-base commit (conflict).
9. Undo to revision 2.
10. Replay the operation log into a fresh store and compare every revision fingerprint (AC-09).

## 6. Golden scenario fingerprints (proposal 3)

The scenario in §5 is fully deterministic: fixed project ID, actor, clock, and command IDs, and IDs minted under D041. Its outputs are recorded in a committed file, `tests/vectors/scenarios/reference-house-001.json`. For each revision it records:

- the revision ID;
- the snapshot fingerprint;
- each artifact's status, `generator_version`, `input_fingerprint`, and a payload fingerprint (RFC 8785 over the payload).

**Drift check:** a test compares a fresh run with the committed file. It is regenerated with `uv run python -m tests.integration.golden` (exact module path decided during implementation).

**Why:** any change to generation, derivation, rounding, or canonicalization changes a fingerprint. An intended change then appears as a reviewed diff to this file, together with the matching `generator_version` bump or decision. An unintended change fails the suite. This enforces AGENTS.md's "never silently modify authoritative engineering data" for derived output.

## 7. Property-based command sequences (proposal 4)

`backend/tests/integration/test_sequences.py` uses Hypothesis to generate sequences of 1–8 commands:

- footprint, story heights, roof, grid (move, add, or remove a line; equal bays), sections, and undo;
- arguments drawn both inside and just outside the D032 and D034 bounds, so rejections are exercised.

**Each step:**
- previews and, if accepted, commits;
- runs the §5 checker;
- after a rejection, asserts that nothing changed.

**Runs:**
- **Memory store only.** PostgreSQL behavior is already covered by the scenario and the MODEL-004 tests.
- **Deterministic in CI:** a Hypothesis profile `ci` uses `derandomize=True` and a fixed example count (proposed: 40 sequences), so a run never flakes.
- **Longer runs on demand:** a `thorough` profile runs 500 sequences when selected with `HYPOTHESIS_PROFILE=thorough`.

Any failing example Hypothesis finds is added as an explicit regression test.

## 8. One command locally, the same in CI (proposals 5–7)

**`scripts/check.sh`** (proposal 5) runs every check in the same order as CI, stops at the first failure, and prints which step failed:

1. **Backend:** `uv sync --locked`, `pytest` (which needs the local PostgreSQL, as today), `schema_export --check`, and `ui_fixtures --check`.
2. **Cross-language vectors:** regenerate the ECMAScript oracle files (`node tests/vectors/jcs/generate.mjs`), then `git diff --exit-code tests/vectors/`. This is the only check that the committed Node vectors still match their generator.
3. **Frontend:** `npm ci`, `check:api`, `typecheck`, Vitest, and `build`.
4. **End to end:** Playwright in Chromium.

**GitHub Actions** (proposal 6): `.github/workflows/ci.yml` runs on pull requests, and by hand (`workflow_dispatch`). It has four jobs mirroring the steps above:

> **Amended (2026-11-20, by the product owner):** the workflow no longer runs on pushes to `main`. `main` only moves by fast-forward to a commit whose pull request passed (AGENTS.md, "CI before `main` moves"), so that run tested identical code a second time. A ruleset on `main` that requires the four checks replaces it as the guard against unchecked commits.

| Job | Runs on | Needs |
|---|---|---|
| `backend` | ubuntu-latest | PostgreSQL 18 service container; uv with the pinned Python 3.12 |
| `vectors` | ubuntu-latest | Node 22 |
| `frontend` | ubuntu-latest | Node 22, with an npm cache |
| `e2e` | ubuntu-latest, after `backend` and `frontend` | uv, Node 22, `playwright install --with-deps chromium`; Playwright traces uploaded as an artifact on failure |

- **Pinned actions:** third-party actions are pinned to full commit SHAs, with the version in a comment, so the workflow cannot change underneath us.
- **Postgres in CI:** the backend job sets `HOMEDESIGN_TEST_DATABASE_URL` to the service container. The existing name guard (`homedesign_test`) applies unchanged.
- **No secrets** are needed. The preview key and development tokens in tests are test-only values, already in the test configuration.
- **Nothing runs on GitHub until a pull request is opened.** Requiring the checks on `main` (a ruleset) is a repository setting for the owner.

**Determinism and flakes** (proposal 7):
- No automatic retries, locally or in CI. A flaky test is a bug.
- Every test uses fixed clocks, seeds, and IDs. Wall-clock time appears only where a test is about expiry, and then through the injected clock.
- If a test must be quarantined while it is fixed, it is skipped with a reason that names a tracking issue, and the matrix (§4) marks its rows as at risk. The matrix test fails if a criterion has *only* quarantined tests.

## 9. Proposals for the product owner

1. ~~**Traceability matrix** (§4),~~ **Approved** (2026-11-19); enforced by a test that requires every source criterion to have a row and every referenced test to exist. Not-applicable rows need a reason.
2. ~~**Reference-house scenario and invariant checker** (§5):~~ **Approved** (2026-11-19). one scripted project exercising every D043 command over HTTP on both stores, with whole-house invariants after every step, and replay at the end.
3. ~~**Golden scenario fingerprints** (§6):~~ **Approved** (2026-11-19). a committed per-revision record of snapshot, artifact-input, and payload fingerprints, with a drift check. Intended output changes appear as reviewed diffs.
4. ~~**Property-based sequences** (§7):~~ **Approved** (2026-11-19). Hypothesis-generated command sequences, deterministic in CI (40 sequences), with a `thorough` profile on demand.
5. ~~**`scripts/check.sh`** (§8):~~ **Approved** (2026-11-19). one local command for everything CI runs. The alternative is a Makefile, which is less portable on Windows and adds no capability here.
6. ~~**GitHub Actions CI** (§8):~~ **Approved** (2026-11-19). four jobs on pushes to `main` and on pull requests (pull requests only since 2026-11-20, §8), with PostgreSQL 18 and Node 22, actions pinned to SHAs, and traces uploaded on failure. The repository is already on GitHub. Turning on branch protection stays with the owner.
7. ~~**Flake policy** (§8):~~ **Approved** (2026-11-19). no automatic retries; fixed clocks and seeds; quarantine only with a tracking issue, reflected in the matrix.

## 10. Acceptance criteria

1. The matrix covers every item in the five source lists, and `test_traceability.py` passes. Removing or renaming any referenced test makes it fail.
2. The scenario passes on both stores, with the checker running after every step, including rejections, a retry, a conflict, undo, and replay.
3. The golden file is committed. Changing any generator's output, for example by perturbing one rounding step locally, fails the drift check.
4. The property-based test passes under the `ci` profile, and runs under `thorough` on demand.
5. `scripts/check.sh` passes locally. The workflow passes on GitHub after a push (verified by the owner, or from the run link).
6. backend/README.md, frontend/README.md, and the root README document `scripts/check.sh` and CI. The task index and status files are updated.

## 11. Definition of done

All §10 criteria are met. VS-01 is then complete by its own acceptance criteria. The status files say so, and list what remains open: hosting and identity (open question 8), and the at-risk rows in the matrix, if any.

## 12. Implementation notes (2026-11-19)

**Delivered:**
- **Traceability:** [`vs-01-traceability.md`](../acceptance-tests/vs-01-traceability.md) has 40 rows: AC-01 to AC-09, BM-1 to BM-7, DEP-1 to DEP-8, ART-1 to ART-8, and IF-1 to IF-8. `backend/tests/test_traceability.py` derives the expected IDs from the five source documents and checks every referenced pytest function, Vitest or Playwright title, and npm script. Two rows are not applicable:
  - DEP-2: VS-01 has no display-only command;
  - DEP-6: VS-01 has no workers. The row lists the closest guarantees.
- **Shared helpers:**
  - `backend/tests/api_support.py`: the OpenAPI-validating HTTP client, moved out of `test_api.py`;
  - `backend/tests/integration/invariants.py`: `check_revision`, `check_transition`, and `assert_unchanged`.
- **Scenario:** `backend/tests/integration/scenario.py` and `test_reference_house.py` cover 13 steps and 9 revisions:
  - every D043 command, a price book, a rejection, a replayed retry, a stale-base conflict, and undo;
  - the checker runs after every step;
  - the operation log is replayed into a fresh store at the end.
  
  Both stores produce byte-identical records.
- **Golden record:** `tests/vectors/scenarios/reference-house-001.json`. Regenerate it with `uv run python tests/integration/golden.py` and check it with `--check`. Adding one cent to the money rounding locally changes the record, as intended.
- **Sequences:** `backend/tests/integration/test_sequences.py`. Hypothesis profiles are registered in `conftest.py`: `ci` is the default (derandomized, 40 sequences) and `thorough` runs 500. Each run records its outcomes as Hypothesis events, and every command type is both accepted and rejected under the `ci` profile.
- **Tooling:** `scripts/check.sh`, and `.github/workflows/ci.yml` with four jobs (`backend` with a PostgreSQL 18 service, `vectors`, `frontend`, and `e2e`). Actions are pinned to commit SHAs: checkout v7.0.1, setup-node v7.1.0, setup-uv v10.3.3, and upload-artifact v7.0.2.

**Tests:**
- `scripts/check.sh` passes locally: 444 backend tests (5 new), the schema, fixture, and vector drift checks, 51 Vitest tests, type-checking, the build, and 14 Playwright tests.
- The `thorough` profile (500 random sequences) passed once, in 6 min 37 s.

**Choices made during implementation:**
- **Test seam:** `create_app` gains an optional `project_id_factory`. Tests use it for deterministic project IDs; production never passes it.
- **Deterministic random UUIDs:** server-generated random UUIDs (request IDs and the price-book ID) are drawn from a fixed sequence during the scenario, so the price-book ID, and therefore the estimate fingerprint, is reproducible.
- **Deterministic Hypothesis by default:** the `ci` profile is now the default for every Hypothesis test in the suite. Tests that set `max_examples` keep their counts, and all of them become derandomized, in line with the flake policy.
- **Sequence IDs:** the sequence test fixes the project ID, derives command IDs from the step number, and samples sections by label. Hypothesis had detected that random project IDs changed the entity order between runs of one example.

**Limitations:**
- **CI on GitHub:** the first run failed only in `vectors`: `vectors.json` recorded the exact Node version, which differs between CI (Node 22) and local runs. The label now names the engine family only, and [run 44624998046](https://github.com/pursuingpareto/home-design/actions/runs/44624998046) passed all four jobs. Making CI required before merging is a repository setting.
- **Golden scope:** the golden record covers one scenario. New derivations or generator versions need a reviewed regeneration.
