# TIMBER-001 — Deterministic post/beam generator and rule conformance

**Status:** Ready for implementation — all §10 proposals approved (2026-11-18)  
**Owner module:** `timber`  
**Slice:** VS-01  
**Depends on:** `MODEL-001` (done)  
**Unblocks:** `MODEL-003` (regeneration), `GEOM-001` and `EST-001` (member inventory)  
**Resolves:** the main `MODEL-001` limitation (members are not checked against the rule)

## 1. Objective and user-visible behavior

Implement `vs01-post-beam-1` as a pure, deterministic function from a snapshot's parameters to the member inventory the rule defines. Use it to **check conformance**: every snapshot's members must be exactly what the rule generates (within the D026 comparison epsilon).

There is no user-visible behavior yet. After this task, a snapshot cannot be valid while its members disagree with its footprint, levels, grid, or member defaults. `MODEL-003` uses the generator to regenerate frames.

## 2. Inputs and governing documents

- [generation-rules.md](../../reference-projects/vermont-timber-house/generation-rules.md) (`vs01-post-beam-1`, as amended by D039 and D042).
- Decisions:
  - [D025](../../product/decisions/D025-reference-house-001-vs01-fixture.md) fixture;
  - [D026](../../product/decisions/D026-canonical-units-identity-persistence.md) units and the 1e-6 m epsilon;
  - [D033](../../product/decisions/D033-level-story-height.md)/[D034](../../product/decisions/D034-vs01-level-bounds.md) levels;
  - [D035](../../product/decisions/D035-validation-stages-detail-codes.md)–[D037](../../product/decisions/D037-error-related-paths.md) validation and errors;
  - [D039](../../product/decisions/D039-frame-member-defaults.md) member defaults;
  - [D042](../../product/decisions/D042-stable-grid-line-ids.md) line-based keys.
- [building-model.md](../../architecture/building-model.md) §3.1, §5–6; [interfaces.md](../../architecture/interfaces.md) §2 (creation envelope).

## 3. Scope

**In scope**

- `homedesign.timber`: a rule registry keyed by `generation_rule_version`, with one rule, `vs01-post-beam-1`.
- `generate(snapshot) -> tuple[GeneratedMember, ...]`, where `GeneratedMember` = `{generation_key, member_role, start_m, end_m, section_id, material_id}`. It has **no IDs**; assigning IDs is `MODEL-003`'s job (D041). The tuple is sorted by `generation_key` in code-unit order.
- `conformance(snapshot) -> issues`: compares the snapshot's members with `generate(snapshot)`.
- Wiring conformance into snapshot validation as a new stage (§5).
- A cross-language vector for the generated inventory of Reference House 001 (§7).
- Updates to `MODEL-001` tests whose mutations change parameters without regenerating members (§8).

**Non-goals**

