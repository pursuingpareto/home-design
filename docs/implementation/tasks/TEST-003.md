# TEST-003 — VS-02b traceability, the golden scenario's wall commands, sequences, and budgets

**Status:** Done (2026-11-23). Implementation notes are in §17. Judgment item 13 (§17: two CI times over half their ceilings) was settled with option (a) and recorded as an amendment to D090. Approved 2026-11-23: routine items 1–8 together. Judgment items 9–11 were approved as recommended and are recorded as [D090](../../product/decisions/D090-vs02b-budgets-and-named-wall-case.md). Item 12 confirmed UI-004's twelve choices as implemented, recorded in UI-004 §20 (§13).  
**Owner module:** tests and tooling: `backend/tests/`, `frontend/tests/`, `frontend/e2e/`, `tests/vectors/scenarios/`, `docs/implementation/acceptance-tests/`. No product code changes. Two architecture documents change wording only, as their contract checks become rows (§5.3).  
**Slice:** VS-02b  
**Depends on:** `MODEL-006`, `ASM-001`, `ART-003`, and `UI-004` (all done; `main` at `9ca3301`). Merges on its own, with CI passing ([vs-02b.md](../acceptance-tests/vs-02b.md) §16).  
**Unblocks:** declaring VS-02b complete (AC2b-11); drafting VS-03

## 1. Objective

VS-02b's behavior is implemented and tested task by task: 997 backend tests, 137 Vitest tests, and 31 Playwright tests, with the drift checks (UI-004 §20). The if-and-only-if impact property runs over all five artifacts in the sequences, the invariants, and the golden scenario (ART-003 §8.4). Five things are missing before VS-02b can be called done:

1. **Proof of coverage.** No document maps AC2b-01 to AC2b-11 to tests. ART-003 wrote its VS-02b contract checks in artifacts.md §10 and dependencies.md §8 as prose, "traced by `TEST-003`", so that the VS-02 parser's 24 items did not change.
2. **The golden scenario's wall commands.** The golden record runs on the v3 house, but no step sends `SetWallAssembly`, `AddOpening`, `SetOpening`, or `RemoveOpening` (MODEL-006 §15, ART-003 §8.4).
3. **The sequences.** They do not draw the four wall commands (MODEL-006 §15: "The sequences do not send the four new commands yet (`TEST-003`)"). They also never check that walls, wall framing, and openings keep their IDs, or that an opening never moves silently (§7.3).
4. **Budgets.** The stud infill house's sizes are reported but not gated (D086 left the choice to this task, ART-003 §9.4). VS-02b has no largest supported case for walls: this task measured a valid snapshot whose payloads exceed D063's 2 MB ceiling (§8.2). UI-004's three browser timings are reported, not gated (UI-004 §13).
5. **UI-004's twelve flagged choices** (UI-004 §20), still open, as UI-003's four were before TEST-002.

After this task:
- every VS-02b criterion bullet and contract check maps to named tests, and a test enforces the map against vs-02b.md's IDs and wording;
- the golden record covers the four wall commands, a rejection of each (one of them a fit rejection through `SetWallAssembly`), and their reuse on undo;
- the `ci` sequences draw the four wall commands, and a gate keeps them reaching their outcomes;
- payload size and time budgets cover the new payloads and flows, in the form §13 settles;
- VS-02b is complete by its own acceptance criteria.

## 2. Inputs and governing documents

