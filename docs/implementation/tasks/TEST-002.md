# TEST-002 — VS-02 traceability, the golden scenario's new commands, and budgets

**Status:** Done (2026-11-20). All nine §12 proposals were approved: items 6–8 are recorded as [D063](../../product/decisions/D063-vs02-traceability-and-budgets.md), and item 9 confirmed UI-003's four choices. Implementation notes are in §17.  
**Owner module:** tests and tooling: `backend/tests/`, `frontend/tests/`, `frontend/e2e/`, `tests/vectors/scenarios/`, `docs/implementation/acceptance-tests/`. No product code changes.  
**Slice:** VS-02  
**Depends on:** `MODEL-005`, `TIMBER-002`, `CONN-001`, `ART-002`, `DEP-001`, and `UI-003` (all done; `main` at `e632578`). Merges on its own, with CI passing ([vs-02.md](../acceptance-tests/vs-02.md) §12.2).  
**Unblocks:** declaring VS-02 complete (AC2-09); drafting VS-02b

## 1. Objective

VS-02's behavior is implemented and tested task by task: 718 backend tests, 89 Vitest tests, and 22 Playwright tests, with the drift checks. The if-and-only-if impact property already runs in the property-based sequences, the invariants, and the golden scenario (DEP-001, [D061](../../product/decisions/D061-vs02-selector-contents.md)). Four things are still missing before VS-02 can be called done:

1. **Proof of coverage.** No document maps AC2-01 to AC2-09 to tests, and nothing fails when a VS-02 test is deleted or renamed. The VS-02 contract checks that ART-002 and DEP-001 added to artifacts.md §10 and dependencies.md §8 are, by their own wording, "traced by `TEST-002`".
2. **The golden scenario's new commands.** The golden record still covers only the D043 commands. `SetFrameParameters` and `SetConnectionType` are absent (TIMBER-002 §13, MODEL-005 §9: "`TEST-002` extends the scenario").
3. **Reach of the sequences.** The sequences draw both new commands, but a measured `ci` run never reaches three narrow-impact outcomes, two of them ones DEP-001 added draws for (§4, §7).
4. **Budgets.** CONN-001, ART-002, DEP-001, and UI-003 each measured size or time, and deferred "any budget" to this task. None is set.

After this task:
- every VS-02 criterion and contract check maps to named tests, and a test enforces the map against vs-02.md's wording;
- the golden record covers the two new commands, a rejection of each, and their reuse on undo;
- the `ci` sequences reach every VS-02 outcome, and a gate keeps them reaching it;
- payload size and time budgets are set and checked (in the form §12 settles);
- VS-02 is complete by its own acceptance criteria.

## 2. Inputs and governing documents