- Assigning member IDs, applying commands, and assigning new grid-line IDs → `MODEL-003`.
- Roof members, joists, rafters, braces, connections, machining, or any structural check (the rule's own non-goals).
- Schedules, meshes, plans → artifact tasks.

## 4. Generator contract (§10; approved)

### 4.1 Preconditions

`generate` is defined only for snapshots that pass validation stages 1–4. That means a supported rule and mode, exactly two levels, D031–D034 bounds, and `member_defaults` with `POST` and `BEAM` entries. It never raises for such input. For other input it is not called; the validator guarantees this.

### 4.2 Numeric evaluation

All values are IEEE-754 doubles, evaluated **exactly as written, left to right**, with no fused multiply-add, no reordering, and **no rounding or snapping**:

```text
x(line)  = footprint.origin_m[0] + footprint.width_m * line.fraction
y(line)  = footprint.origin_m[1] + footprint.depth_m * line.fraction
z0       = level[0].elevation_m
z1       = level[1].elevation_m
z_eave   = level[1].elevation_m + level[1].story_height_m
```

Every language with IEEE-754 doubles produces identical bits from these formulas. Python and ECMAScript both do, and the vector in §7 checks it.

**Consequence for the fixture:**
- The fixture stores hand-entered decimals, chosen in D025 so that bay lengths read as 12'-0".
- For lines `x1` and `x2`, `10.9728 × ⅓` evaluates to `3.6575999999999995`, and `10.9728 × ⅔` to `7.315199999999999`. The fixture stores `3.6576` and `7.3152`.
- So **38 of the 58 fixture members differ from generator output in the last bits**, all within 1e-6 m. Y stations and all z values are bit-identical.
- The fixture still **conforms**, because conformance uses the epsilon. It is no longer a bit-exact generator output.

### 4.3 Members

The keys, roles, axes, and planes are as in generation-rules.md. Section and material come from `member_defaults[role]` (D039). Posts at every `(x, y)` line pair on both stories, and beams on `plane-L1` and `plane-eave` along both axes, give:

```text
posts = 2 · nx · ny
beams = 2 · (ny · (nx − 1) + nx · (ny − 1))
```

For Reference House 001 (nx = 4, ny = 3) that is 24 posts and 34 beams.

## 5. Conformance as validation stage 5 (approved — D046)

The rule is defined only for supported configurations, so conformance can run only after stage 4 passes. [D035](../../product/decisions/D035-validation-stages-detail-codes.md) defines four stages; this task proposes **adding stage 5, "conformance"**, with top-level `VALIDATION_FAILED`. A member that disagrees with the rule is invalid data, not an unsupported configuration. The stage runs only when stages 1–4 pass.

Proposed new detail codes (stage 5):

| Detail code | Situation | `path` | `value` | `related_paths` (D037) |
|---|---|---|---|---|
| `MISSING_GENERATED_MEMBER` | The rule generates a key that no member has | `entities[<frame>].member_ids` | the missing key | — |
| `UNEXPECTED_MEMBER` | A member's key is not generated by the rule | `entities[<member>].generation_key` | the key | — |
| `MEMBER_GEOMETRY_MISMATCH` | `start_m` or `end_m` differs from the rule by more than 1e-6 m in any coordinate | `entities[<member>].start_m` or `.end_m` | — | — |
| `MEMBER_ASSIGNMENT_MISMATCH` | `member_role`, `section_id`, or `material_id` differs from what the rule assigns | `entities[<member>].<field>` | the stored value | for section and material: `entities[<frame>].member_defaults.<ROLE>.<field>` |

- Issues are reported for every member, in the usual `(path, code)` order.
- A reversed member (start and end swapped) is a geometry mismatch.
- Adding a stage and adding codes amends D035, so it is recorded as a decision (§10).

## 6. Module boundary

`homedesign.timber` depends on `homedesign.model.schema` (types only). `homedesign.model.validation` reaches the rule through the registry (`timber.rules.get(version)`). The model module never contains rule logic, and a later rule version is added by registering it (building-model.md §10, "framing rules embedded or plug-in": this answers it with a registry).

## 7. Acceptance criteria and automated tests

1. **Fixture inventory:** `generate(fixture)` yields 58 members (24 posts, 34 beams) with exactly the fixture's keys, roles, section IDs, and material IDs. Endpoints are within 1e-6 m. The 38 bit-level differences are asserted explicitly, so a change in arithmetic is caught.
2. **The fixture conforms:** stage 5 passes, and the fixture stays valid end to end.
3. **Cross-language vector:** `tests/vectors/` gains the canonical inventory of the fixture's parameters (and its `sha256:` fingerprint), computed by an independent ECMAScript implementation of §4.2 in `generate.mjs`. Python's `generate` must match byte for byte.
4. **Determinism:** identical output across runs and across entity orderings, and canonical bytes are identical.
5. **Count formula:** for every grid size allowed by D032 (2–7 stations per axis), the counts match §4.3 and every key is unique.
6. **Key stability (D042):**
   - Inserting a line leaves the keys on all other lines unchanged.
   - Removing interior line `x2` removes exactly the `x2` posts and the `x1-x2` and `x2-x3` beams, and adds `x1-x3` beams.
   - Renumbering is impossible: keys use IDs, not positions.
7. **Member defaults (D039):** changing `POST.section_id` changes only the posts' `section_id`. No key or coordinate changes.
8. **Conformance mutations:**
   - An endpoint moved by 5e-7 m still passes; one moved by 2e-6 m gives `MEMBER_GEOMETRY_MISMATCH`.
   - A removed member (and its `member_ids` entry) gives `MISSING_GENERATED_MEMBER`.
   - An extra member with an unknown key gives `UNEXPECTED_MEMBER`.
   - A post with the beam section gives `MEMBER_ASSIGNMENT_MISMATCH`, with the D037 related path.
   - Swapped endpoints give `MEMBER_GEOMETRY_MISMATCH`.
9. **Stage gating:** a snapshot that fails stage 4 (for example, a 30 m width with stale members) reports only stage-4 issues.
10. **Robustness:** the never-raises property tests from MODEL-001 cover stage 5. Random mutations produce no exceptions.

## 8. Changes to existing tests and docs

- **MODEL-001 tests that expect a valid result after changing parameters** must regenerate members, or expect stage-5 issues:
  - case 29 (width at the lower bound) is rebuilt with generated members;
  - `d042-line-ids-need-not-be-sequential` must rename the line in the member keys too. Otherwise it now correctly fails with `MISSING_GENERATED_MEMBER` and `UNEXPECTED_MEMBER`, which is worth a separate test.
- building-model.md §6 and §6.1 already document stage 5 and its codes (D046), and generation-rules.md documents numeric evaluation. `backend/tests/test_catalog_doc.py` currently matches only stages 1–4 (regex `[1-4]`), so it must be widened to `[1-5]` when `codes.py` gains stage 5. Until then the docs are ahead of the code. The MODEL-001 §13 limitation is marked resolved when this task is done.
- **Wording corrections** (§10, item 4): interfaces.md §2 (creation envelope) and MODEL-003 §6 say a created project "equals the fixture in every value". Under §4.2 that should read "equals the fixture in every value and key, with generated member coordinates within 1e-6 m."

## 9. Implementation guidance (not prescriptive)

- `backend/src/homedesign/timber/`: `rules/__init__.py` (registry), `rules/vs01_post_beam_1.py` (`generate`, `conformance`), `inventory.py` (`GeneratedMember`).
- Build members from the line lists directly; never index by position (D042).
- Compare coordinates with `abs(a - b) <= 1e-6` per axis, as building-model.md §9 test 6 and D026 prescribe.

## 10. Proposals approved by the product owner

1. ~~**Generator contract** (§3–4.1, §4.3): `generate` returns ID-less members sorted by key, defined only for snapshots passing stages 1–4.~~ **Approved**; interfaces.md §6 updated.
2. ~~**Numeric evaluation** (§4.2): exact IEEE formulas with no rounding or snapping. The fixture keeps its hand-entered decimals and conforms within 1e-6 m, but is not bit-identical to generator output.~~ **Approved**; recorded in [generation-rules.md, "Numeric evaluation"](../../reference-projects/vermont-timber-house/generation-rules.md#numeric-evaluation).
3. ~~**Conformance as validation stage 5**, with the four new detail codes and their D037 mappings (§5).~~ **Approved: [D046](../../product/decisions/D046-conformance-validation-stage.md)**; building-model.md §6 and §6.1 updated, with D035 and D037 noted.
4. ~~**Wording corrections** to interfaces.md §2 and MODEL-003 §6 (§8).~~ **Approved**; both corrected, plus MODEL-003 §8 test 10.
5. ~~**Rule registry** as the module boundary (§6), answering building-model.md §10's "embedded or plug-in" question.~~ **Approved**; interfaces.md §1 and building-model.md §10 updated.

## 11. Definition of done

- All §7 tests pass, including updated MODEL-001 tests. The exported JSON Schema is unchanged; stage 5 adds no schema fields. The JCS and inventory vectors are regenerated and committed.
- building-model.md, generation-rules.md, interfaces.md, MODEL-001 §13, MODEL-003 §6, the decision register, and the status docs are updated.
- Changed files, tests, limitations, and next steps are summarized (AGENTS.md).
