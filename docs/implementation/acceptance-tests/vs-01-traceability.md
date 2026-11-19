# VS-01 traceability matrix

Every VS-01 acceptance criterion and architecture contract test, with the automated tests that cover it ([TEST-001](../tasks/TEST-001.md) §4). `backend/tests/test_traceability.py` enforces this file:

- every item in the five source lists has exactly one row;
- every row lists at least one test, or starts with `N/A —` and gives a reason;
- every referenced test exists.

**Reference forms:**
- pytest: `backend/tests/<file>.py::<function>`;
- Vitest and Playwright: `frontend/<path> › <exact test title>`;
- npm scripts: `frontend/package.json#<script>`.

A test being fixed may be marked `[quarantined: <issue>]` (TEST-001 §8). A row whose every reference is quarantined fails the check.

**Sources:**
- AC: [vs-01.md](vs-01.md);
- BM: [building-model.md §9](../../architecture/building-model.md#9-vs-01-model-acceptance-tests);
- DEP: [dependencies.md §8](../../architecture/dependencies.md#8-vs-01-examples-and-tests), table rows in order;
- ART: [artifacts.md §10](../../architecture/artifacts.md#10-acceptance-tests-additions-to-vs-01);
- IF: [interfaces.md §9](../../architecture/interfaces.md#9-contract-test-matrix).

Integration tests (`backend/tests/integration/`) check the whole house after every step, so they appear in many rows.

## VS-01 acceptance criteria

| ID | Criterion | Tests |
|---|---|---|
| AC-01 | Same dimensions in 2D and 3D for the reference house | `frontend/e2e/vs01.spec.ts › AC-01: Reference House 001 shows the same dimensions in 2D and 3D`<br>`backend/tests/test_api.py::test_vs01_flow`<br>`frontend/tests/components.test.tsx › labels dimensions from value_m and shows every member of each plane`<br>`backend/tests/integration/test_reference_house.py::test_reference_house_scenario_matches_golden` |
| AC-02 | A validated width change updates members and both views without stale geometry | `frontend/e2e/vs01.spec.ts › AC-02, AC-07: a width change updates both views and the schedule, never pairing old geometry`<br>`backend/tests/test_geometry.py::test_service_derives_geometry_and_tracks_width_changes`<br>`backend/tests/integration/test_reference_house.py::test_reference_house_scenario_matches_golden` |
| AC-03 | Stable member IDs; deterministic lengths and quantities | `backend/tests/test_commands.py::test_width_change_preserves_member_ids`<br>`backend/tests/test_timber.py::test_generation_is_deterministic_and_order_independent`<br>`backend/tests/integration/test_sequences.py::test_random_command_sequences_keep_every_invariant` |
| AC-04 | The schedule reconciles with the inventory and reports units and assumptions | `backend/tests/test_estimating.py::test_reference_house_schedule`<br>`backend/tests/test_estimating.py::test_schedule_matches_independent_ecmascript_implementation`<br>`backend/tests/integration/test_reference_house.py::test_reference_house_scenario_matches_golden` |
| AC-05 | Saving and reopening restores the revision and parameter values | `backend/tests/test_project.py::test_round_trip_preserves_canonical_bytes`<br>`frontend/e2e/vs01.spec.ts › AC-05: reloading and reopening restores the revision and dimensions`<br>`backend/tests/test_api.py::test_vs01_flow` |
| AC-06 | Invalid or contradictory input is rejected atomically with actionable errors | `backend/tests/test_commands.py::test_rejections`<br>`backend/tests/test_api.py::test_8_unsupported_geometry_is_a_structured_422`<br>`frontend/e2e/vs01.spec.ts › AC-06: an unsupported width is rejected with a field error and no new revision`<br>`frontend/e2e/editors.spec.ts › AC-06: a width the grid cannot support points to the Grid tab, and works after adding a bay`<br>`backend/tests/integration/test_sequences.py::test_random_command_sequences_keep_every_invariant` |
| AC-07 | Derived outputs name their revision; stale outputs are never shown as current | `backend/tests/test_artifacts.py::test_old_head_artifacts_never_current_for_new_head`<br>`frontend/tests/pairing.test.ts › refuses mismatched revisions even when both are CURRENT`<br>`frontend/e2e/vs01.spec.ts › AC-02, AC-07: a width change updates both views and the schedule, never pairing old geometry`<br>`backend/tests/test_api.py::test_7_plan_mesh_schedule_share_source_revision` |
| AC-08 | The UI labels framing and estimates as preliminary | `frontend/tests/components.test.tsx › shows the envelope's preliminary message`<br>`frontend/e2e/vs01.spec.ts › AC-08 and undo: history is labeled, preliminary, and undo goes through the preview`<br>`backend/tests/test_artifacts.py::test_envelope_contract_and_fingerprint` |
| AC-09 | Automated tests cover the operations and invariants, including deterministic replay and round trips | `backend/tests/test_project.py::test_replaying_the_operation_log_reproduces_history`<br>`backend/tests/integration/test_reference_house.py::test_reference_house_scenario_matches_golden`<br>`backend/tests/integration/test_sequences.py::test_random_command_sequences_keep_every_invariant`<br>`backend/tests/test_fixture.py::test_round_trip_is_lossless`<br>`backend/tests/test_traceability.py::test_every_vs01_item_is_traced` |

## Building model (building-model.md §9)

| ID | Contract test | Tests |
|---|---|---|
| BM-1 | The reference snapshot validates and round-trips with identical canonical bytes | `backend/tests/test_fixture.py::test_fixture_is_valid`<br>`backend/tests/test_fixture.py::test_round_trip_is_lossless` |
| BM-2 | Invalid and unsupported footprint, grid, and roof values are rejected | `backend/tests/test_mutations.py::test_mutation`<br>`backend/tests/test_commands.py::test_rejections` |
| BM-3 | A missing material, section, or building reference is rejected with a path | `backend/tests/test_mutations.py::test_mutation`<br>`backend/tests/test_mutations.py::test_every_catalog_code_is_exercised` |
| BM-4 | A width change keeps member IDs for unchanged generation keys | `backend/tests/test_commands.py::test_width_change_preserves_member_ids`<br>`backend/tests/integration/test_reference_house.py::test_reference_house_scenario_matches_golden` |
| BM-5 | Same snapshot and generator version give byte-identical canonical schedules | `backend/tests/test_timber.py::test_generation_is_deterministic_and_order_independent`<br>`backend/tests/test_estimating.py::test_schedule_matches_independent_ecmascript_implementation`<br>`backend/tests/test_estimating.py::test_estimate_is_deterministic` |
| BM-6 | Member endpoints are in model coordinates; schedule totals reconcile | `backend/tests/test_timber.py::test_regenerated_snapshot_is_valid_and_exact`<br>`backend/tests/test_estimating.py::test_reference_house_schedule`<br>`backend/tests/integration/test_sequences.py::test_random_command_sequences_keep_every_invariant` |
| BM-7 | An invalid operation or stale base leaves head and model unchanged | `backend/tests/test_project.py::test_stale_preview_is_a_revision_conflict`<br>`backend/tests/test_api.py::test_service_errors_map_to_statuses`<br>`backend/tests/integration/test_sequences.py::test_random_command_sequences_keep_every_invariant` |

## Dependencies (dependencies.md §8)

| ID | Event | Tests |
|---|---|---|
| DEP-1 | Width change: new revision; artifacts stale until regenerated | `backend/tests/test_artifacts.py::test_old_head_artifacts_never_current_for_new_head`<br>`backend/tests/test_estimating.py::test_width_change_recomputes_schedule_and_estimate` |
| DEP-2 | Display-only change: no geometry recomputation | N/A — VS-01 has no display-only command (D043); every command changes semantic data. |
| DEP-3 | Negative width: validation error, no revision or invalidation | `backend/tests/test_commands.py::test_rejections`<br>`backend/tests/test_api.py::test_service_errors_map_to_statuses` |
| DEP-4 | The same command twice: idempotent, no duplicate revision | `backend/tests/test_project.py::test_idempotent_retry_writes_nothing`<br>`backend/tests/test_api.py::test_5_retry_is_replayed` |
| DEP-5 | Confirming an old preview after another edit: `REVISION_CONFLICT` | `backend/tests/test_project.py::test_stale_preview_is_a_revision_conflict`<br>`frontend/e2e/vs01.spec.ts › a commit from another tab gives a conflict and a fresh preview` |
| DEP-6 | An old worker finishing after a new one stays superseded | N/A — VS-01 has no workers; artifacts are derived synchronously and served only when their fingerprint matches (ART-001). Closest guarantees: `backend/tests/test_artifacts.py::test_generator_version_bump_makes_artifacts_stale`<br>`backend/tests/test_artifacts.py::test_rederivation_stores_one_row` |
| DEP-7 | Removing a grid bay retires its members and keeps the others | `backend/tests/test_commands.py::test_removing_interior_line_retires_exactly_its_members`<br>`backend/tests/test_timber.py::test_removing_an_interior_line_retires_exactly_its_members` |
| DEP-8 | Missing unit prices: `UNAVAILABLE` or partial, never a $0 total | `backend/tests/test_estimating.py::test_no_book_is_unavailable_never_zero`<br>`backend/tests/test_estimating.py::test_partial_book`<br>`frontend/tests/components.test.tsx › shows an unavailable estimate as not configured, never a zero total` |

## Artifacts (artifacts.md §10)

| ID | Contract test | Tests |
|---|---|---|
| ART-1 | The manifest lists exactly the four VS-01 artifact types | `backend/tests/test_artifacts.py::test_create_and_commit_report_stored_statuses`<br>`backend/tests/test_api.py::test_vs01_flow` |
| ART-2 | Plan dimensions and the mesh footprint match the semantic footprint | `backend/tests/test_geometry.py::test_reference_house_plan`<br>`backend/tests/test_geometry.py::test_reference_house_mesh`<br>`backend/tests/integration/test_reference_house.py::test_reference_house_scenario_matches_golden` |
| ART-3 | Plan, mesh, and schedule list the same 58 member IDs as the inventory | `frontend/tests/meshScene.test.ts › draws one box per member with the schedule's and plan's IDs (artifacts.md §10 test 3)`<br>`backend/tests/integration/test_reference_house.py::test_reference_house_scenario_matches_golden` |
| ART-4 | Schedule aggregates match; the default estimate is `UNAVAILABLE` with a null total | `backend/tests/test_estimating.py::test_reference_house_schedule`<br>`backend/tests/test_estimating.py::test_no_book_is_unavailable_never_zero` |
| ART-5 | After a width change, the old head's artifacts are not current for the new head | `backend/tests/test_artifacts.py::test_old_head_artifacts_never_current_for_new_head` |
| ART-6 | Clients refuse to composite views with mismatched revisions | `frontend/tests/pairing.test.ts › refuses mismatched revisions even when both are CURRENT`<br>`frontend/e2e/vs01.spec.ts › AC-02, AC-07: a width change updates both views and the schedule, never pairing old geometry` |
| ART-7 | Every `CURRENT` envelope is preliminary, with no structural claim | `backend/tests/test_artifacts.py::test_envelope_contract_and_fingerprint`<br>`backend/tests/integration/test_reference_house.py::test_reference_house_scenario_matches_golden` |
| ART-8 | Estimate quantities match the schedule aggregates for the same revision | `backend/tests/test_estimating.py::test_width_change_recomputes_schedule_and_estimate`<br>`backend/tests/integration/test_sequences.py::test_random_command_sequences_keep_every_invariant` |

## Interfaces (interfaces.md §9)

| ID | Contract test | Tests |
|---|---|---|
| IF-1 | OpenAPI validates examples; the generated TypeScript client compiles | `backend/tests/test_api.py::test_1_openapi_is_current_and_requests_conform`<br>`frontend/package.json#check:api`<br>`frontend/package.json#typecheck` |
| IF-2 | A preview has no database side effects | `backend/tests/test_api.py::test_2_preview_writes_nothing`<br>`backend/tests/test_project.py::test_previews_write_nothing` |
| IF-3 | A confirmed commit moves the head exactly once | `backend/tests/test_api.py::test_3_commit_moves_head_exactly_once` |
| IF-4 | Two concurrent commits on one base: one winner, the other 409 | `backend/tests/test_api.py::test_4_concurrent_commits_have_one_winner`<br>`backend/tests/test_project.py::test_concurrent_commits_have_one_winner` |
| IF-5 | An idempotent retry duplicates nothing | `backend/tests/test_api.py::test_5_retry_is_replayed`<br>`backend/tests/test_project.py::test_idempotent_retry_writes_nothing` |
| IF-6 | Unauthorized access cannot read snapshots or artifacts | `backend/tests/test_api.py::test_6_other_actors_get_404_and_anonymous_callers_401`<br>`frontend/e2e/vs01.spec.ts › sign-in rejects unknown tokens, and other actors cannot see a project` |
| IF-7 | Plan, mesh, and schedule identify the same source revision | `backend/tests/test_api.py::test_7_plan_mesh_schedule_share_source_revision`<br>`backend/tests/integration/test_reference_house.py::test_reference_house_scenario_matches_golden` |
| IF-8 | Unsupported geometry returns a structured error, never an exception or invented output | `backend/tests/test_api.py::test_8_unsupported_geometry_is_a_structured_422`<br>`backend/tests/test_commands.py::test_random_footprints_never_raise` |