- **Acceptance criteria:** [vs-02.md](../acceptance-tests/vs-02.md) §12.1 (AC2-01 to AC2-09) and §12.2 (the `TEST-002` row: "a regenerated golden scenario covering the new commands; new commands in the sequences; traceability for the if-and-only-if impact property, which `DEP-001` delivers (D061)").
- **VS-02 contract checks** (bullet lists, kept out of the VS-01 matrix's numbered lists on purpose):
  - [artifacts.md §10](../../architecture/artifacts.md#10-acceptance-tests-additions-to-vs-01), "Version 2 reconciliation" (3 bullets; ART-002 §17);
  - [dependencies.md §8](../../architecture/dependencies.md#8-vs-01-examples-and-tests), "VS-02 examples" (4 bullets; DEP-001 §18).
- **The pattern this task follows:** [TEST-001](TEST-001.md) §4–8 (the matrix, the scenario, the golden record, the sequences, the flake policy), [vs-01-traceability.md](../acceptance-tests/vs-01-traceability.md), and `backend/tests/test_traceability.py`.
- **Decisions:** [D061](../../product/decisions/D061-vs02-selector-contents.md) (the impact property ships with DEP-001; `TEST-002` traces it), [D055](../../product/decisions/D055-pre-release-schema-replacement.md) (records regenerated as reviewed diffs), [D059](../../product/decisions/D059-vs02-junction-rules-connection-type-command.md) (312 connections, `SetConnectionType`), [D057](../../product/decisions/D057-vs02-frame-command-roof-classification.md) (`SetFrameParameters`), [D062](../../product/decisions/D062-vs02-browser-connections.md) (the browser).
- **Implementation notes, and where each test lives:** [MODEL-005](MODEL-005.md) §14, [TIMBER-002](TIMBER-002.md) §13, [CONN-001](CONN-001.md) §15, [ART-002](ART-002.md) §17 (payload sizes), [DEP-001](DEP-001.md) §18 (preview times, reuse), [UI-003](UI-003.md) §17 (the browser tests, and four choices flagged for the product owner).
- **Code:** `backend/tests/integration/` (`scenario.py`, `invariants.py`, `test_sequences.py`, `golden.py`), `backend/tests/test_traceability.py`, `backend/tests/conftest.py` (Hypothesis profiles), `frontend/tests/ui003.test.tsx`, `frontend/e2e/connections.spec.ts`, `frontend/e2e/editors.spec.ts`, `scripts/check.sh`, `.github/workflows/ci.yml`.

## 3. Scope

**In scope**

- A VS-02 traceability matrix and its enforcement (§4–5).
- New steps in the golden scenario, and its regenerated record (§6).
- Draw changes and an outcome gate for the sequences (§7).
- Payload size and time budgets (§8).
- How the browser tests trace AC2-08 (§9), and closing UI-003's four flagged choices (§10).
- Documents and status (§11).

**Non-goals**

- Any product behavior, payload, command, or API change. If a test exposes a defect, it is reported and fixed in its own change, not here.
- Re-implementing the impact property (done by DEP-001, D061).
- Tracing task-file acceptance lists (for example UI-003 §13) row by row. The matrix traces vs-02.md and the architecture contract checks, as TEST-001 did for VS-01. Task-level tests appear in it only where they prove a criterion.
- Performance work. If a budget fails, that is a finding for the product owner, not a reason to tune here.
- The `main` ruleset (a repository setting for the owner, roadmap next step 2), hosting, and deployment.

## 4. Where VS-02 stands (measured while drafting, against `e632578`)

**Already in place:**

- **Sequences** (`test_sequences.py`) draw all nine command types after creation, `SetFrameParameters` and `SetConnectionType` included (MODEL-005, CONN-001), and check `check_impact` (AC2-04) at every accepted step and an empty list at every no-op (DEP-001).
- **Invariants** (`invariants.py`) check connections against the frame and the CONN-001 §6 formula, plan, mesh, and schedule connections against the snapshot (artifacts.md §10's three version 2 bullets), and every payload against a fresh build.
- **Golden scenario** (`scenario.py`): 13 steps and 9 revisions; every committing step is previewed and its `impacted_artifacts` recorded and checked; undo reuses all four of revision 2's payloads. 10 of 32 post-creation artifacts are reused.
- **Browser:** `ui003.test.tsx` (32 cases, one `describe` per UI-003 §13 test number), `connections.spec.ts` (6 cases), and the Frame tab in `editors.spec.ts`'s untouched-tab case.

**What the `ci` profile reaches** (`pytest tests/integration/test_sequences.py --hypothesis-show-statistics`, 40 sequences, 3 min 51 s; the share of the 45 generated cases, 5 of them discarded as invalid, in which each outcome occurs):

| Command | Accepted | Rejected | No-op | Impact sizes reached |
|---|---|---|---|---|
| `SetFrameParameters` | 37.8% | 22.2% | — | 4 only |
| `SetConnectionType` | 4.4% | 17.8% | 28.9% | 4 only |
| `SetGableRoofParameters` | 55.6% | 26.7% | 2.2% | 4, 3 (pitch only), 2 (overhang only) |
| `SetMemberSection` | 11.1% | — | — | 3 only |
| `SetTimberGrid` | 6.7% | 4.4% | — | 4, 3 (re-identified line) |
| `AddSection` | 4.4% | 22.2% | — | 0 |

**Gaps found:**

- No VS-02 matrix (§5).
- The golden record has no `SetFrameParameters` or `SetConnectionType` step (§6).
- The `ci` sequences never reach three narrow outcomes: two that DEP-001 added draws for, a joist spacing that keeps the joist count (impact 2) and a section swap to one with the same dimensions (impact 2, mesh unchanged), and one that no draw targets, `SetConnectionType` for a class with no connections (impact 0). Each is covered by a targeted case in `test_impact.py::test_measured_impact` or `test_impact.py::test_connection_type_for_a_class_without_connections_impacts_nothing_but_needs_confirmation`, so AC2-04 is checked for them, but only from the created house (§7).
- No budget is set (§8).
- vs-02.md §12.2 lists "new commands in the sequences" under `TEST-002`. They are already there, so this task's part is §7.

## 5. The VS-02 traceability matrix (items 6 and 4)

### 5.1 Form (item 6, judgment; approved 2026-11-20)

A new document, `docs/implementation/acceptance-tests/vs-02-traceability.md`, beside the VS-01 matrix, which stays as it is and is still enforced (AC2-05 points to it).

**One row per criterion bullet**, with the bullet's text:

- **AC rows:** a criterion with bullets gets one row per bullet, numbered in order (`AC2-02.1`, `AC2-02.2`, `AC2-02.3`). A criterion without bullets is one row (`AC2-01`). From §12.1: AC2-01; AC2-02.1–3; AC2-03.1–3; AC2-04; AC2-05; AC2-06.1–3; AC2-07; AC2-08.1–3; AC2-09. **17 rows.**
- **Contract rows:** `ART2-1` to `ART2-3` (artifacts.md §10, "Version 2 reconciliation") and `DEP2-1` to `DEP2-4` (dependencies.md §8, "VS-02 examples"). **7 rows.**

**24 rows** in all. Reference forms, `N/A —` rows, and the `[quarantined: <issue>]` marker are exactly TEST-001 §4's.

**Why per bullet:** AC2-08's three bullets are proven by different tests (views, editors, the price-book form). The same holds for AC2-02, AC2-03, and AC2-06. One row per criterion would pass while a bullet had no test.

*Alternatives:*
- **one row per criterion** (9 + 7 rows), as the VS-01 matrix does. It is shorter, but a row can be satisfied by tests of one bullet only;
- **VS-02 sections in vs-01-traceability.md.** One file, but the two slices' counts and parsers mix, and a VS-02 edit risks the VS-01 check.

### 5.2 The drift check against vs-02.md (item 6, judgment; approved 2026-11-20)

`test_traceability.py` gains `test_every_vs02_item_is_traced`, which:

- **derives the 24 IDs** from the sources: the `- **AC2-NN: …**` lines of vs-02.md §12.1 and the `- ` bullets indented under each, and the two bullet lists in artifacts.md §10 and dependencies.md §8. A count guard (24) fails if a source list changes size, as TEST-001's guard (40) does;
- **checks each row's criterion cell against the source text**, after normalizing whitespace and turning Markdown links into their text. So rewording a criterion fails until its row, and the tests listed for it, are reviewed again. This is new: the VS-01 check compares IDs only;
- **applies TEST-001's checks** to every row: at least one test or an `N/A —` reason, every reference exists, and not every reference is quarantined.

*Alternative:* IDs only, as for VS-01. It is less to maintain, but a criterion can be reworded, or narrowed, under a row whose tests no longer prove it, and nothing notices.

### 5.3 Reference checks, for both matrices (item 4, routine)

`reference_exists` is tightened, test-only:

- a Vitest or Playwright title must occur **once** in its file, as the first argument of `it(`, `test(`, or `describe(`, and not of `.skip(`, `.only(`, `.fixme(`, or `.todo(`;
- a pytest function must not carry `pytest.mark.skip` or `xfail`, unless the matrix marks it quarantined.

Today a title only has to appear somewhere in the file in double quotes, so a skipped test, or the same text in a comment, passes. The VS-01 matrix is checked the same way. Measured while drafting, each of its Vitest and Playwright titles occurs exactly once in its file. Any row that still fails is fixed in the same change and listed in the implementation notes.

### 5.4 First draft of the rows

Candidate tests, from the task files' implementation notes. The implementation confirms each one, adds the new tests of §6–8, and may replace a candidate with a better one. `GOLDEN` is `backend/tests/integration/test_reference_house.py::test_reference_house_scenario_matches_golden`, and `SEQ` is `backend/tests/integration/test_sequences.py::test_random_command_sequences_keep_every_invariant`. Backend paths are shortened (`test_x.py::` for `backend/tests/test_x.py::`, and `::` alone for the file named just before), and long titles end in `…`. The matrix uses full references.

| ID | Criterion (short) | Candidate tests |
|---|---|---|
| AC2-01 | Version 2 only; version 1 rejected | `test_commands.py::test_created_project_equals_fixture_exactly`, `test_timber.py::test_registry`, `test_timber.py::test_retired_rule_is_unsupported`, `test_mutations.py::test_mutation` (case `13-model-schema-version-1-retired`), `test_fixture.py::test_committed_schema_rejects_stage1_errors`, `test_project.py::test_migration_refuses_a_database_with_version_1_projects` |
| AC2-02.1 | New roles generated; 193 members | `test_timber.py::test_reference_values`, `::test_fixture_inventory_is_exact_generator_output`, `::test_inventory_matches_independent_ecmascript_implementation`, `::test_generation_is_deterministic_and_order_independent`, `::test_member_counts_for_every_supported_grid` |
| AC2-02.2 | Stable IDs, including the frame commands | `test_timber.py::test_spacing_change_keeps_lower_ordinals`, `::test_purlin_count_change_keeps_lower_ordinals`, `test_connections.py::test_brace_toggle_mints_new_ids_and_undo_restores_originals`, `test_commands.py::test_frame_parameters`, `GOLDEN` (§6), `SEQ` |
| AC2-02.3 | Plan, mesh, and schedule agree | `test_geometry.py::test_one_inventory_in_plan_mesh_and_schedule`, `::test_plan_positions_are_exact_projections`, `frontend/tests/meshScene.test.ts › draws one box per member…`, `GOLDEN`, `SEQ` |
| AC2-03.1 | Connections per D054, two members, stable IDs | `test_connections.py::test_fixture_connections_are_exact_rule_output`, `::test_junction_rules_hold_for_the_fixture`, `::test_connections_match_independent_ecmascript_implementation`, `::test_surviving_connections_keep_ids_and_members`, `::test_connections_are_deterministic_and_order_independent` |
| AC2-03.2 | Switching a class's type is validated | `test_connections.py::test_set_connection_type_switches_one_class_and_back`, `::test_set_connection_type_errors`, `::test_set_connection_type_current_type_is_noop`, `::test_api_requires_a_preview_and_validates_the_response`, `::test_random_set_connection_type_never_raises`, `GOLDEN` (§6) |
| AC2-03.3 | Counts reconcile with the frame | `test_connections.py::test_counts_for_every_supported_grid`, `::test_counts_at_parameter_bounds`, `test_estimating.py::test_schedule_counts_follow_the_formula_for_every_grid`, `SEQ` |
| AC2-04 | Exact impact; reuse | `test_impact.py::test_measured_impact`, `::test_undo_reuses_every_payload_of_its_target`, `::test_noop_impacts_nothing`, `test_artifacts.py::test_unchanged_artifacts_are_copied_without_deriving`, `SEQ`, `GOLDEN` |
| AC2-05 | VS-01 still holds | `test_traceability.py::test_every_vs01_item_is_traced`, `test_api.py::test_ui_fixtures_are_current`, `test_fixture.py::test_committed_schema_is_current`, `test_timber.py::test_fixture_and_template_are_current`, `GOLDEN` |
| AC2-06.1 | 193 members, 312 connections | `test_timber.py::test_reference_values`, `test_connections.py::test_fixture_connections_are_exact_rule_output` |
| AC2-06.2 | The schedule reconciles | `test_estimating.py::test_reference_house_schedule`, `::test_reference_house_schedule_connections`, `SEQ` |
| AC2-06.3 | Per meter and per piece; never 0 | `test_estimating.py::test_complete_book`, `::test_timber_only_book_is_partial`, `::test_no_book_is_unavailable_never_zero`, `frontend/tests/components.test.tsx › shows connection lines as counts priced each…`, `GOLDEN` (§6, the unpriced Joist hanger line) |
| AC2-07 | Still preliminary; no capacity claim | `test_geometry.py::test_no_capacity_size_or_fastener_fields`, `test_connections.py::test_connections_make_no_claims`, `test_artifacts.py::test_envelope_contract_and_fingerprint`, `test_estimating.py::test_reference_length_is_the_plain_formula`, `ui003.test.tsx › every type description says representational only…`, `› shows the preliminary banner in the workspace` |
| AC2-08.1–3 | Browser | §9 |
| AC2-09 | Traceability; golden, sequences, CI | `test_traceability.py::test_every_vs02_item_is_traced` (new), `GOLDEN`, `SEQ`, the sequence outcome gate (§7) |
| ART2-1 | Markers and rows are the 312 connections | `test_geometry.py::test_mesh_markers_copy_the_records`, `::test_plan_markers_are_on_the_entering_members_plane`, `GOLDEN`, `SEQ` |
| ART2-2 | Aggregates sum; class counts follow the formula | `test_estimating.py::test_schedule_counts_follow_the_formula_for_every_grid`, `::test_schedule_counts_at_parameter_bounds`, `SEQ` |
| ART2-3 | Assumptions copied; no capacity field | `test_geometry.py::test_no_capacity_size_or_fastener_fields`, `GOLDEN` |
| DEP2-1 | `AddSection`: nothing impacted, all reused | `test_artifacts.py::test_unchanged_artifacts_are_copied_without_deriving`, `test_impact.py::test_measured_impact`, `GOLDEN` |
| DEP2-2 | Pitch only: plan reused | `test_impact.py::test_measured_impact`, `GOLDEN` |
| DEP2-3 | Overhang only: plan and mesh | `test_impact.py::test_measured_impact`, `test_commands.py::test_overhang_alone_moves_no_member` |
| DEP2-4 | Price book: only the estimate | `test_impact.py::test_price_book_change_makes_only_the_head_estimate_stale`, `test_estimating.py::test_book_change_makes_only_the_estimate_stale` |

Parametrized tests (`test_mutation`, `test_measured_impact`) are referenced by function, as in the VS-01 matrix. The row's cell names the case that matters in a short note after the reference, which the checker ignores.

**CI:** AC2-09 says CI runs these tests. CI runs `scripts/check.sh`'s steps, so every referenced test runs there. The matrix does not reference the workflow. The definition of done links the passing run, as TEST-001 did.

## 6. The golden scenario's new commands (item 1, routine)

### 6.1 New steps

Inserted after step 7 (the beam section change) and before step 8 (the retry and the conflict), so the final undo to revision 2 crosses them, and the records of revisions 1–8 do not change. The base is the 76' four-bay house with 10' stories and a 10/12 roof: **282 members and 470 connections**. Measured through the HTTP API on `e632578`:

| Step | Command | Preview | `impacted_artifacts` | Shows |
|---|---|---|---|---|
| 7a `frame-joists-0.62` | `SetFrameParameters`, joist spacing 0.62 m, the rest stored | 72 members and 144 connections updated; none added or removed | `mesh3d`, `plan2d` | A frame edit that keeps the joist count: IDs kept, the schedule and estimate reused (DEP-001 §8, at this house's 19' bays) |
| 7b `frame-eave-braces-off` | `SetFrameParameters`, eave braces off (spacing 0.62 m kept) | 44 members and 88 connections removed | all four | Retirement: surviving member and connection IDs kept (`check_transition`); 238 members and 382 connections after |
| 7c `joist-beam-hanger` | `SetConnectionType {joist-beam, JOIST_HANGER}` | 144 connections updated, no member | all four | The estimate stays `partial`: the Joist hanger line is 144 each with no amount, the grand total is `null`, never 0 (AC2-06) |
| 7d `joist-beam-bridle` | `SetConnectionType {joist-beam, BRIDLE}` | 422 `UNSUPPORTED_CONFIGURATION`, `UNSUPPORTED_VALUE` at `connection_defaults["joist-beam"]` | — | A disallowed type changes nothing (AC2-03, AC-06) |
| 7e `frame-purlins-minus-1` | `SetFrameParameters`, purlins −1 | 422 `VALIDATION_FAILED`, `OUT_OF_RANGE` at `parameters.purlins_per_slope` | — | An out-of-range parameter changes nothing |

The undo to revision 2 then reuses all four of revision 2's payloads, as today (measured: 4 of 4).

**Assertions added to the scenario:** the member and connection counts after 7b, the Joist hanger line after 7c, and the impact lists of 7a (two types) and 7b–7c (four). The checker, `check_impact`, and the replay already run after every step.

### 6.2 The regenerated record (D055)

- **Revisions:** 9 → 12. The records of revisions 1–8 are unchanged. The undo revision moves from sequence 9 to 12; its artifact fingerprints stay equal to revision 2's.
- **Steps:** 13 → 18 (three commits, two rejections).
- **Reuse:** 12 of 44 post-creation artifacts (10 of 32 today), the two new ones being 7a's schedule and estimate.
- **Not changed:** the UI fixture, `vectors.json`, schemas, and OpenAPI.

The diff is reviewed as additive, and any change to revisions 1–8 is a finding.

*Alternatives:*
- **a joist spacing that changes the count** (for example 0.65 m here: 8 joists removed). It shows minting rather than reuse, but 7b already retires members, and the narrow case is the one DEP-001 measured as easy to break;
- **`SetConnectionType` for a class with no connections** (impact 0, still consequential). It needs both brace planes off first, which adds a step. `test_impact.py` and `connections.spec.ts` already cover it from the created house;
- **a separate VS-02 scenario file.** It keeps the VS-01 record untouched, but doubles the scenario machinery for five steps.

## 7. The sequences reach every VS-02 outcome (item 2, routine; test-only)

**Draw changes** in `draw_command`, so the `ci` profile reaches two of the three outcomes of §4 that no sequence reaches today:

- **`joist_spacing`:** half the draws stay within 10% above the stored spacing, where the joist count is kept (DEP-001 §8: 0.62, 0.65, and 0.70 m keep five joists at 12' bays). Today's draw is uniform over 10"–50".
- **`member_section`:** when a section with the same dimensions as the role's current one exists, half the draws pick it.
- **`connection_type`:** a draw that first turns both brace planes off is not added. A sequence step is one command, so this needs two draws in a row. The case stays covered by the targeted test, and the gate does not require it.

**An outcome gate:** a module-scoped fixture in `test_sequences.py` collects each step's outcome (command type, accepted, rejected, or no-op, and the impact size). After the test, under the `ci` profile only, it asserts that:

- every command type is accepted at least once, and every type whose draw includes out-of-bounds arguments (all but `SetMemberSection` and `UndoToRevision`) is also rejected at least once;
- `SetFrameParameters` and `SetMemberSection` reach an impact of 2, `SetGableRoofParameters` 2 and 3, `SetTimberGrid` 3, and `AddSection` 0.

The `ci` profile is derandomized, so the gate is deterministic: it fails only when a change to the draw or the code changes what the 40 sequences reach, which is when it should be reviewed. The count stays 40. The run time (3¾ minutes) is measured again and reported.

*Alternative:* keep TEST-001's practice of reading the Hypothesis statistics by hand when the draw changes. That costs nothing, but §4 shows it already missed three outcomes.

## 8. Budgets (items 7 and 8)

No product document sets a size or time target, and requirements.md has no performance requirement. Budgets are therefore new requirements, for the product owner. The proposals below are ceilings that catch regressions, not targets to tune toward.

### 8.1 Payload size (item 7, judgment; approved 2026-11-20)

**Measured** (ART-002 §17; RFC 8785 canonical bytes of the payload):

| Payload | Reference House 001 v2 (193 members, 312 connections) | Largest supported case (1,216 members, 2,110 connections) |
|---|---|---|
| `plan2d` | 115,823 | 751,076 |
| `mesh3d` | 141,605 | 917,034 |
| `timber_schedule` | 173,680 | 1,135,194 |
| `preliminary_estimate` | 2,588 | 2,598 |

**Proposed ceilings**, checked by a new `backend/tests/test_budgets.py` (deterministic, so gated in CI with no tolerance):

- **each payload of the reference house: at most 256 KiB** (262,144 bytes; today's largest is 66% of it);
- **each payload of the largest supported case** (TIMBER-002 §5.3: 7 × 7 stations, 80' × 80', 12" joists, 4 purlins, both brace planes): **at most 2 MB** (2,000,000 bytes; today's largest is 57% of it).

Canonical bytes are measured, not HTTP bodies: they are deterministic and independent of the server's JSON settings and of compression. The connection keys dominate (ART-002 §17), so a key format change is the likeliest thing to hit a ceiling.

*Alternatives:*
- **no size budget:** the golden record already fixes the scenario's payloads exactly, so any change is reviewed; but nothing bounds growth in the largest case;
- **tighter ceilings** (for example 1.25× today): they flag growth sooner, and fail on ordinary VS-02b additions.

### 8.2 Preview, commit, and render time (item 8, judgment; approved 2026-11-20)

**Measured:**

| What | Measured | Where |
|---|---|---|
| Preview, Reference House 001 v2, through the service | 110–120 ms | DEP-001 §18 |
| Preview of a frame or type change, through the HTTP test client | 205–293 ms (loaded machine, see below) | drafting |
| `propose`, largest case, width edit | 0.47 s | CONN-001 §15 |
| `impact` alone, largest case | 236 ms (equal snapshots) to 331 ms (width edit) | DEP-001 §18 |
| Browser: create the house until 2D, 3D (193 glyphs), and the schedule are shown | 1.8–2.2 s | drafting, Playwright |
| Browser: reload until the same | 2.1–2.5 s | drafting |
| Browser: Preview pressed until the dialog shows | 0.40–0.51 s | drafting |
| Browser: Confirm pressed until both views are paired at the new revision | 2.0–2.3 s | drafting |

The drafting numbers are five runs each, on the development machine, against the e2e setup (the Vite dev server, unbundled), while the 40-sequence test ran on the same machine. They are rough, and probably high. A full preview of the largest case through the service was not measured; `propose` plus `impact` suggests about 0.8–0.9 s.

**Proposal:** ceilings at roughly 5–10× today's numbers, gated in CI, each the median of 5 runs, with no retries (TEST-001 §8):

| Check | Ceiling | Where |
|---|---|---|
| Preview, reference house, `SetFootprintDimensions` | 1 s | `test_budgets.py`, in-process, in-memory store |
| Preview, largest case, width edit | 5 s | `test_budgets.py` |
| Commit with derivation of all four artifacts, largest case | 5 s | `test_budgets.py` |
| Browser: created house until views and schedule are shown | 10 s | a new Playwright case in `connections.spec.ts` |
| Browser: Preview until the dialog | 3 s | the same case |

Each check prints its measurement, and the implementation notes record the CI values. If any CI value exceeds half its ceiling, the implementation stops and reports rather than raising the ceiling.

**Why generous:** shared CI runners vary by several times, and a time check that flakes breaks the flake policy. A ceiling 5–10× out still catches what matters at this stage: an accidental quadratic step, a lost reuse, or a render loop. The browser ceilings describe the dev-server setup the e2e job uses, not a production build, and say so.

*Alternatives:*
- **report only:** print the measurements in CI (and in an on-demand `budgets` marker) and set no ceiling until there is a product target. It never flakes, but nothing fails on a regression;
- **user-facing targets** (for example a preview dialog within 1 s and a first render within 3 s, in a production build): meaningful for users, but they need a production-build e2e job and quieter runners, which is more than VS-02's tooling has;
- **the largest case in the browser** (created through the API, then rendered): it would bound the 3D scene at 2,110 connections, at the cost of a slow e2e case. Not proposed; the 3D glyphs are instanced (UI-003 §17).

## 9. How the browser tests trace AC2-08 (item 3, routine)

By the **`it` and `test` titles** of the cases that prove each bullet, in TEST-001's reference form (`frontend/<path> › <exact title>`), checked by §5.3:

- **AC2-08.1** (new members and markers in 2D, 3D, and the schedule): `ui003.test.tsx` groups 1–4 (role styling, markers and grouping, 3D markers and the switch, selection), the schedule case of group 8, `components.test.tsx › shows rafters and purlins on the roof tab, with their role styles (UI-003 §4)`, `meshScene.test.ts`'s basis case, and in Playwright `connections.spec.ts › markers: …` and `vs01.spec.ts › the plan's roof tab shows the rafters and purlins (ART-002 §9)`.
- **AC2-08.2** (frame parameters and connection types through preview and apply): `ui003.test.tsx` groups 5–7 and the dialog cases of group 8; in Playwright the four `frame:` and `connection type:` cases, the brace-fit pointer, and `editors.spec.ts › submitting a consequential tab without edits previews as a no-op`.
- **AC2-08.3** (the price-book form's "each" rows, delivered by ART-002): `components.test.tsx › takes per-piece prices for each rows, with no unit conversion (ART-002 §9)`, `› keeps untouched stored prices exactly and keeps unused rows with their unit`, and `vs01.spec.ts › price book: complete then partial coverage` (which prices the Pegged mortise and tenon line per piece).

UI-003 §13 test 10 (VS-01 still holds) traces AC2-05 through the VS-01 matrix, and §13 test 11 traces AC2-07.

*Alternatives:*
- **`describe` titles** (UI-003's §13 numbers): a cell of three references instead of a dozen, but a group still passes when its cases are deleted, and the rows would follow UI-003's numbering rather than AC2-08's bullets;
- **a `file › describe › it` form** that the checker resolves structurally: precise and readable, but a parser for nested blocks is more than the tightened title check needs.

## 10. UI-003's four flagged choices (item 9, judgment; settled 2026-11-20)

UI-003 §17 kept four implementation choices and flagged them for the product owner. None changes a matrix row: AC2-08 does not mention them, and each is tested as implemented. They are listed here so that VS-02 is not declared complete with open flags. Each is a separate question, in this order, and the recommendation for each is to **confirm it as implemented**:

- **a. Untouched Connections rows cannot be previewed** (UI-003 §7.2, approved item 5): a row's Preview is enabled only when its select differs from the stored type. UI-003 §13 test 9 said "or any Connections row … previews as a no-op", which cannot happen. Playwright asserts that the seven buttons are disabled; the server's no-op is covered by `test_connections.py::test_set_connection_type_current_type_is_noop`. *If not confirmed:* enable the button on untouched rows, so that they preview as a no-op, as the Frame tab does.
- **b. The dialog expands object-valued changes per key:** the preview's `changes` carry `parameters` and `connection_defaults` as whole objects, and the dialog shows one row per changed key (`parameters.<field>`, `connection_defaults["<class>"]`). *If not confirmed:* one row per object, with its old and new values whole.
- **c. The "Steel knife plate" label** (UI-003 §8.3's table), while the catalog description begins "Concealed steel knife plate with dowels". The full description is still shown from the catalog. *If not confirmed:* another label, changed in `labels.ts` and the tests that name it.
- **d. The brace-fit pointer also names the Footprint tab**, because the server's detail names the footprint too (a bay is a fraction of the footprint). *If not confirmed:* point to the Frame tab only, which means filtering a related path the server reports.

Any change that is not a confirmation is a small UI change of its own, outside this task (§3), with its own approval. This task then records the outcome in UI-003 §17 and in the matrix.

## 11. Changes to existing tests and documents

**Tests** (test-only changes need no approval):

- `test_traceability.py`: `test_every_vs02_item_is_traced` and the tightened `reference_exists` (§5), with cases in `test_reference_checks_reject_missing_tests` for a skipped title, a duplicate title, and a title only in a comment.
- `integration/scenario.py` and the golden record (§6); `integration/test_sequences.py` (§7).
- `test_budgets.py` (new) and one Playwright case (§8), in the form items 7 and 8 settle.
- Any VS-01 matrix row that the tightened check rejects, fixed in place.

**Documents:**

- `docs/implementation/acceptance-tests/vs-02-traceability.md` (new, §5).
- vs-02.md §12.2: the `TEST-002` row says the sequences already drew the new commands, and this task added their reach and the gate (§7). Its status line names the matrix.
- artifacts.md §10 and dependencies.md §8: their "traced by `TEST-002`" notes point to the matrix.
- `tests/README.md` and `backend/README.md`: the golden scenario's steps, the budgets test, and `--hypothesis-show-statistics`.
- UI-003 §17: the outcome of item 9.
- **Decision record:** the judgment items, once approved, are recorded as **D063** (VS-02 traceability form and budgets), with the register updated.
- **The roadmap:** TEST-002's row, VS-02 complete, the next steps, and the "Current limitations" line about traceability and budgets.

## 12. Proposals for approval

**Routine** (they follow from TEST-001 §4–8, D055, D061, and vs-02.md §12.2). **All five approved together (2026-11-20).**

1. **Golden scenario** (§6): steps 7a–7e after the beam section change and before the retry: joist spacing 0.62 m (plan and mesh only), eave braces off (members and connections retired), `joist-beam` → Joist hanger (unpriced, never 0), and two rejections; revisions 1–8 unchanged; the record regenerated and reviewed as an additive diff.
2. **Sequences** (§7): draws biased toward the joist spacing that keeps the count and the same-dimension section, and a deterministic outcome gate under the `ci` profile; still 40 sequences.
3. **AC2-08 by `it` and `test` titles** (§9), listed per bullet, including the ART-002 price-book cases for AC2-08.3 and `editors.spec.ts`'s untouched-tab case for AC2-08.2.
4. **Tightened reference checks** (§5.3) for both matrices: one occurrence as a test title, not skipped, and no skip mark on pytest functions unless quarantined.
5. **Documents and status** (§11), with VS-02 declared complete in the roadmap once §13 passes.

**Your judgment** (one at a time, in this order):

6. **Matrix form and drift check** (§5.1–5.2): a separate `vs-02-traceability.md`; one row per criterion bullet (17 AC rows) plus the 7 VS-02 contract checks; enforced against vs-02.md's IDs **and wording**, so a reworded criterion fails until its row is reviewed. *Alternatives:* one row per criterion; VS-02 sections in the VS-01 file; IDs only. **Approved as proposed (2026-11-20):** one row per bullet, checked against IDs and wording.
7. **Payload size budgets** (§8.1): each payload at most 256 KiB for the reference house and 2 MB for the largest supported case, in canonical bytes, gated in CI. *Alternatives:* no size budget; tighter ceilings. **Approved as proposed (2026-11-20).**
8. **Time budgets** (§8.2): ceilings at about 5–10× today (preview 1 s for the reference house and 5 s for the largest case; commit 5 s for the largest case; in the browser, 10 s to first render and 3 s to the preview dialog), median of 5, gated in CI, with a stop-and-report rule above half a ceiling. *Alternatives:* report only, with no ceiling; user-facing targets in a production build. **Approved as proposed (2026-11-20).**
9. **UI-003's four flagged choices** (§10), each confirmed as implemented, or changed in a UI change of its own: (a) untouched Connections rows disabled; (b) per-key dialog rows; (c) "Steel knife plate"; (d) the brace-fit pointer naming Footprint too. **Settled (2026-11-20): all four confirmed as implemented.** Recorded in UI-003 §17. No UI change follows.

Items 6–8 are approved and recorded as **[D063](../../product/decisions/D063-vs02-traceability-and-budgets.md)**.

## 13. Acceptance criteria and automated tests

1. **Matrix (AC2-09):** `vs-02-traceability.md` has a row for every item of the three sources, in the approved form, and `test_every_vs02_item_is_traced` passes. Removing or renaming a referenced test, skipping it, or rewording a criterion in vs-02.md (if item 6 is approved with the wording check) makes it fail. The VS-01 check still passes, with the tightened references.
2. **Golden scenario:** the record has the §6 steps and 12 revisions; revisions 1–8 are byte-identical to today's; 7a impacts exactly `mesh3d` and `plan2d`; the counts after 7b and the Joist hanger line after 7c are as §6 states; both rejections leave the project unchanged; undo reuses all four of revision 2's payloads; `golden.py --check` passes on both stores.
3. **Sequences:** under the `ci` profile, the outcome gate passes, and every VS-02 outcome in §7 is reached. The `thorough` profile still runs on demand.
4. **Budgets:** the checks approved in items 7 and 8 pass locally and in CI, and print their measurements.
5. **Browser traceability:** every AC2-08 row lists the §9 titles, each found once and not skipped.
6. **Everything else unchanged:** no product code changes; the UI fixture, vectors, schemas, and OpenAPI drift checks pass unchanged; `scripts/check.sh` passes locally, and the pull request's CI passes all four jobs.

## 14. Errors, security, and migration

- **Errors:** none new. A budget failure is a test failure with the measurement in its message.
- **Security:** no routes, permissions, or secrets. The budget tests use the in-memory store and test tokens.
- **Migration:** none. The golden record is regenerated as a reviewed diff (D055).

## 15. Implementation guidance (not prescriptive)

- **Order:**
  1. the tightened reference checks, against the VS-01 matrix first;
  2. the VS-02 matrix and its test, from §5.4;
  3. the golden steps, then the regenerated record;
  4. the sequence draws and the gate, then a statistics run;
  5. the budgets, measured in CI on the pull request before the ceilings are final.
- **Parsing vs-02.md:** take §12.1 from its heading to `### 12.2`, as `_section` does for the VS-01 sources. A bullet's text runs to the end of its line; none wraps.
- **The largest case:** `test_connections.py::_largest_doc` already builds it. Move it to a shared helper rather than copying it.
- **Collecting outcomes:** Hypothesis runs the test body once per example, so a module-level collector filled by the body and checked in a fixture's teardown is enough. Skip the check when `settings().max_examples` is not the `ci` profile's.
- **Measuring time:** `time.perf_counter()` around the service call, and in Playwright, `Date.now()` around the action and the awaited state, as in the drafting measurements.

## 16. Definition of done

- All §13 criteria are met, with the full backend suite, Vitest, Playwright, `tsc`, and the drift checks. `scripts/check.sh` and CI pass; the run is linked in the implementation notes.
- The judgment items are recorded in D063, and item 9's outcome in UI-003 §17. The §11 documents are updated.
- VS-02 is complete by its own acceptance criteria. The roadmap says so, and lists what remains open: the `main` ruleset, hosting and identity (open question 8), and any at-risk rows in either matrix.
- Changed files, tests, measurements, limitations, and next steps are summarized (AGENTS.md).

## 17. Implementation notes (2026-11-20)

**Delivered** (test-only; no product code changes):
- `docs/implementation/acceptance-tests/vs-02-traceability.md` (new): 24 rows, 17 for the §12.1 criterion bullets and 7 for the contract checks (D063). It starts from the §5.4 draft. AC2-08's rows cite `it` and `test` titles (§9). AC2-08.2 also notes the disabled untouched Connections rows, which item 9 confirmed. AC2-09 cites the new traceability tests, the outcome gate, and the size budgets.
- `backend/tests/test_traceability.py`:
  - `test_every_vs02_item_is_traced`: derives the 24 IDs from the three sources, with a count guard. It compares each row's criterion with its source after normalizing whitespace, bold markers, and links to their text, and applies TEST-001's reference checks.
  - `test_vs02_check_rejects_reworded_missing_and_untested_rows`: rewording, whitespace, a missing row, an untested row, and a renamed reference.
  - `reference_exists` is tightened for both matrices (§5.3). A title must occur once in its file, as the first argument of `it(`, `test(`, or `describe(`. A pytest function must be at module level with no `skip`, `skipif`, or `xfail` mark, on itself or in `pytestmark`, unless the matrix quarantines it; it is found with `ast`. A mark on one parametrized case does not count. `test_reference_checks_reject_missing_tests` gains cases for each rule, in temporary files. The VS-01 matrix passed unchanged.
- `integration/scenario.py`: steps 7a–7e (§6.1), with the counts after 7b (238 members, 382 connections), the Joist hanger line after 7c (144 each, unpriced, no amount; coverage `partial`, grand total `null`), the impact lists of 7a–7c, and each rejection's detail code and path.
- **Golden record regenerated** (D055). Revisions 1–8 are byte-identical. There are 18 steps and 12 revisions, and 12 of 44 post-creation artifacts are reused: 7a's schedule and estimate, plus the 10 before. The undo revision moves from sequence 9 to 12. Its artifact fingerprints equal revision 2's, as before. Its `snapshot_fingerprint` changes because its `parent_revision_id` is now revision 11, which is expected. Nothing else changed.
- `integration/test_sequences.py` (§7):
  - **the §7 draws:** half the joist-spacing draws stay within 10% above the stored spacing, and half the section swaps pick a section with the role's current dimensions;
  - **an outcome gate:** a module-scoped fixture checks it under the `ci` profile, and skips it when the run already failed. `test_outcome_gate_names_every_missing_outcome` checks the gate's rules.
  - **additions beyond §7** (see the findings):
    - the step right after an `AddSection` swaps a role to a same-dimension section when one exists;
    - half the connection-type draws pick the class's other allowed type;
    - half the `frame` draws put one parameter just outside its bounds;
    - a `grid_reidentify` kind re-identifies one line;
    - half of all steps are a targeted edit (`draw_targeted`), one for each outcome the gate requires.
- `backend/tests/test_budgets.py` (new, D063). The size check covers each payload, and the estimate both with a book pricing every line and with none. The time checks are the median of 5 runs through the service, in-process, with the in-memory store, after one untimed warm-up preview: the reference-house preview, the largest-case preview, and the largest-case commit with all four artifacts derived. The largest case is inserted into the store as its head revision, with a complete book and its artifacts derived, rather than reached through a series of grid, footprint, and frame commands. Each check prints its measurement, also without `-s`.
- `frontend/e2e/connections.spec.ts`: one budgets case. It takes 5 creations, from Create pressed until the paired views, 193 3D glyphs, and the schedule are shown, and 5 joist-spacing previews, from Preview pressed until the dialog's impact line shows, then Cancel. It prints the medians.
- `backend/tests/conftest.py`: `with_frame_parameters`, `grid_doc`, and `largest_doc`, moved from `test_connections.py` and `test_timber.py` (§15), and used by them, by `test_estimating.py`, and by the budgets. The Hypothesis `ci` and `thorough` profiles now set `deadline=None`. `test_robustness.py::test_random_fixture_mutations_never_raise` failed once in `check.sh` under load with a `FlakyFailure` (`DeadlineExceeded`: 261 ms on the first call, 29 ms on the second), and a flaky test is a bug (TEST-001 §8).
- **Documents:**
  - vs-02.md: its status block names the matrix, and the §12.2 `TEST-002` row is updated (§11);
  - artifacts.md §10 and dependencies.md §8: their notes point to the matrix rows;
  - `tests/README.md` (the golden record) and `backend/README.md` (statistics, budgets, the gate);
  - D063 is marked implemented, and the register's range now reads D001–D063;
  - this file and the roadmap.

**Measured:**

*The `ci` sequences* (`--hypothesis-show-statistics`): 40 passing and 23 invalid cases. Each cell is the share of the 63 generated cases in which the outcome occurs:

| Command | Accepted | Rejected | No-op | Impact sizes reached |
|---|---|---|---|---|
| `SetFrameParameters` | 22.2% | 9.5% | — | 2 (11.1%), 4 |
| `SetConnectionType` | 11.1% | 9.5% | 3.2% | 4 |
| `SetGableRoofParameters` | 30.2% | 22.2% | — | 2 (19.0%), 3 (22.2%) |
| `SetMemberSection` | 20.6% | — | — | 2 (17.5%), 3 |
| `SetTimberGrid` | 11.1% | 31.7% | — | 3 (3.2%), 4 |
| `AddSection` | 17.5% | 12.7% | — | 0 |
| `SetFootprintDimensions` | 14.3% | 52.4% | 1.6% | 4 |
| `SetStoryHeights` | 12.7% | 14.3% | — | 4 |
| `UndoToRevision` | 9.5% | — | 7.9% | 2, 3, 4 |

*Seed robustness:*
- Before the targeted edits, four random seeds (`--hypothesis-seed` 1–4, 40 examples) each missed one or two required outcomes.
- After them, all four seeds reach every outcome, and so does the derandomized run.

*Run time:*
- The 40 sequences took 4 min 5 s to 4 min 58 s alone while the draws were being tuned. With the final draws they took 6 min 55 s with four other runs sharing the machine; the whole backend suite took 7 min 22 s in `scripts/check.sh`.
- The run has more invalid cases than before (23, against 4–8), because the targeted edits draw more data.

*Budgets*: the local values are from `scripts/check.sh` on the development machine (the browser values were taken while another test run shared it). The CI values are from run CI_RUN.

| Check | Ceiling | Local | CI |
|---|---|---|---|
| Largest payload, reference house (`timber_schedule`) | 262,144 B | 173,680 B (66%) | the same (deterministic) |
| Largest payload, largest case (`timber_schedule`) | 2,000,000 B | 1,135,194 B (57%) | the same |
| Preview, reference house, width edit | 1 s | 122 ms (12%) | CI_PREVIEW_REF |
| Preview, largest case, width edit | 5 s | 885 ms (18%) | CI_PREVIEW_LARGE |
| Commit with all four artifacts derived, largest case | 5 s | 1,089 ms (22%) | CI_COMMIT |
| Browser: Create until views and schedule | 10 s | 2,531 ms | CI_CREATE |
| Browser: Preview until the dialog | 3 s | 453 ms | CI_DIALOG |

The estimate is 2,786 B with a book pricing every line and 2,588 B with none. The other payloads match ART-002 §17 exactly.

**Findings:**
- **§7's two draw changes were not enough to reach the outcomes the gate requires**:
  - The fixture has no two sections with the same dimensions, so a same-dimension swap first needs a same-dimension `AddSection`, which takes two draws in a row.
  - A run has about 120 steps, because Hypothesis favors short sequences, and most `frame` draws stay inside the bounds.
  - Hypothesis derives the derandomized seed from the test function's source. So every edit to the test body reshuffles all 40 sequences: adding the gate's fixture argument alone lost `SetTimberGrid` impact 3.
  - With only the §7 changes, each of five attempts missed one to three outcomes, and four random seeds each missed one or two.
  - With the targeted edits, the derandomized run and all four random seeds tried reach every required outcome. The sequences still draw every command at random in the other half of the steps.

**Limitations:**
- The time ceilings describe the in-process service and the e2e dev-server setup, not a production build or the HTTP layer (D063).
- The gate checks reach only under the `ci` profile. `thorough` runs it as before, without the gate.