- **Acceptance criteria:** [vs-02b.md](../acceptance-tests/vs-02b.md) §15 (AC2b-01 to AC2b-11) and §16 (the `TEST-003` row). Routine item 15 (vs-02b.md §6) is already approved: "A separate `vs-02b-traceability.md`, one row per criterion bullet, checked against this file's IDs and wording, as D063 set for VS-02", with D063's per-payload ceilings applied to every payload and the stop-and-report rule when a measurement passes half a ceiling.
- **VS-02b contract checks** (prose today; §5.3 turns them into bullets):
  - [artifacts.md §10](../../architecture/artifacts.md#10-acceptance-tests-additions-to-vs-01), "VS-02b reconciliation";
  - [dependencies.md §8](../../architecture/dependencies.md#8-vs-01-examples-and-tests), "VS-02b examples".
- **The pattern this task follows:** [TEST-002](TEST-002.md) (the VS-02 matrix, the golden steps 7a–7e, the outcome gate, the budgets), [vs-02-traceability.md](../acceptance-tests/vs-02-traceability.md), `backend/tests/test_traceability.py`, and [D063](../../product/decisions/D063-vs02-traceability-and-budgets.md).
- **Decisions:** D055 (records regenerated as reviewed diffs), D056 (impact is exact), D063 (matrix form and budgets), D068 (`SetWallAssembly`), D069 (openings), D077 (openings have no size bounds beyond the fit), D086 (the stud infill gate is left to `TEST-003`), D087–D089 (the browser).
- **Implementation notes, and where each test lives:** [MODEL-006](MODEL-006.md) §15, [ASM-001](ASM-001.md) §15 (the largest case's piece counts and times), [ART-003](ART-003.md) §8.3 (measured impact) and §17 (sizes and times for both families), [UI-004](UI-004.md) §13 (what this task needs) and §20 (browser tests, test hooks, timings, and the twelve flagged choices).
- **Code:** `backend/tests/integration/` (`scenario.py`, `invariants.py`, `test_sequences.py`, `golden.py`), `backend/tests/test_traceability.py`, `backend/tests/test_budgets.py`, `backend/tests/conftest.py` (`largest_doc`, `with_assembly`, `STUD_INFILL`), `frontend/tests/ui004.test.tsx`, `frontend/tests/art003.test.tsx`, `frontend/e2e/walls.spec.ts`, `frontend/e2e/connections.spec.ts` (D063's browser budget case).

## 3. Scope

**In scope**

- A VS-02b traceability matrix and its enforcement, with the contract checks as bullets (§5).
- The VS-02 matrix's AC2-01 row, which AC2b-01 replaces (§5.5).
- New steps in the golden scenario, and its regenerated record (§6).
- The four wall commands in the sequences, new invariants, and an extended outcome gate (§7).
- Payload size and time budgets for the new payloads and flows (§8).
- How the browser tests trace AC2b-10 (§9), and closing UI-004's twelve flagged choices (§10).
- Documents and status (§11).

**Non-goals**

- Any product behavior, payload, command, validation rule, or API change. If a test exposes a defect, it is reported and fixed in its own change. In particular, **bounds on openings** (a minimum size, or a maximum per wall), which §8.2 shows are missing, are a product decision for a task of their own (item 10).
- Re-implementing exact impact (ART-003) or the wall rule (ASM-001).
- Tracing task-file acceptance lists row by row. The matrix traces vs-02b.md §15 and the VS-02b contract checks, as TEST-002 did for VS-02.
- Performance work. A failing budget is a finding for the product owner, not a reason to tune.

## 4. Where VS-02b stands (measured while drafting, against `9ca3301`)

**Already in place:**
- **Sequences** (`test_sequences.py`) draw the nine VS-02 command types and check exact impact over five artifacts at every accepted step. `check_walls` (`invariants.py`) checks walls, openings, and wall framing in the plan, the mesh, and the assembly schedule against the snapshot after every step.
- **Golden scenario:** 18 steps and 12 revisions on the v3 house, with the assembly schedule in every step (ART-003 §9.3). The grid step `grid-x-4` already removes 4 openings with the 4 walls of the `x2`–`x3` bay (measured below), but nothing asserts it.
- **Browser:** `ui004.test.tsx` (41 cases, one `describe` per UI-004 §16 test number), `walls.spec.ts` (6 cases in `test.describe("9. UI-004 end to end")`, plus the ART-003 price-book case and a reported-timings test), and `art003.test.tsx` (7 cases).

**What the `ci` sequences reach today** (`uv run pytest tests/integration/test_sequences.py --hypothesis-show-statistics`, local, idle machine): 40 passing and 11 invalid cases, 5 min 4 s. No wall command is drawn. Every gated outcome is reached. Measured shares are close to MODEL-006 §15's table: for example `SetFootprintDimensions` accepted in 11.8% and rejected in 37.3% of the generated cases, `SetTimberGrid` impacts 5 in 17.6%.

**The golden house at the point the new steps go in** (after step 7e; measured by running `Scenario.run` up to that step, `uv run python` from `backend/`):
- 76' × 24', four 19' bays along X (`x0`, `x1`, `x2`, `x4`, `x3`) and two 12' bays along Y, stories 10' and 10';
- straw bale, 24 walls, **16 openings** (the 4 of the `x2`–`x3` walls went with step `grid-x-4`), 63 buck pieces;
- knee braces on Level 1 beams only (eave braces off since 7b), so Level 0 walls have braces in their top corners and Level 1 walls none;
- 238 members, 382 connections; the estimate `partial` with no total (the 10x12 beams and the joist hangers are unpriced).

**Gaps found:**
- No VS-02b matrix; the VS-02b contract checks are prose that no parser reads (§5).
- **The `walls.spec.ts` end-to-end group cannot be referenced by its `describe` title.** It is `test.describe("9. UI-004 end to end")`, and `_title_exists` accepts only `it(`, `test(`, or `describe(` not preceded by a word character or a dot. Checked with `reference_exists`: the describe title fails, and every case title inside it passes (§9).
- The VS-02 matrix's AC2-01 row ("version 2 only") names tests that now create version 3 projects (§5.5).
- No golden step sends a wall command (§6).
- The sequences never draw a wall command, and `check_transition` compares member and connection IDs only: wall, wall framing, and opening identity is not checked between steps (§7).
- **One VS-02b example in dependencies.md §8 is not general.** It says that after moving an opening, "the estimate's sums are unchanged there, so it is reused". On the golden house, moving the new window of §6 (step 7h) changes `wallframing.BUCK_SILL.1.5x18` from 15.240000000000004 m to 15.24 m, so the estimate is impacted, exactly (D056). On the reference house the same edit happens to leave every sum bit-identical (ART-003 §8.3). §5.3 corrects the sentence.
- **No largest supported case exists for walls** (§8.2), and the stud infill house is not gated (§8.1).
- **The largest case's sizes differ between machines.** CI's backend job on PR #20 printed `mesh3d` 949,138 and `timber_schedule` 1,135,024 bytes for the largest case; this machine measures 951,115 and 1,135,194. The reference house's sizes are identical on both. TEST-002 §17 recorded the CI sizes as "the same (deterministic)". The likeliest cause is last-bit differences in the platform's math library (the roof's trigonometry) that change the length of some printed doubles; that is not verified here. The golden record and vectors are unaffected, because they use the reference house. §8 treats the CI number as the gated one.

## 5. The VS-02b traceability matrix (items 1–3)

### 5.1 Form (item 1, routine; vs-02b.md §6 item 15 and D063)

A new document, `docs/implementation/acceptance-tests/vs-02b-traceability.md`, beside the VS-01 and VS-02 matrices, which stay enforced (AC2b-08).

- **AC rows,** one per criterion bullet of vs-02b.md §15, numbered in order (`AC2b-02.1`); a criterion without bullets is one row: AC2b-01; AC2b-02.1–2; AC2b-03.1–3; AC2b-04.1–3; AC2b-05.1–3; AC2b-06.1–3; AC2b-07; AC2b-08; AC2b-09; AC2b-10.1–3; AC2b-11. **22 rows.** AC2b-11 is the traceability criterion itself, traced as AC2-09 was.
- **Contract rows:** `ART2b-1` to `ART2b-5` and `DEP2b-1` to `DEP2b-6` (§5.3). **11 rows.**
- **33 rows** in all. Reference forms, `N/A —` rows, and `[quarantined: <issue>]` are the VS-02 matrix's.

### 5.2 The check (item 1, routine; test-only)

`test_traceability.py` gains `test_every_vs02b_item_is_traced`, and the VS-02 functions are generalized rather than copied:

- **Sources:** vs-02b.md from `## 15.` to `## 16.`, with criterion lines `- **AC2b-NN: …` and their indented bullets, read as `vs02_source_items` reads vs-02.md §12.1 (a parameter for the path, section bounds, and prefix); and the two bullet lists of §5.3.
- **A count guard** of 33, as the VS-02 check's 24.
- **Wording:** each row's criterion equals its source after `normalize` (whitespace, bold markers, links to their text). §15 has no links, so its text is compared as written.
- **References:** `reference_problems`, unchanged, so the VS-01 and VS-02 rules apply.
- `test_vs02b_check_rejects_reworded_missing_and_untested_rows`: rewording, whitespace, a missing row, an untested row, and a renamed reference, as for VS-02.

### 5.3 The VS-02b contract checks become bullets (item 2, routine)

The two prose paragraphs ART-003 wrote become bullet lists **with the same sentences**, one bullet per check, so that the matrix can trace them:

| ID | artifacts.md §10, "VS-02b reconciliation" |
|---|---|
| ART2b-1 | Plan, mesh, and assembly schedule walls, openings, and pieces are exactly the snapshot's, by ID; each on its level's plane; each mesh box's axis its record's |
| ART2b-2 | Each wall's length, opening area, and net area follow its records; totals, per-layer areas (D082), volumes, and framing aggregates reconcile with the rows; `has_jacks` agrees with the pieces |
| ART2b-3 | The estimate's assembly and wall framing lines equal the schedule's aggregates, counts beside lengths; its assumptions are the timber schedule's, then the assembly schedule's |
| ART2b-4 | The assembly schedule's envelope carries `CLIMATE_DETAILS_UNVERIFIED` |
| ART2b-5 | The four wall commands impact exactly the artifacts whose payloads they change, and never `timber_schedule` |

| ID | dependencies.md §8, "VS-02b examples" |
|---|---|
| DEP2b-1 | An opening added, removed, or narrowed impacts `plan2d`, `mesh3d`, `assembly_schedule`, and `preliminary_estimate` |
| DEP2b-2 | Moving an opening along its wall impacts the two views and `assembly_schedule`; its sill height alone, `mesh3d` and `assembly_schedule` (piece lengths and face areas change in their last bit) |
| DEP2b-3 | **Corrected (§4):** the estimate is reused when its sums are unchanged; a piece that really changes length, or a summed length that changes in its last bit, impacts it |
| DEP2b-4 | `SetWallAssembly` impacts every artifact but `timber_schedule` |
| DEP2b-5 | A frame edit that moves no wall piece (straw bale: brace leg, eave braces, connection type) impacts every artifact but `assembly_schedule` |
| DEP2b-6 | No wall edit impacts `timber_schedule` |

- The sentences are kept as ART-003 wrote them, split at their semicolons where one sentence holds two checks. **DEP2b-3 is the one change of meaning:** "so it is reused, unless a stud infill piece really changes length" becomes the measured rule. It describes behavior that is already implemented and exact (D056); nothing in the code changes.
- **The VS-02 parser must stop at them.** `vs02_source_items` reads ART2 from "Version 2 reconciliation" to the next `## ` heading, and DEP2 from "VS-02 examples" likewise, so new bullets after them would be counted as ART2 and DEP2 items. The section ends become "VS-02b reconciliation" and "VS-02b examples", and the VS-02 count guard (24) proves the VS-02 items are unchanged.

*Alternative:* leave the prose and trace each paragraph as one row (ART2b-1, DEP2b-1). Two rows instead of eleven, but each would then pass while one of its sentences had no test, which is what D063's per-bullet rule exists to prevent.

### 5.4 First draft of the rows

Candidate tests, from the task files' implementation notes. **Every reference below was checked with `test_traceability.reference_exists` while drafting (150 references; all pass but the `test.describe` title, §9).** The implementation confirms each one, adds the new tests of §6–8, and may replace a candidate with a better one. `GOLDEN` and `SEQ` are as in TEST-002 §5.4; `GATE` is `integration/test_sequences.py::test_outcome_gate_names_every_missing_outcome`. Backend paths are shortened (`test_x.py::` for `backend/tests/test_x.py::`, `::` alone for the file just named).

| ID | Criterion (short) | Candidate tests |
|---|---|---|
| AC2b-01 | Version 3 only; version 2 rejected | `test_commands.py::test_created_project_equals_fixture_exactly`, `test_walls_model.py::test_version_2_is_rejected`, `::test_record_versions_are_per_kind`, `test_project.py::test_migration_refuses_a_database_with_version_2_projects`, `test_fixture.py::test_committed_schema_is_current`, `test_wall_rule.py::test_created_project_equals_fixture_apart_from_ids` |
| AC2b-02.1 | Both definitions, layers, framing values | `test_wall_rule.py::test_template_definitions`, `::test_template_text_is_d081_exactly`, `test_walls_model.py::test_model_006_examples_validate_against_the_committed_schema`, `test_assembly_schedule.py::test_only_definitions_in_use_are_listed_with_their_values_as_stored`, `ui004.test.tsx › selects the assembly, shows the chosen build-up, and previews SetWallAssembly` |
| AC2b-02.2 | Declared with provenance or `null`; never 0 | `test_walls_model.py::test_declared_values`, `test_assembly_schedule.py::test_reference_house_has_no_thermal_figures_and_names_the_missing_inputs`, `ui004.test.tsx › shows the assembly schedule: warning and details, declared values, figures, walls, openings, takeoff, and pieces` |
| AC2b-03.1 | 20 walls, deterministic, stable IDs | `test_wall_rule.py::test_fixture_inventory_is_exactly_the_rule_output`, `::test_wall_counts_per_grid`, `::test_determinism_across_orderings`, `::test_oracle_walls_are_bit_identical`, `::test_keys`, `test_walls_model.py::test_identity_footprint`, `::test_identity_story_heights`, `::test_identity_frame_only_edits`, `::test_golden_grid_step_keeps_the_x0_x2_walls`, `SEQ` (§7.3) |
| AC2b-03.2 | Wall framing deterministic, stable IDs | `test_wall_rule.py::test_stud_infill_inventory`, `::test_worked_example_stud_infill`, `::test_worked_example_straw_bale`, `::test_five_foot_window_and_door`, `::test_every_opening_cuts_its_mid_height_girt`, `::test_jacks_appear_exactly_above_the_threshold`, `::test_properties_on_the_fixture_and_stud_infill`, `::test_rectangles_agree_with_pieces_on_the_fixture_and_stud_infill`, `::test_zero_length_cases_generate_nothing`, `::test_conformance_codes_for_each_piece_kind`, `test_walls_model.py::test_identity_brace_parameters`, `::test_identity_opening_commands`, `GOLDEN` (§6), `SEQ` (§7.3) |
| AC2b-03.3 | `SetWallAssembly` validated, consequential; 193 and 312 unchanged | `test_walls_model.py::test_set_wall_assembly`, `::test_set_wall_assembly_needs_a_preview`, `::test_identity_set_wall_assembly`, `::test_classification_of_the_new_commands`, `test_commands.py::test_classification_table_matches_dependencies_doc`, `GOLDEN` (steps 7g, 7i), `SEQ` |
| AC2b-04.1 | Opening commands routine, stable IDs, rough openings | `test_walls_model.py::test_opening_commands`, `::test_opening_command_errors_carry_their_paths`, `::test_remove_and_undo_restore_original_ids`, `::test_classification_of_the_new_commands`, `::test_new_commands_never_raise`, `GOLDEN` (steps 7f, 7h, 7l), `SEQ` (§7.3) |
| AC2b-04.2 | Fit rejected from its command, a frame edit, or `SetWallAssembly` | `test_walls_model.py::test_fit_boundaries`, `::test_openings_overlap_boundary`, `::test_fit_through_frame_edits`, `::test_girt_fit_edge_case`, `::test_every_new_code_is_reached`, `test_impact.py::test_move_y1_to_0_3_is_rejected_by_the_fit`, `ui004.test.tsx › places server details on their fields, naming the other opening of an overlap`, `walls.spec.ts › a fit rejection from a frame edit: …`, `GOLDEN` (steps 7g, 7j, 7k), `SEQ`, `GATE` (§7.4) |
| AC2b-04.3 | Openings removed with their wall listed in the preview | `test_walls_model.py::test_openings_are_removed_with_their_wall`, `::test_preview_diff_shape`, `ui004.test.tsx › lists the 8 windows a re-identified grid line removes, above Confirm (D088)`, `walls.spec.ts › removed openings: …`, `GOLDEN` (step `grid-x-4`, §6.2) |
| AC2b-05.1 | Areas reconcile: 2,016 sf net; layers | `test_assembly_schedule.py::test_reference_house_areas`, `::test_wall_rows_follow_the_records`, `::test_aggregates_reconcile_with_the_rows`, `::test_layer_aggregates_and_the_fill_net_of_framing`, `test_geometry.py::test_assembly_quantities_match_independent_ecmascript_implementation`, `SEQ` |
| AC2b-05.2 | Framing counts and lengths reconcile | `test_assembly_schedule.py::test_framing_aggregates`, `::test_has_jacks_follows_the_pieces`, `test_wall_rule.py::test_stud_infill_inventory`, `GOLDEN` (step 7i), `SEQ` |
| AC2b-05.3 | Per m², per m; never 0 | `test_estimating.py::test_wall_lines_carry_their_schedule_fields_and_exact_amounts`, `::test_frame_only_book_leaves_the_six_wall_lines_unpriced`, `::test_wall_assembly_switch_turns_bucks_into_unused_rows`, `::test_wall_families_need_their_units`, `::test_m2_rows_are_accepted_for_assembly_keys`, `::test_no_book_is_unavailable_never_zero`, `art003.test.tsx › prices assembly lines per square meter, with the per-square-foot equivalent`, `GOLDEN` (step 7i: unpriced stud infill lines, no total) |
| AC2b-06.1 | Framing fraction from the pieces; the named method | `test_assembly_schedule.py::test_faces_overlap_only_at_girt_crossings_and_count_once`, `::test_reference_house_framing_fractions`, `::test_parallel_path_arithmetic`, `::test_a_wall_without_framing_still_needs_the_framing_path` |
| AC2b-06.2 | A figure only when every input is known | `test_assembly_schedule.py::test_reference_house_has_no_thermal_figures_and_names_the_missing_inputs`, `::test_missing_framing_conductivity_leaves_only_the_center_of_cavity`, `ui004.test.tsx › shows test-only declared figures as served in metric and converted in imperial, each with its unit` |
| AC2b-06.3 | Climate details unverified; no compliance claim | `test_assembly_schedule.py::test_envelope_is_preliminary_and_flags_climate_details`, `::test_climate_warning_is_on_every_envelope_whatever_its_status`, `test_geometry.py::test_no_capacity_size_or_fastener_fields`, `ui004.test.tsx › keeps the banner, shows the climate warning and the method notes, and never shows a thermal figure as 0` |
| AC2b-07 | Exact impact, new artifact and commands too | `test_impact.py::test_measured_wall_impact`, `::test_measured_impact`, `::test_undo_reuses_every_payload_of_its_target`, `::test_noop_impacts_nothing`, `test_artifacts.py::test_unchanged_artifacts_are_copied_without_deriving`, `SEQ` (§7), `GATE`, `GOLDEN` |
| AC2b-08 | Earlier slices still hold | `test_traceability.py::test_every_vs01_item_is_traced`, `::test_every_vs02_item_is_traced`, `test_api.py::test_ui_fixtures_are_current`, `test_fixture.py::test_committed_schema_is_current`, `test_wall_rule.py::test_fixture_check_passes`, `GOLDEN` |
| AC2b-09 | Still preliminary; assumption lines | `test_assembly_schedule.py::test_assumptions_in_order`, `::test_envelope_is_preliminary_and_flags_climate_details`, `test_artifacts.py::test_envelope_contract_and_fingerprint`, `test_geometry.py::test_no_capacity_size_or_fastener_fields`, `ui004.test.tsx › keeps the banner, …` |
| AC2b-10.1–3 | Browser | §9 |
| AC2b-11 | Traceability; golden, sequences, budgets, CI | `test_traceability.py::test_every_vs02b_item_is_traced` (new), `::test_vs02b_check_rejects_reworded_missing_and_untested_rows` (new), `GOLDEN`, `SEQ`, `GATE`, `test_budgets.py::test_payload_sizes_are_within_budget` |
| ART2b-1 | Inventory by ID, planes, box axes | `test_assembly_schedule.py::test_rows_are_exactly_the_snapshots_records_in_order`, `test_geometry.py::test_walls_and_framing_are_on_their_levels_planes`, `::test_framing_boxes_follow_the_orientation_rule`, `::test_wall_views_match_independent_ecmascript_implementation`, `GOLDEN`, `SEQ` |
| ART2b-2 | Areas, aggregates, `has_jacks` | `test_assembly_schedule.py::test_wall_rows_follow_the_records`, `::test_aggregates_reconcile_with_the_rows`, `::test_layer_aggregates_and_the_fill_net_of_framing`, `::test_has_jacks_follows_the_pieces`, `SEQ` |
| ART2b-3 | Estimate lines equal aggregates; assumptions | `test_estimating.py::test_wall_lines_carry_their_schedule_fields_and_exact_amounts`, `test_assembly_schedule.py::test_assumptions_in_order`, `SEQ` |
| ART2b-4 | Climate warning on the envelope | `test_assembly_schedule.py::test_envelope_is_preliminary_and_flags_climate_details`, `::test_climate_warning_is_on_every_envelope_whatever_its_status` |
| ART2b-5 | Wall commands impact exactly; never the timber schedule | `test_impact.py::test_measured_wall_impact`, `GOLDEN` (§6), `SEQ` (§7) |
| DEP2b-1 | Add, remove, narrow: four artifacts | `test_impact.py::test_measured_wall_impact` (the add, remove, and width cases), `GOLDEN` (steps 7f, 7l) |
| DEP2b-2 | Offset or sill only | `test_impact.py::test_measured_wall_impact` (offset only, sill only), `SEQ` (§7.4: `SetOpening` impacts 2 and 3) |
| DEP2b-3 | Estimate reused only when its sums are unchanged | `test_impact.py::test_measured_wall_impact` (offset only, sill only on stud infill), `GOLDEN` (step 7h: a last-bit sum change) |
| DEP2b-4 | `SetWallAssembly`: all but the timber schedule | `test_impact.py::test_measured_wall_impact`, `GOLDEN` (step 7i) |
| DEP2b-5 | A frame edit that moves no wall piece | `test_impact.py::test_measured_wall_impact` (brace cases, straw bale), `GOLDEN` (steps 7a–7c) |
| DEP2b-6 | No wall edit impacts the timber schedule | `test_impact.py::test_measured_wall_impact`, `GOLDEN` (§6), `SEQ` (§7.3) |

`test_measured_wall_impact` is parametrized; as in the VS-02 matrix, the row names the case in a short note after the reference.

### 5.5 The VS-02 matrix's AC2-01 row (item 3, routine)

AC2b-08 says "AC2b-01 takes the place of AC2-01". The VS-02 row still names `test_created_project_equals_fixture_exactly` and others, which now create version 3 projects, so the row passes while proving something else. Its tests cell becomes `N/A — replaced by AC2b-01 (vs-02b.md AC2b-08); traced in the VS-02b matrix.` The criterion text stays, so the VS-02 wording check still passes. The VS-02 matrix's other rows hold against the v3 house and are unchanged.

*Alternative:* keep the row's tests. It costs nothing, but a reader of the VS-02 matrix would take "version 2 only" as proven today.

## 6. The golden scenario's wall commands (item 4, routine)

### 6.1 New steps

Inserted after step 7e and before step 8 (the retry and the conflict), as TEST-002 inserted 7a–7e, so the final undo to revision 2 crosses them and the records of revisions 1–11 do not change. The house is §4's. **Every outcome below was measured** by running `Scenario.run` to step 7e and then sending each step through the same `routine`, `consequential`, and `rejected` helpers (`uv run python` from `backend/`, on `9ca3301`). IDs are minted by the scenario's fixed UUIDs, so the opening IDs below are as measured.

| Step | Command | Outcome | `impacted_artifacts` | Shows |
|---|---|---|---|---|
| 7f `add-window-near-brace` | `AddOpening` (routine): a 3'-0" × 4'-0" window, sill 3'-0", offset 6" in `wall/axis-x/y0/x4-x3/level-0` | Committed without a token. 17 openings; +4 buck pieces (67) | all but `timber_schedule` | A routine opening command; the timber schedule is reused |
| 7g `assembly-stud-infill-crosses-brace` | `SetWallAssembly {stud-infill}` | 422 `UNSUPPORTED_CONFIGURATION`; one detail, `OPENING_CROSSES_BRACE` at the 7f window's `offset_m`, with `args.assembly_definition_id` first in `related_paths` | — | A framed opening that fits with bucks but not with kings and a header is rejected through `SetWallAssembly`, naming the opening and the argument (AC2b-04.2). Nothing moves the window |
| 7h `center-window` | `SetOpening` (routine): the same window at offset 8'-0", centered | Committed. 4 pieces updated | all but `timber_schedule` | Moving an opening along its wall. The estimate is impacted because `wallframing.BUCK_SILL.1.5x18`'s total changes in its last bit (15.240000000000004 → 15.24 m): exact under D056 (DEP2b-3) |
| 7i `assembly-stud-infill` | `SetWallAssembly {stud-infill}` (consequential) | Committed. Walls 24 updated; wall framing +311 −67: 164 studs, 41 girts, 34 kings, 2 jacks, 17 headers, 16 rough sills, 37 cripples. Members 238 and connections 382 unchanged. The estimate `partial`, `grand_total_minor` `null`, `PRICE_ROWS_UNUSED` (the buck rows) | all but `timber_schedule` | AC2b-03.3 and AC2b-05.3: the switch, the frame untouched, the stud infill lines unpriced and never 0 |
| 7j `window-level-1-8ft` | `SetOpening`: the south-west Level 1 window (`wall/axis-x/y0/x0-x1/level-1`), height 8'-0" | 422 `UNSUPPORTED_CONFIGURATION`; one detail, `OPENING_OUTSIDE_WALL` at its `height_m`, with `args.height_m` first in `related_paths` | — | An opening command's fit rejection, on a wall without braces, so one detail |
| 7k `overlapping-window` | `AddOpening`: the 7f window again, at offset 9'-0" | 422 `UNSUPPORTED_CONFIGURATION`; `OPENINGS_OVERLAP` at the new opening's `offset_m`, with `args.offset_m` and the 7f window's `offset_m` | — | Overlap names both openings |
| 7l `remove-north-window` | `RemoveOpening` (routine): the fixture's window in `wall/axis-x/y2/x0-x1/level-1` | Committed. 16 openings; wall framing +1 −7, 1 updated (its two girt pieces become one, its cripples a stud); 305 pieces | all but `timber_schedule` | Removing a fixture opening that the undo then restores |
| 7m `remove-north-window-again` | `RemoveOpening`: the same ID | 422 `VALIDATION_FAILED`; `DANGLING_REFERENCE` at `args.opening_id` | — | A stale opening ID changes nothing |

**The undo to revision 2** (step 9) then impacts all five artifacts and **reuses all five of revision 2's payloads** (measured: equal input fingerprints for all five). It restores straw bale and revision 2's 20 openings with their original IDs: the fixture window removed in 7l returns, and the 7f window is gone (measured).

**Assertions added to the scenario:**
- step `grid-x-4`: its preview lists **4 openings removed with their walls** in `changes` (`after: null`, `field: ""`), and `walls` reads 8 added, 4 removed, 8 updated (measured; AC2b-04.3);
- 7g, 7j, 7k, 7m: each rejection's single detail code and path, and the argument in `related_paths`;
- 7i: the piece counts per kind, the unchanged member and connection counts, and the estimate's coverage, total, and `PRICE_ROWS_UNUSED`;
- 7f, 7h, 7i, 7l: the impact lists (four types each, never `timber_schedule`);
- step 9: revision 2's opening IDs and default assembly restored.

`check_revision`, `check_impact`, the new `check_transition` rules (§7.3), and the replay already run after every step.

### 6.2 The regenerated record (D055)

- **Revisions:** 12 → 16. Revisions 1–11 are byte-identical. The undo revision moves from sequence 12 to 16; its artifact fingerprints stay equal to revision 2's.
- **Steps:** 18 → 26 (four commits, four rejections).
- **Not changed:** the UI fixture, `vectors.json`, schemas, and OpenAPI.

The diff is reviewed as additive. Any change to revisions 1–11 is a finding.

*Alternatives:*
- **`SetWallAssembly` rejected for a dangling or wrong-kind ID** (measured: `DANGLING_REFERENCE` or `WRONG_REFERENCE_KIND` at `args.assembly_definition_id`, `VALIDATION_FAILED`). Simpler, but it proves only argument validation; the fit through `SetWallAssembly` is the part of AC2b-04.2 that no golden step covers today. The sequences draw the wrong-kind case (§7.2).
- **An offset that leaves every sum bit-identical**, so 7h reuses the estimate. It would match the old DEP2b-3 wording, but it would pin a lucky case; the measured last-bit change is the more honest record of D056.
- **A frame edit rejected by the fit** in the golden scenario. `test_fit_through_frame_edits`, the Playwright `GIRT_CROSSES_BRACE` case, and the gate (§7.4) cover it.

## 7. The sequences draw the wall commands (item 5, routine; test-only)

### 7.1 Why not just add four kinds

TEST-002 §17 found that Hypothesis derives the derandomized seed from the test's source, so any edit to the test reshuffles all 40 sequences, and outcomes that only one branch reaches are missed by many seeds. The approach that worked there is kept: half the steps are a targeted edit, one per required outcome.

### 7.2 Draws

New kinds in `draw_command`, and new targets in `draw_targeted`, all from the current view's walls and openings (in key and ID order, so draws are deterministic):

- **`add_opening`:** a wall; half the draws a D072-sized window (3'-0" × 4'-0", sill 3'-0") centered, which usually fits; the rest width 1'–8', height 1'–8', sill 0–6', offset from −1' to the wall's length, with the kind drawn (a door's sill 0 or not).
- **`set_opening`:** an existing opening, with one field changed: offset only, sill only (height kept, so its head moves), height only, or width, each within ±1' for half the draws and anywhere in the ranges above for the rest.
- **`remove_opening`:** an existing opening; a quarter of the draws an opening ID from an earlier revision that the view no longer holds (rejected, `DANGLING_REFERENCE`).
- **`wall_assembly`:** the other definition; a quarter of the draws a `Section`'s ID (rejected, `WRONG_REFERENCE_KIND`).
- **The step after an accepted `SetWallAssembly` to stud infill** makes a brace-leg edit within ±6", as TEST-002 made the swap after an `AddSection`: on stud infill, studs end on braces, so it impacts all five artifacts (ART-003 §8.3).
- **A targeted fit rejection:** an `AddOpening` that overlaps an existing opening in its wall.

The house has openings in most walls, so a frame edit that shrinks a bay is often rejected by the fit already (MODEL-006 §15); no draw is added for that.

### 7.3 New invariants (test-only)

`check_transition` gains, for accepted steps other than `UndoToRevision`:
- **walls and wall framing** keep their IDs for surviving generation keys, as members and connections do (AC2b-03.1–2);
- **openings never move silently** (AC2b-04, principle 3): an opening in both revisions is identical (wall, kind, dimensions, offset) unless the step is a `SetOpening` on it; an opening that disappears is either the target of a `RemoveOpening` or on a wall the step removed; only an `AddOpening` adds one. The step's command is passed in to decide this.

`check_walls` already checks the views and the schedule against the snapshot.

### 7.4 The outcome gate

- `COMMAND_TYPES` gains the four wall commands, and none is in `NEVER_REJECTED`: each must be accepted and rejected at least once.
- `REQUIRED_IMPACTS` gains `AddOpening {4}`, `RemoveOpening {4}`, `SetOpening {2, 3, 4}` (sill only; height only or offset only; width), `SetWallAssembly {4}`, and `SetFrameParameters` becomes `{2, 5}` (5: the brace edit on stud infill).
- **A fit outcome:** a rejection whose details include `OPENING_OUTSIDE_WALL`, `OPENING_CROSSES_BRACE`, `OPENINGS_OVERLAP`, or `GIRT_CROSSES_BRACE` also records `"rejected (fit)"`. The gate requires it for `AddOpening`, `SetOpening`, and at least one of the frame commands (`SetFootprintDimensions`, `SetStoryHeights`, `SetTimberGrid`, `SetFrameParameters`).
- `test_outcome_gate_names_every_missing_outcome` is extended to the new rules.
- **Still 40 sequences.** The run time is measured again and reported; it was 5 min 4 s before this task (§4). Wall-command previews take 130–350 ms each on the golden and reference houses (measured above and in §8.3), close to the frame commands', so the run should grow by well under a minute. If the 40 sequences no longer reach every outcome with this draw, the implementation adds targeted draws, as TEST-002 did, and says so; it does not lower the count or drop a requirement.

## 8. Budgets (items 9–11)

No product document sets a size or time target (D063). Routine item 15 of vs-02b.md already applies D063's ceilings to every payload of the reference house and of "the largest supported case". This section asks what those words mean for walls.

**How measured:** RFC 8785 canonical bytes, by `test_budgets.payload_sizes`, which builds each payload from a snapshot, the estimate with a book that prices every line. Snapshots were built with `conftest`'s helpers (`largest_doc`, `with_assembly`, `with_frame_parameters`, `regenerate`) and validated with `validate_bytes` (the fit included); every case below is valid. Times are the median of 5 through the service, in-process, with the in-memory store, after one untimed warm-up, as `test_budgets.py` does. The machine is an Apple A18 Pro, otherwise idle. CI numbers are from the backend and e2e jobs of PR #20's run 45072276767, the last CI run on `main`'s code.

### 8.1 The stud infill house (item 9, judgment; D086's open question; approved as recommended 2026-11-23)

| Payload | Reference house, straw bale (gated) | Reference house, stud infill (reported) | Largest case, straw bale (gated) | Largest case, stud infill (reported) |
|---|---|---|---|---|
| `plan2d` | 132,737 (51%) | 150,197 (57%) | 767,318 (38%) | 803,659 (40%) |
| `mesh3d` | 174,958 (67%) | **219,188 (84%)** | 949,138 in CI, 951,115 here (48%) | 1,045,269 in CI, 1,047,246 here (52%) |
| `timber_schedule` | 173,680 (66%) | 173,680 (66%) | 1,135,024 in CI, 1,135,194 here (57%) | the same |
| `assembly_schedule` | 63,191 (24%) | 135,983 (52%) | 53,558 (3%) | 203,959 (10%) |
| `preliminary_estimate` | 5,826 (2%) | 6,971 (3%) | 5,826 | 6,955 |

Ceilings: 262,144 bytes for the reference house, 2,000,000 for the largest case. The reference house's numbers are identical in CI and here.

**Recommendation: gate the stud infill house at the same ceilings as the straw bale house,** in both cases. One command (`SetWallAssembly`, D068) reaches it from every project, and a ceiling that checks only one of the two approved assemblies leaves half of D008's comparison unbounded.

**Reported under D063's rule:** the stud infill reference house's `mesh3d` is at **84%** of its ceiling, past half. Gating it now leaves 42,956 bytes of room. ART-003 §9.4 measured that keys and `primitive` on every framing entry would have put it at about 97%, so the next additions to the mesh's framing entries are likely to need a decision on this ceiling. That is the point of a ceiling: the growth is then a reviewed choice.

*Alternatives:*
- **Keep it reported, not gated** (today). Nothing fails if the stud infill mesh passes 256 KiB.
- **A separate, higher ceiling for the stud infill house** (for example 384 KiB). Room to grow, but a new number with no basis but today's size.

### 8.2 A largest case for walls (item 10, judgment; approved as recommended 2026-11-23)

D063's largest case is the largest frame: 7 × 7 stations over 80' × 80', 12" joists, 4 purlins, both brace planes. On it, walls take the fixture's definitions and **only 10 openings** survive (ART-003 §17), so it does not bound walls at all. For the frame, "largest" was a real maximum: every parameter has a bound. **For walls it is not.** D077 bounds the definitions (stud spacing 12"–48", girts 0–4), but openings have no bounds beyond positive width and height and the fit ("Openings have no size bounds beyond width and height greater than 0 and the fit rules").

**Measured** on the largest frame, stud infill unless stated:

| Case | Openings | Pieces | `plan2d` | `mesh3d` | `assembly_schedule` |
|---|---|---|---|---|---|
| D063's case, fixture definitions (gated straw bale; stud infill reported) | 10 | 402 | 803,659 | 1,047,246 | 203,959 |
| A centered 3'-0" × 4'-0" window in every wall, fixture definitions | 48 | 668 | 838,503 | 1,123,622 | 351,984 |
| The same, with D077's densest framing: 12" studs, 4 girts (which need 1'-6" brace legs to fit) | 48 | **1,239** | 899,300 | **1,268,294 (63%)** | 595,252 |
| *As built in implementation (§17): a centered window in every wall, none of the fixture's openings kept* | 48 | **1,224** | 898,144 | **1,265,481 (63%)** | 588,964 |
| Two 2'-0" × 4'-0" windows per wall, densest framing | 96 | 1,536 | 940,868 | 1,353,405 (68%) | 756,257 |
| 26 windows 1" × 1'-0" per wall, straw bale (valid; every framed opening fits) | 1,248 | 4,992 | 1,533,764 | **2,441,533 (122%)** | **2,834,791 (142%)** |

The last row is a valid snapshot whose `mesh3d` and `assembly_schedule` exceed D063's 2 MB ceiling. So the phrase "each payload of the largest supported case at most 2 MB" cannot hold for VS-02b as specified: there is no largest supported case.

**Recommendation:**
- **Name a representative largest case for walls,** the third row: D063's largest frame, stud infill with D077's densest framing (12", 4 girts, brace legs 1'-6"), and one centered D072-sized window (3'-0" × 4'-0", sill 3'-0") in every wall. Gate its payloads at 2 MB, both families, with D063's case kept as it is. Its largest payload is 63%, past half, and is reported as such.
- **Move the largest-case time checks to it** (§8.3), because it is the heaviest named case.
- **Say plainly that this is a named case, not a bound:** the 2 MB ceiling then guards against regressions in the wall payloads, not against what a user can build. The roadmap's "Current limitations" says so.
- **Raise opening bounds as a product question,** outside this task: a minimum rough-opening size and/or a maximum number of openings per wall, which would give walls a real largest case. It is a validation change (MODEL-006's territory) and a new requirement, so it is a decision for the product owner and a task of its own, not something a test task introduces.

*Alternatives:*
- **Keep D063's case only,** and report the wall cases. Simple, but the gated largest case then has 10 openings and fixture framing, and the ceiling checks almost none of the wall payloads' growth.
- **The two-per-wall row** as the named case: larger (68%), but two windows per wall is no more principled than one; one matches D072's pattern.
- **Bound openings first, then set the case:** the most correct, but it blocks VS-02b's completion on a product change.

### 8.3 Time budgets (item 11, judgment; approved as recommended 2026-11-23)

**Backend** (local; CI is from PR #20, where backend times ran about 1.5× local):

| What | Local | CI (PR #20) | Ceiling (D063) |
|---|---|---|---|
| Preview, reference house, width edit, straw bale | 136 ms | 202 ms | 1 s |
| The same, stud infill | 204 ms | — | — |
| Preview, reference house, `SetOpening` width +1" | 132 ms | — | — |
| Preview, reference house, `SetWallAssembly` to stud infill | 171 ms | — | — |
| Preview, D063's largest case, width edit | 877 ms | 1,305 ms | 5 s |
| Commit with five artifacts, D063's largest case | 1,108 ms | 1,569 ms | 5 s |
| Preview, §8.2's named wall case, width edit | 1,328 ms | — (about 2.0 s at 1.5×) | — |
| Preview, the named wall case, `SetWallAssembly` to straw bale | 1,103 ms | — (about 1.7 s) | — |
| Commit with five artifacts, the named wall case | 1,612 ms | — (about 2.4 s) | — |

**Browser** (the e2e dev-server setup; median of 5):

| What | Local (UI-004 §20) | CI (PR #20) | Today |
|---|---|---|---|
| Create until both views, the timber schedule, and the assembly schedule | 1,828 ms | 1,327 ms | reported |
| Preview pressed until the `SetWallAssembly` dialog | 556 ms | 519 ms | reported |
| The stud infill house reloaded until both views | 2,012 ms (one run 4,253 ms) | 1,607 ms | reported |
| D063: Create until views and schedule; Preview until dialog | — | 1,303 ms; 503 ms | gated, 10 s and 3 s |

**Recommendation** (D063's form: median of 5, gated in CI, no retries, stop and report above half):
- **Backend:** the largest-case preview and commit checks run on §8.2's named wall case (if item 10 is approved), with D063's 5 s ceilings, plus a **`SetWallAssembly` preview on it, 5 s**, and a **reference-house `SetOpening` preview, 1 s** (the routine path a homeowner uses most). D063's reference-house width preview stays.
- **Browser:** UI-004's three timings become **gated** at D063's existing ceilings: 10 s for the two render timings (Create until both schedules; the stud infill reload), 3 s for the `SetWallAssembly` dialog. They stay in their own test in `walls.spec.ts`. D063's case in `connections.spec.ts` is unchanged.
- **Expected against half:** every value is under half its ceiling except, possibly, the named wall case's commit, estimated at about 48% in CI. If CI measures more than half, the implementation stops and reports (D063); it does not raise the ceiling.

*Alternatives:*
- **Backend checks on D063's case only,** with the wall case's times reported. No risk of the half rule, and no check on the heaviest wall regeneration.
- **Browser timings reported only** (UI-004's choice): never flakes, catches nothing. The one slow local run (4,253 ms) is still far under 10 s.

## 9. How the browser tests trace AC2b-10 (item 6, routine)

By the **`it` and `test` titles** of the cases that prove each bullet, in the reference form `frontend/<path> › <exact title>`, as TEST-002 item 3 set:

- **AC2b-10.1** (walls, wall framing, and openings in 2D, 3D, and the schedule, with the two switches): `ui004.test.tsx` groups 1–5 (all 20 cases), the schedule cases of group 8 (`shows the assembly schedule: …`, `formats volumes and the stud infill takeoff (76 studs)`), and in Playwright `walls.spec.ts › views and switches: 10 walls on Level 0, 20 walls and 79 pieces in 3D; the switches hide them and are remembered`.
- **AC2b-10.2** (the wall assembly and openings through preview and apply): `ui004.test.tsx` groups 6–7 and the dialog cases of group 8 (`shows SetWallAssembly's wall counts, artifacts, and labeled definitions`, `lists the 8 windows a re-identified grid line removes, above Confirm (D088)`, `shows the width preview's 16 updated walls`); in Playwright the five other "9. UI-004 end to end" cases (switch the assembly; change an opening; add and remove; the fit rejection from a frame edit; removed openings).
- **AC2b-10.3** (square-meter rows, moved to ART-003 by D085): `art003.test.tsx › converts per-square-foot prices exactly, rounded half-even`, `› shows stored m2 prices per square foot or meter`, `› builds rows from the estimate's lines with their units, and submits m2`, and `walls.spec.ts › assembly line: a per-square-foot price is stored per square meter, prices the line, and reloads`.

**Two titles to avoid:**
- the group's `test.describe("9. UI-004 end to end")`, which the checker does not accept (§4). The checker stays as it is: a `describe` title passes when its cases are deleted, which TEST-002 §9 already rejected as a reference form;
- `ui004.test.tsx › centers a 3' opening in a 12' wall at 4' 6\", and sends the computed value`, whose title contains an escaped quote; the matrix would have to carry the backslash. Group 6's other cases cover the same bullet.

UI-004 §16 test 10 (earlier slices) traces AC2b-08 through the VS-01 and VS-02 matrices, and test 11 traces AC2b-06.3 and AC2b-09.

## 10. UI-004's twelve flagged choices (item 12, judgment; settled 2026-11-23: all twelve confirmed as implemented)

UI-004 §20 kept twelve implementation choices "within the approved text, flagged for the product owner". None changes a matrix row: each is tested as implemented, and AC2b-10 does not name any of them. They are listed so that VS-02b is not declared complete with open flags, as TEST-002 item 9 did for UI-003's four. **The recommendation for each is to confirm it as implemented.** They can be confirmed together, or any of them taken one at a time:

1. The Walls tab sums the layer thicknesses for its total; the schedule panel shows the served total.
2. The editor and the dialog name a wall's side from its key and the grid's line order (tested to agree with the schedule's labels for all 20 walls).
3. Picking a wall switches the Walls tab's form to a new opening in that wall, dropping typed values in an existing opening's form; the tab does not open.
4. D088's block says "with their walls" only when every removed opening's wall goes too; an undo that removes an added opening reads "This opening will be removed. Undo restores it."; one opening reads in the singular.
5. Thermal rounding: U-values and conductivities to 3 decimals, R-values to 2, UA to 1, permeances to 3 significant digits.
6. The thermal table: one row per figure; the walls table's totals row shows "—" for the framing fraction.
7. Missing inputs: one deduplicated list, "Missing declared values:".
8. Opening marks drawn after the members, unfilled, so they can be seen and clicked; a click exactly on a buck head or header line picks the framing.
9. The Connections switch still does not clear a connection selection; only the two wall switches clear what they hide.
10. 3D opening pick surfaces lie on the wall's exterior face.
11. Opening list rows show the full opening label.
12. The stud infill fixture envelopes come from a second, identical in-memory project.

Any choice not confirmed becomes a small UI change of its own, outside this task, with its own approval. This task records the outcome in UI-004 §20.

## 11. Changes to existing tests and documents

**Tests** (test-only changes need no approval):
- `test_traceability.py`: the generalized source reader, `test_every_vs02b_item_is_traced`, its rejection test, and the VS-02 section ends of §5.3.
- `integration/scenario.py` and the golden record (§6); `integration/test_sequences.py` and `invariants.py` (§7).
- `test_budgets.py` and `walls.spec.ts` (§8), in the form items 9–11 settle. `conftest.py` gains the named wall case's builder beside `largest_doc` (§15).

**Documents:**
- `docs/implementation/acceptance-tests/vs-02b-traceability.md` (new, §5).
- `vs-02-traceability.md`: the AC2-01 row (§5.5).
- artifacts.md §10 and dependencies.md §8: the VS-02b checks as bullets, with DEP2b-3 corrected (§5.3), and their notes pointing to the matrix.
- vs-02b.md: its status block names the matrix, and §16's `TEST-003` row is updated.
- `tests/README.md` and `backend/README.md`: the golden steps, the gate, and the budgets.
- UI-004 §20: item 12's outcome.
- **Decision record:** the judgment items 9–11, once approved, are recorded as **D090** (VS-02b budgets and the named wall case), with the register updated. Item 12 is recorded in UI-004 §20, as TEST-002 item 9 was in UI-003 §17.
- **The roadmap:** TEST-003's row, VS-02b complete, the next steps, the "Current limitations" lines (the stud infill gate, the named wall case and unbounded openings), and "Open items" (opening bounds, if item 10 is approved).

## 12. Errors, security, and migration

- **Errors:** none new. A budget failure is a test failure with its measurement in the message.
- **Security:** no routes, permissions, or secrets. The budget tests use the in-memory store and test tokens.
- **Migration:** none. The golden record is regenerated as a reviewed diff (D055).

## 13. Proposals for approval

**Routine** (they follow from vs-02b.md §6 item 15, D063, TEST-002, D055, and D056). **All eight approved together (2026-11-23).**

1. **Matrix and check** (§5.1–5.2): `vs-02b-traceability.md` with 22 AC rows and 11 contract rows, checked against vs-02b.md's IDs and wording with a count guard of 33, by a generalized form of the VS-02 check.
2. **Contract checks as bullets** (§5.3): artifacts.md §10's and dependencies.md §8's VS-02b prose as 5 and 6 bullets, sentences kept, **with DEP2b-3 corrected to the measured rule** (the estimate is also impacted when a summed length changes in its last bit); the VS-02 parser stops at the VS-02b headings.
3. **AC2-01's row** (§5.5): `N/A — replaced by AC2b-01`, as AC2b-08 says.
4. **Golden scenario** (§6): steps 7f–7m after 7e, with four commits (add, move, switch to stud infill, remove), four rejections (one a fit rejection through `SetWallAssembly`), the removed openings of `grid-x-4` asserted, and the undo reusing all five of revision 2's payloads; revisions 1–11 unchanged; regenerated and reviewed as an additive diff.
5. **Sequences** (§7): the four wall commands drawn, wall, framing, and opening identity checked between steps, openings never moving silently, and the gate extended; still 40 sequences.
6. **AC2b-10 by `it` and `test` titles** (§9), per bullet; the `test.describe` title and the escaped-quote title are not used.
7. **How sizes are measured and reported** (§8): the CI number is the gated one; the implementation notes record both local and CI sizes, since the largest case's bytes differ between machines (§4).
8. **Documents and status** (§11), with VS-02b declared complete in the roadmap once §14 passes.

**Your judgment** (one at a time, in this order):

9. **Gate the stud infill house** (§8.1) at the same ceilings as straw bale: 256 KiB for the reference house, 2 MB for the largest case. Its mesh is at 84%, reported here under D063's rule. *Alternatives:* reported only, as today; a separate, higher ceiling. **Approved as recommended (2026-11-23).**
10. **A named largest case for walls** (§8.2): D063's frame, stud infill with D077's densest framing (12", 4 girts, 1'-6" brace legs), and a centered 3'-0" × 4'-0" window in every wall (1,239 pieces; largest payload 63%), gated at 2 MB in both families beside D063's case; stated as a named case, not a bound, because openings are unbounded (a valid snapshot reaches 2.4–2.8 MB); **opening bounds raised as a separate product question.** *Alternatives:* D063's case only; two windows per wall; bound openings first. **Approved as recommended (2026-11-23).**
11. **Time budgets** (§8.3): the largest-case preview and commit on the named wall case (5 s), a `SetWallAssembly` preview there (5 s), a reference-house `SetOpening` preview (1 s); UI-004's three browser timings gated at D063's 10 s and 3 s. *Alternatives:* backend checks on D063's case only; browser timings reported only. **Approved as recommended (2026-11-23).**
12. **UI-004's twelve flagged choices** (§10), each confirmed as implemented, or changed in a UI change of its own. **Settled (2026-11-23): all twelve confirmed as implemented.** Recorded in UI-004 §20. No UI change follows.

Items 9–11 are approved and recorded as **[D090](../../product/decisions/D090-vs02b-budgets-and-named-wall-case.md)**.

## 14. Acceptance criteria and automated tests

1. **Matrix (AC2b-11):** `vs-02b-traceability.md` has a row for every item of its three sources, and `test_every_vs02b_item_is_traced` passes. Removing, renaming, or skipping a referenced test, or rewording a criterion in vs-02b.md, makes it fail. The VS-01 and VS-02 checks still pass, the VS-02 count still 24.
2. **Golden scenario:** the record has §6's steps and 16 revisions; revisions 1–11 are byte-identical to today's; each new step's outcome, detail, and impact list is as §6.1 states; every rejection leaves the project unchanged; `grid-x-4` lists its 4 removed openings; undo reuses all five of revision 2's payloads and restores its openings; `golden.py --check` passes on both stores.
3. **Sequences:** under the `ci` profile, the gate passes with every §7.4 outcome reached; the new transition rules hold at every step; `thorough` still runs on demand. The run time is reported.
4. **Budgets:** the checks approved in items 9–11 pass locally and in CI and print their measurements; values above half a ceiling are reported.
5. **Browser traceability:** every AC2b-10 row lists §9's titles, each found once and not skipped.
6. **Everything else unchanged:** no product code changes; the UI fixture, vectors, schemas, and OpenAPI drift checks pass unchanged; `scripts/check.sh` passes locally, and the pull request's CI passes all four jobs.

## 15. Implementation guidance (not prescriptive)

- **Order:**
  1. the bullets of §5.3 and the VS-02 section ends, with the VS-02 check passing;
  2. the VS-02b matrix and its test, from §5.4;
  3. the golden steps, then the regenerated record;
  4. the new invariants, then the draws and the gate, then a statistics run;
  5. the budgets, measured in CI on the pull request before the ceilings are final.
- **Generalizing the source reader:** `vs02_source_items` hard-codes vs-02.md's section bounds and the `AC2-` prefix; take them as arguments. vs-02b.md §15's criterion lines are `- **AC2b-NN: …`, with bullets indented by two spaces, as in vs-02.md.
- **The named wall case:** build it in `conftest.py` from `largest_doc()`: set the brace leg to 0.4572 m with `with_frame_parameters`, add one opening per wall (`offset_m = (L − w) / 2`, IDs from UUIDv5 of the wall's key, listed in `opening_ids` in ID order), set the stud infill definition's `stud_spacing_m` to 0.3048 and `girt_count` to 4, then `with_assembly`. The drafting measurement did exactly this and the result validated.
- **Passing the command to `check_transition`:** the sequences and the scenario both have it at hand; a keyword argument keeps the existing callers working.
- **Measuring time:** as `test_budgets.py` does; for the browser, reuse `walls.spec.ts`'s timing test and add the ceilings to it.

## 16. Definition of done

- All §14 criteria are met, with the full backend suite, Vitest, Playwright, `tsc`, and the drift checks. `scripts/check.sh` and CI pass; the run is linked in the implementation notes.
- The judgment items are recorded in D090, and item 12's outcome in UI-004 §20. The §11 documents are updated.
- VS-02b is complete by its own acceptance criteria. The roadmap says so, and lists what remains open (opening bounds, if item 10 raises them; hosting and identity, open question 8).
- Changed files, tests, measurements, limitations, and next steps are summarized (AGENTS.md).

## 17. Implementation notes (2026-11-23)

**Delivered** (test-only, plus documents; no product code changes):
- **Matrix (items 1–3):**
  - `docs/implementation/acceptance-tests/vs-02b-traceability.md` (new): 33 rows, 22 for the §15 criterion bullets and 11 for the contract checks. It starts from §5.4's candidates, with the new tests added. Its criterion cells were generated from the sources, so their text matches exactly.
  - artifacts.md §10 and dependencies.md §8: the VS-02b checks are bullet lists now, with every original sentence kept (checked while editing) and DEP2b-3 corrected (§5.3). Their notes point to the matrix.
  - `vs-02-traceability.md`: AC2-01's row is `N/A — replaced by AC2b-01` (§5.5).
- **`test_traceability.py`:** `criteria_items` and `bullet_items` read any slice's criteria and contract bullets; `slice_matrix_rows` and `slice_problems` replace the VS-02-only versions. The VS-02 lists now end at "VS-02b reconciliation" and "VS-02b examples", and the VS-02 count guard is still 24. New: `test_every_vs02b_item_is_traced` (count guard 33) and `test_vs02b_check_rejects_reworded_missing_and_untested_rows`, which also checks that neither slice reads the other's bullets.
- **Golden scenario (item 4):** `scenario.py` gains `wall_steps` (7f–7m, as §6.1 measured them, each detail code, path, and argument asserted), the removed-openings assertion at `grid-x-4`, and the restored openings after the undo. `accepted` passes each step's command to `check_transition`. **Regenerated record:** 26 steps and 16 revisions. Revisions 1–11 and the first 15 steps are byte-identical; the undo moves from sequence 12 to 16, with artifact fingerprints equal to revision 2's. Its `snapshot_fingerprint` changes because its parent is now revision 15, as in TEST-002.
- **Invariants (item 5):** `check_transition` checks wall and wall framing IDs for surviving keys, and, given the command, that openings never move, appear, or disappear silently (`check_openings_transition`). `test_check_transition_catches_silent_wall_and_opening_changes` checks each rule on mutated fixtures.
- **Sequences (item 5):** the four wall commands are drawn (§7.2), the gate is extended (§7.4), and fit rejections are recorded as `rejected (fit)`. See the findings for the draw changes that reaching every outcome needed.
- **Budgets (items 9–11, D090):**
  - `conftest.largest_wall_case(label)` builds the named case;
  - `test_payload_sizes_are_within_budget` has six gated cases: the reference house and D063's largest frame, each in both families, and the named wall case in both;
  - the time checks: `test_reference_house_preview_time` (unchanged), `test_reference_house_set_opening_preview_time`, `test_largest_wall_case_set_wall_assembly_preview_time`, and `test_largest_case_preview_time` and `test_largest_case_commit_time`, gated on D063's largest frame and reported on the named wall case. As first implemented they were gated on the named wall case; item 13 changed that;
  - `walls.spec.ts`: UI-004's timing test is now `budgets: …`, gated at 10 s, 3 s, and 10 s. `connections.spec.ts` is unchanged.
- **Documents:** vs-02b.md (status block, §16 row), `tests/README.md`, `backend/README.md`, D090 (implemented; numbers corrected, below) and the register, UI-004 §20 (item 12), and the roadmap.

**Corrected while implementing:** the named wall case as D090 defines it has **1,224 pieces** with stud infill, and its largest payload, `mesh3d`, is 1,265,481 bytes (63%). §8.2's drafting measurement (1,239 pieces, 1,268,294 bytes) kept the fixture's 10 surviving openings, among them a door and two 5'-0" windows. D090 and §8.2 now carry both, with the reason. Nothing approved changed.

**Measured** (local, on the development machine; CI values are below):

*Sizes* (canonical bytes; `test_payload_sizes_are_within_budget`):

| Case | `plan2d` | `mesh3d` | `timber_schedule` | `assembly_schedule` | Largest share |
|---|---|---|---|---|---|
| Reference house, straw bale | 132,737 | 174,958 | 173,680 | 63,191 | 67% of 256 KiB |
| Reference house, stud infill | 150,197 | **219,188** | 173,680 | 135,983 | **84%** of 256 KiB |
| Largest frame, straw bale | 767,318 | 951,115 | 1,135,194 | 53,558 | 57% of 2 MB |
| Largest frame, stud infill | 803,659 | 1,047,246 | 1,135,194 | 203,959 | 57% |
| Named wall case, stud infill | 898,144 | **1,265,481** | 1,135,239 | 588,964 | **63%** |
| Named wall case, straw bale | 790,268 | 999,837 | 1,135,239 | 142,563 | 57% |

Every estimate is under 7,000 bytes. Above half a ceiling, as D063 asks to report: the stud infill reference house's `mesh3d` (84%), the straw bale reference house's `mesh3d` and `timber_schedule` (67%, 66%), the named wall case's `mesh3d` (63%), and every case's `timber_schedule` on the largest frame (57%). None is over its ceiling.

*The `ci` sequences* (`--hypothesis-show-statistics`, local): 40 passing and 19 invalid cases, **7 min 20 s** (5 min 4 s before this task). Every gated outcome is reached, and the statistics are identical whether the file runs alone or inside the full suite (see the findings). The wall commands' shares of the generated cases: `AddOpening` accepted 17.0% (rejected 5.1%), `SetOpening` accepted 39.0% (impacts 2, 3, 4: 11.9%, 17.0%, 17.0%; rejected 8.5%), `RemoveOpening` accepted 10.2% (rejected 20.3%), `SetWallAssembly` accepted 17.0% (rejected 5.1%), and `SetFrameParameters` impacts 5 in 15.3%. **`SetOpening` can impact a single artifact:** a sill move on straw bale changes the mesh, and leaves the assembly schedule bit-identical when no piece length changes in its last bit. That is exact (D056), and the gate does not require it.

**Findings:**
- **Reaching every outcome needed more than §7.2's draws.** With them alone, each of five attempts missed two to ten outcomes: 40 sequences of a few steps each cannot reach about 50 outcomes by chance, and Hypothesis builds examples by mutating earlier ones, so a choice made once per sequence (a theme, an offset) repeats across the 40 and clustered (for example 50%, 29%, 15%, and 6% over four themes). What the gate passes with:
  - **targets from the house's state:** a targeted step takes its target from a hash of the current house's entities, with floats rounded to 1e-6, plus a drawn integer (`target_for`), over all 28 targets: §7.2's, the VS-02 ones, and "brace leg on stud infill" (on stud infill it shortens the braces; otherwise it switches to stud infill, which queues the brace edit). Houses diverge after a sequence's first steps, so the targets spread. The rounding keeps last-bit platform differences (§4) from changing a target;
  - **a follow-up queue per sequence** (`FOLLOW_UPS`), for outcomes that need a particular house: after an accepted `RemoveOpening`, a window in the now-empty wall, an opening as wide as its wall, the removed ID again, an overlap, a sill move, and a shorter opening; after an accepted roof edit, an undo; after a switch to stud infill, shorter braces; after an accepted `SetConnectionType` or `SetMemberSection`, a joist spacing that keeps the count. Queued steps run first, in order. The queue replaces rules keyed on the last command for these cases, because a rejected step does not change `last`, so such a rule could fire forever. TEST-002's `AddSection` rule is unchanged;
  - **draws that keep the house valid where an acceptance is wanted:** "footprint accepted" only widens (by up to 3%) and "stories accepted" only raises the heights, because a narrower bay or a lower story can fail the opening fit since v3. A new window goes into an empty wall, or, on the created house where every wall has one, a 1' × 1' window low near the start post. Small changes are drawn with a nonzero size and a sign (`_nudge`), because Hypothesis shrinks floats toward 0, which made "offset only" a no-op;
  - two steps in three are targeted (one in two before), and sequences have 4 to 8 steps (1 to 8 before). Still 40 sequences.
- **The derandomized run drew differently alone and inside the full suite.** Hypothesis also draws numeric literals it finds in every loaded local module (its "local constants"; for example 1.1176 m, 3'-8", from another test module), and the full suite loads 21 test modules, so the same seed produced different floats from the twelfth draw on, and `check.sh` missed an outcome that the file alone reached. `no_local_constants` (in the gate's fixture) gives the sequences an empty constant pool, by patching `hypothesis.internal.conjecture.providers._get_local_constants` and swapping its cache, both restored after the module. With it, a full-suite run and a standalone run produce identical statistics (checked). It uses a private Hypothesis API, pinned by `uv.lock`; an upgrade that removes it fails loudly at the patch.
- **`--hypothesis-seed` is ignored under the `ci` profile,** because it is derandomized: two seeds drew identical values in a small check. So a seed check needs random generation. Run that way (`derandomize=False`, 40 examples, seeds 1–3, through the test's inner function with `no_local_constants`, then the gate's `missing_outcomes`): seed 3 reaches every outcome; seed 1 misses `SetFrameParameters: impacts 5`, and seed 2 `AddSection: rejected` and `RemoveOpening: rejected`. No seed broke an invariant. The gate is deterministic in CI, so this does not make it flaky; it says that a large change to the draw may need a targeted edit to keep the gate passing, as TEST-002 found. TEST-002 §17's seed check used `--hypothesis-seed` with the `ci` profile, so it probably repeated the derandomized run; that is not verified here.
- **The largest frame's sizes differ between machines** (§4). CI's numbers are the gated ones, and the notes record both.

**Limitations:**
- The named wall case is a named case, not a bound (D090): openings are unbounded, so a valid house can exceed 2 MB (§8.2).
- The time ceilings describe the in-process service and the e2e dev-server setup, not a production build (D063).
- The outcome gate checks reach only under the derandomized `ci` profile, which is fixed by the test's source: an edit to `test_sequences.py` reshuffles the 40 sequences, and the gate then names anything lost.

**CI values** (PR #22, run [45236217611](https://github.com/pursuingpareto/home-design/actions/runs/45236217611); all four jobs passed; backend 1,004 passed in 25 min 51 s, e2e 31 passed):

*Sizes:* the reference house's are byte-identical to the local ones. The largest frame and the named wall case differ slightly, as §4 expects. The CI values are `mesh3d` 949,138 and 1,045,269 for the largest frame (straw bale, stud infill), 1,263,504 and 997,860 for the named wall case (stud infill, straw bale), and `timber_schedule` 1,135,024 for the largest frame and 1,135,069 for the named case. The other payloads are identical. The shares above half are the same as locally: 84%, 67%, 66%, 63%, and 57%. D090 approved these with the measurements.

*Times* (median of 5; the CI runner was slower than PR #20's: the reference house preview took 293 ms here against 202 ms there):

| What | Local (`check.sh`) | CI (PR #22) | Ceiling | CI share |
|---|---|---|---|---|
| Preview, reference house, width edit | 169 ms | 293 ms | 1 s | 29% |
| Preview, reference house, `SetOpening` | 167 ms | 282 ms | 1 s | 28% |
| Preview, named wall case, width edit | 1,409 ms | **2,632 ms** | 5 s | **53%** |
| Preview, named wall case, `SetWallAssembly` to straw bale | 1,148 ms | 2,121 ms | 5 s | 42% |
| Commit with five artifacts, named wall case | 1,631 ms | **3,077 ms** | 5 s | **62%** |
| Browser: Create until both views and both schedules | 1,631 ms | 1,777 ms | 10 s | 18% |
| Browser: Preview pressed until the `SetWallAssembly` dialog | 425 ms | 589 ms | 3 s | 20% |
| Browser: the stud infill house reloaded until both views | 2,005 ms | 2,225 ms | 10 s | 22% |
| Browser (TEST-002): Create until 2D, 3D, and the schedule | 1,633 ms | 1,545 ms | 10 s | 15% |
| Browser (TEST-002): Preview pressed until the dialog | 311 ms | 615 ms | 3 s | 21% |

**Stopped under D063's rule (2026-11-23).** Two CI times are over half their ceilings: the named wall case's commit at 62% and its width preview at 53%. D090 estimated the commit at about 48%, assuming CI runs at 1.5× local. This run was 1.9× local (1.73× for the reference house). As D063 and D090 require, `main` was not fast-forwarded, and no ceiling was changed. Both checks pass. The concern is headroom. D063 set its time ceilings at 5–10× the measured times, because shared runners "vary by several times" and the gates have no retries. At 62%, a runner 1.6× slower than this one fails the commit check, and that blocks `main`. Item 13 puts the response to the product owner.

13. **The named wall case's CI times over half** (*Your judgment*). Options:
    - **(a) Gate D063's largest frame again; report the named wall case** *(recommended)*. The preview and commit gates go back to D063's largest frame, as before this task: 1,305 ms and 1,569 ms in PR #20's CI, about 2.1 s for the commit on this run's runner. The named case's three timings are printed, not gated. This adds no new number and keeps D063's headroom. Its cost: a slowdown specific to walls is caught only when it also slows the largest frame, or by reading the printed lines. The `SetWallAssembly` preview on the named case can stay gated (42%).
    - **(b) Keep D090 as approved.** The named case stays gated at 5 s, and the flake risk is accepted. D090 records the CI shares.
    - **(c) Speed up the commit first.** A product task (profiling the commit's derivation on the named case), with `main` waiting on it.
    - **(d) Raise the named case's ceilings** (for example to 10 s). This adds a new number, which D063 says not to do as the automatic response.

    **Settled (2026-11-23): option (a).** Recorded as an amendment to D090. `test_largest_case_preview_time` and `test_largest_case_commit_time` are parametrized over D063's largest frame, which is gated at 5 s, and the named wall case, which is printed as `reported, not gated`. `test_largest_wall_case_set_wall_assembly_preview_time` stays gated. The matrix's AC2b-11 row now cites the gated commit check. Measured locally afterwards (`scripts/check.sh`, 1,006 backend tests): the largest frame's width preview 971 ms (19%) and commit 1,151 ms (23%), both gated; the named wall case's width preview 1,369 ms and commit 1,588 ms, both reported; its `SetWallAssembly` preview 1,121 ms (22%), gated. PR #22's final CI run holds the CI values.
