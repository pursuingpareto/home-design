# MODEL-003 — Typed commands and candidate snapshots

**Status:** Implemented (2026-11-18). See §12 for implementation notes.  
**Owner module:** `model` (uses `timber` for regeneration)  
**Slice:** VS-01  
**Depends on:** `MODEL-001` (done), **`TIMBER-001`** (deterministic generator and rule-conformance check; to be specified and implemented first)  
**Unblocks:** `MODEL-004` (revision persistence, idempotency, preview storage), the API task, `UI-001`  
**Closes:** gap M5 (command argument schemas)

## 1. Objective and user-visible behavior

Provide a pure, deterministic library function that turns a **typed command** and a **base snapshot** into a **candidate change**:

- a new candidate snapshot;
- a semantic diff, including added, removed, and updated member IDs;
- the change classification (routine or consequential) and the impacted artifacts;
- warnings;

or a structured validation failure. This is steps 2–6 of the change protocol (dependencies.md §5) without storage, HTTP, or authorization.

There is no user-visible behavior yet. Every later edit path (API, UI, and future AI proposals) goes through this function, so it is the single validated way to change the model (AGENTS.md principle 3).

## 2. Inputs and governing documents

- [interfaces.md](../../architecture/interfaces.md) §2–4 (envelope, preview, commit), [dependencies.md](../../architecture/dependencies.md) §4–5 (classification, protocol), [building-model.md](../../architecture/building-model.md) §5–6.
- Decisions:
  - [D026](../../product/decisions/D026-canonical-units-identity-persistence.md) units and concurrency.
  - [D029](../../product/decisions/D029-canonical-json-rfc8785.md)/[D030](../../product/decisions/D030-canonical-snapshot-entity-order.md) canonical form.
  - [D031](../../product/decisions/D031-vs01-unsupported-configurations.md)–[D034](../../product/decisions/D034-vs01-level-bounds.md) supported domain.
  - [D035](../../product/decisions/D035-validation-stages-detail-codes.md)–[D037](../../product/decisions/D037-error-related-paths.md) errors.
  - [D039](../../product/decisions/D039-frame-member-defaults.md)/[D040](../../product/decisions/D040-setmembersection-role-default.md) member defaults.
  - [D041](../../product/decisions/D041-deterministic-id-minting.md) ID minting.
  - [D042](../../product/decisions/D042-stable-grid-line-ids.md) grid lines.
- `TIMBER-001` interface (assumed): `generate(snapshot) -> members`. It produces every member for the snapshot's grid, levels, and `member_defaults` under `vs01-post-beam-1`, with keys and endpoints but without IDs. MODEL-003 assigns IDs: it reuses an existing ID when the key exists in the base, and otherwise mints one per D041.

## 3. Scope

**In scope**

- Pydantic models for the command envelope and the arguments of every VS-01 command (§4), exported to JSON Schema and committed with a drift test (as in D028/MODEL-001).
- `propose(base, command, *, actor_id, at) -> ProposeResult`, which runs these steps:
  1. validate the envelope and arguments;
  2. check that `base_revision_id` matches the base snapshot;
  3. apply the arguments to a copy of the base;
  4. assign new grid-line IDs (D042);
  5. regenerate members through `TIMBER-001`;
  6. mint IDs (D041);
  7. validate the candidate with MODEL-001;
  8. compute the diff, the classification, the impacted artifacts, and the warnings.
- `instantiate_template(project_id, *, actor_id, command_id, at) -> Snapshot` for `CreateReferenceProject`.
- `command_hash(command)` (D029).
- Shared test vectors: the D041 UUIDv5 vector, confirmed by an independent implementation.

**Non-goals (later tasks)**

- Persistence, revision head, idempotency store, preview tokens and expiry, and the `REVISION_CONFLICT` race between commits → `MODEL-004`.
- HTTP endpoints, authentication, authorization → API task.
- Dependency-graph engine, artifact invalidation and recomputation → dependency/artifact tasks.
- Member generation itself and rule conformance → `TIMBER-001`.
- Per-member overrides (D040), material commands (§4.6), and AI proposals.

## 4. Command contracts (§10; all items approved)

### 4.1 Envelope

```json
{
  "command_id": "<uuid>",
  "project_id": "<uuid>",
  "base_revision_id": "<uuid>",
  "type": "SetFootprintDimensions",
  "args": { "width_m": 12.192, "depth_m": 7.3152 }
}
```

- The envelope is a union discriminated by `type`. An unknown `type` is `INVALID_ENUM` at path `type`.
- `args` is strict: every key is required and unknown keys are rejected, the same rules as D038.
- `CreateReferenceProject` uses a **creation envelope** without `project_id` and `base_revision_id`: `{command_id, type, args}`. The server assigns the project ID (D041).
- The actor is never in the body (interfaces.md §2); `propose` receives `actor_id` from the caller.

### 4.2 Commands

| `type` | `args` | Effect on the candidate | Regenerates members |
|---|---|---|---|
| `CreateReferenceProject` | `{}` | Instantiates Reference House 001 (§6) | yes (from nothing) |
| `SetFootprintDimensions` | `{width_m, depth_m}` (both required) | Sets `Footprint.width_m`, `depth_m` | yes: endpoints move, keys and IDs kept |
| `SetStoryHeights` *(renames `SetLevelElevations`)* | `{story_heights_m: [h0, h1]}` | `L0.story_height_m = h0`; `L1.elevation_m = h0`; `L1.story_height_m = h1` (D033 consistency holds by construction; L0 stays at elevation 0, D034) | yes: post lengths, beam planes |
| `SetGableRoofParameters` | `{pitch_rad, eave_overhang_m}` | Sets those two roof fields. `ridge_axis` and `ridge_offset_m` are not arguments, since D031 fixes them | no (the rule does not use the roof) |
| `SetTimberGrid` | `{x_lines: [GridLineArg], y_lines: [GridLineArg]}` | Replaces both axes' lines (§4.3) | yes: survivors keep IDs, split or merged bays retire beams |
| `SetMemberSection` | `{role, section_id}` | Sets `member_defaults[role].section_id` (D040) | yes: that role's sections change, IDs kept |
| `AddSection` | `{nominal_label, actual_width_m, actual_depth_m}` | Adds a `rectangular` `Section` catalog record (D038); ID minted with creation key `"section"` | no |
| `UndoToRevision` | `{target_revision_id}` | Candidate entities equal the target revision's entities exactly, IDs included (§4.5) | no (content copied) |

### 4.3 `SetTimberGrid` arguments

`GridLineArg` is either:

- `{"id": "x2", "fraction": 0.5}`, which keeps the existing line `x2` and sets its fraction; or
- `{"fraction": 0.5}`, which adds a new line.

Rules:

- **Full replacement:** lines of the base grid that are not listed are removed.
- **Order:** entries must be strictly ascending by `fraction`. They are validated, not re-sorted (D030).
- **New line IDs:** new lines receive IDs in argument order. On each axis, `n` starts at one more than the largest number among the base grid's lines and the listed existing lines (D042).
- **Errors:**
  - an `id` that is not a base line on that axis is `DANGLING_REFERENCE` at `args.x_lines[k].id`;
  - the same `id` listed twice is `DUPLICATE_LINE_ID`;
  - endpoints, bounds, and bay lengths are checked on the candidate (D032, D035).

### 4.4 `SetMemberSection`

- `role` must be a role the frame's rule generates (`POST`, `BEAM`); any other role is `UNSUPPORTED_VALUE`.
- `section_id` must reference an existing `Section`, or the result is `DANGLING_REFERENCE` or `WRONG_REFERENCE_KIND` at `args.section_id`.

### 4.5 `UndoToRevision`

- **What the caller supplies:** the target snapshot. Loading it is `MODEL-004`'s job.
- **Result:** the candidate gets a new `revision_id` (D041) with `parent_revision_id` = base (history stays linear, D026), and the target's `entities` and `building`.
- **Restored IDs:** members whose keys were retired after the target come back **with their original IDs**. This is restoration, not re-addition, so it is a stated exception to D041's "re-added keys get new IDs".
- **Redo:** redo is `UndoToRevision` to a later revision in the history.

### 4.6 Not in VS-01

- Commands that change a role's material, or add materials. Reference House 001 has one material, and changing species is not required by any VS-01 acceptance criterion.
- Per-member edits (D040).

## 5. Result contract

```text
ProposeResult = Accepted(candidate: CandidateChange) | Rejected(ValidationResult)

CandidateChange:
  candidate: Snapshot                 # validated by MODEL-001
  revision_id, operation_id: UUID     # minted per D041
  command_hash: "sha256:…"            # SHA-256 of the canonical envelope (D029)
  is_noop: bool                       # candidate entities equal the base's (canonical compare)
  classification: "routine" | "consequential"
  diff:
    changes: [{entity_kind, entity_id, field, before, after}]   # non-member records; `field` uses D036 path syntax relative to the record
    members: {added: [{id, generation_key}], removed: [{id, generation_key}], updated: [id]}
  impacted_artifacts: ["plan2d", "mesh3d", "timber_schedule", "preliminary_estimate"]
  warnings: [{code, message}]         # always includes PRELIMINARY_UNVERIFIED
```

- **Diff ordering:** all diff arrays are sorted deterministically: `changes` by `(entity_kind, entity_id, field)`, member lists by `generation_key`, and `updated` by ID. `before` and `after` are whole JSON values; for example, the full `x_lines` array.
- **Impacted artifacts:** every committing command lists all four artifacts, because each artifact's fingerprint covers the whole canonical snapshot (artifacts.md §2.3). Narrower lists wait on per-artifact input selectors, the open question C5.
- **No-ops:** a no-op command (for example, setting the current width) is accepted with an empty diff and `is_noop: true`. §10 proposes that committing a no-op creates **no revision**.
- **Classification (proposed):** `SetGableRoofParameters` and `AddSection` are **routine**, because they regenerate no framing (dependencies.md §4). Every other command is **consequential**. The table is versioned and server-enforced.
- **Timestamps:** `at` is supplied by the caller (the commit time) and becomes `created_at`. The function reads no clock, so preview and commit produce identical IDs and diffs, and their canonical candidates differ only in `created_at`.

## 6. `CreateReferenceProject`

`instantiate_template` copies the Reference House 001 non-member records with new IDs, using the creation key `"template/" + fixture record ID` (D041). It rewrites every reference to use the new IDs, sets the building name, and then generates all members through `TIMBER-001`, using creation keys `"generation/" + key`.

- `parent_revision_id` is `null`.
- The result must validate. It must also equal the fixture **semantically**: same values, same keys, same 58 members, with generated member coordinates within 1e-6 m (they are generator output; the fixture stores hand-entered decimals, see generation-rules.md "Numeric evaluation"), and with only IDs and revision metadata otherwise differing. A test checks this by mapping IDs through creation keys.

## 7. Errors

- **Stage order:** envelope and argument errors use paths under the envelope (`args.width_m`, `type`) and stop processing (D035 stage 1). Reference errors in arguments (lines, sections, targets) are stage 2. Candidate errors come from MODEL-001 with snapshot paths.
- **Linking candidate errors to arguments:** when a candidate error's `path` or `related_paths` is a field set directly by an argument, the argument's path is added to `related_paths` (D037). For example, a `width_m: 23` bay-length error carries `related_paths` = [footprint `width_m`, `args.width_m`]. Each command defines its argument-to-field mapping in code, and tests cover it.
- **Base-revision mismatch:** `base_revision_id` ≠ the base snapshot's `revision_id` is rejected with top-level `REVISION_CONFLICT` (interfaces.md §7) before anything is computed. Guarding the head against concurrent commits remains `MODEL-004`'s job.
- **Project mismatch:** `project_id` ≠ the base's `project_id` is `VALIDATION_FAILED` at `project_id`.
- **No new detail codes** are proposed. Every case above maps to existing D035/D042 codes.

## 8. Acceptance criteria and automated tests

1. **Width change** (building-model.md §9 test 4): a new candidate, all 58 member IDs and keys preserved, endpoints moved, `members.updated` lists the **48** members that move, and the classification is consequential. *(Corrected during implementation: the 10 members lying entirely on line `x0`, at x = 0, do not move when the width changes; the draft said "all 58".)*
2. **Remove an interior grid line** (dependencies.md §8): removing `x2` keeps every ID on `x0`, `x1`, `x3`. It retires the `x2` posts and the `x1-x2` and `x2-x3` beams and adds `x1-x3` beams with D041 IDs.
3. **Insert a line:** a new line gets ID `x4`; the split bay's beams are retired and new ones added; the endpoint posts keep their IDs.
4. **Invalid commands are rejected with exact codes and paths:** negative width, a 30 m width, a bay over 24' (with `args.width_m` in `related_paths`), an unknown type, an unknown line ID, a non-generated role in `SetMemberSection`, a missing argument, and an unknown argument.
5. **Base unchanged:** after a rejected or accepted propose, the base snapshot's canonical bytes are unchanged.
6. **Determinism:** the same inputs give a byte-identical canonical candidate and diff. Preview and commit (same `command_id`, a different `at`) give identical IDs and diffs.
7. **ID vector:** the D041 vector, reproduced by `tests/vectors/` and confirmed by an independent implementation (for example, Node in `generate.mjs`).
8. **Two actors, one `command_id`:** two actors using the same `command_id` mint different IDs.
9. **Undo round trip:** after a width change, `UndoToRevision` back gives entities canonically equal to the original, with the original member IDs.
10. **Template:** `CreateReferenceProject` equals the fixture semantically (§6; member coordinates within 1e-6 m), and two projects share no entity IDs.
11. **No-op:** setting the current width gives `is_noop: true` and an empty diff.
12. **Robustness:** property tests confirm that random argument values never raise, and every accepted candidate passes MODEL-001.
13. The committed command JSON Schema is current, and validates the examples in this file.

## 9. Implementation guidance (not prescriptive)

- **Location:** `backend/src/homedesign/model/commands/`: envelope and argument models, one module per command (`apply(base, args) -> draft`), `propose`, `diff`, `mint`.
- **Immutability:** apply each command to a deep copy. Snapshots are frozen Pydantic models, so build the candidate as a JSON value and validate it through `validate_value`.
- **Minting:** keep it in one function, `mint(purpose, project_id, actor_id, command_id, creation_key)`, tested against the vector.

## 10. Proposals approved by the product owner

1. ~~**Command set and arguments** as in §4.2, including the rename `SetLevelElevations` → `SetStoryHeights`.~~ **Approved: [D043](../../product/decisions/D043-vs01-command-set.md)** for the five simple commands and the rename; `SetTimberGrid` arguments, `AddSection`, and `UndoToRevision` remain items 2–4. interfaces.md §2 updated, D034 noted.
2. ~~**Full-replacement `SetTimberGrid`**, with existing-line references and ID-less new lines (§4.3).~~ **Approved**; specified in [interfaces.md §2.1](../../architecture/interfaces.md#21-settimbergrid-arguments).
3. ~~**Add `AddSection`**, so `SetMemberSection` can use sizes beyond the template's two. Defer material commands (§4.6).~~ **Approved**; added to interfaces.md §2. Its classification follows item 7.
4. ~~**Include `UndoToRevision`**, with exact restoration of IDs as a stated exception to D041 (§4.5).~~ **Approved: [D044](../../product/decisions/D044-undo-to-revision.md)**; interfaces.md §2, D041, and building-model.md §5 updated. Restored snapshots are validated against current rules.
5. ~~**The result contract** (§5): the diff shape, all four artifacts always listed, and `is_noop`.~~ **Approved**; specified in [interfaces.md §3](../../architecture/interfaces.md#3-preview-contract), which adds `revision_id` to the preview and defines how added and removed non-member records appear in `changes`.
6. ~~**No-op commands** create no revision when committed.~~ **Approved: [D045](../../product/decisions/D045-no-op-commits.md)**. The preview has `revision_id: null` and `confirmation_required: false`; the commit returns HTTP 200 with the current head; the attempt is logged.
7. ~~**Classification:** roof parameters and `AddSection` are routine; all else is consequential.~~ **Approved**; specified as table `vs01-change-classes-1` in [dependencies.md §4.1](../../architecture/dependencies.md#41-vs-01-classification-table-vs01-change-classes-1).
8. ~~**Error reporting:** argument paths, the argument-to-field `related_paths`, and `REVISION_CONFLICT` for a mismatched base (§7).~~ **Approved**; specified in [interfaces.md §7.1](../../architecture/interfaces.md#71-command-errors).
9. ~~**The creation envelope** for `CreateReferenceProject`, and template instantiation through creation keys (§6).~~ **Approved**; specified in [interfaces.md §2](../../architecture/interfaces.md#2-command-envelope).

Approved items that change contracts update interfaces.md §2–4 and dependencies.md §4. Items 1, 4, and 6 are product behavior and are recorded as decisions.

## 11. Definition of done

- All §8 tests pass. The command JSON Schema is exported and drift-checked. The D041 vector is committed and independently confirmed.
- interfaces.md and dependencies.md are updated for approved items. The task index and status docs are updated.
- Changed files, tests, limitations, and next steps are summarized (AGENTS.md).

## 12. Implementation notes (2026-11-18)

**Delivered:**
- `backend/src/homedesign/model/commands/`:
  - `envelope.py`: argument and envelope models, the `type`-discriminated union, and `parse_command`;
  - `mint.py`: D041 minting with the fixed namespace;
  - `propose.py`: `propose`, `propose_create`, `CandidateChange.to_preview_dict()`, the classification table, the diff, and argument linking;
  - `templates/reference-house-001.json`: a packaged copy of the fixture, kept byte-identical by a test.
- `docs/architecture/schemas/commands.v1.schema.json`: the exported command schema, drift-checked by `schema_export --check`.
- An `ids` section in `tests/vectors/jcs/vectors.json`, computed by an independent ECMAScript UUIDv5, which reproduces the D041 vector `5f9ff518…`.

**Tests:** 232 pytest tests pass, 51 of them new, covering every §8 criterion:
- width change (48 members updated, IDs preserved, also on a fixture base);
- interior line removal (22 retired, 6 added with D041 IDs, survivors kept);
- line insertion (new ID `x4`), and new line numbers that skip a removed end line;
- story heights, the routine roof command, and `AddSection` followed by `SetMemberSection`;
- 18 rejection cases with exact codes, paths, and argument-linked `related_paths`, plus `REVISION_CONFLICT` and envelope misuse;
- base immutability;
- preview and commit agreement (identical except `created_at`);
- the UUIDv5 vectors, and two actors minting different IDs;
- an undo round trip that restores original IDs, and an undo no-op;
- template semantic equality through creation keys, and two projects sharing no IDs;
- the no-op contract, and the fixture-base regeneration rewriting 38 members' last bits;
- the preview shape, the classification table matching dependencies.md §4.1, never-raises properties, and the command schema.

An ad hoc fuzz run of 2,000 random command chains (up to six commands each, including undo) produced no exceptions and never mutated a base. Every accepted candidate re-validated.

**Choices made during implementation:**

- **Pipeline:** the draft is validated first. If only stage 5 fails, the draft just has stale members, and a regenerating command then regenerates them. Members keep the base's ID per surviving key, and new keys are minted. The result is validated again. Any stage 1–4 failure is returned with arguments linked through each command's field map.
- **`REVISION_CONFLICT`:** it has no detail issues, and it is checked before the envelope is parsed whenever `base_revision_id` is a readable string.
- **Project mismatch:** it uses detail code `DANGLING_REFERENCE` at `project_id` (interfaces.md §7.1 named only the top-level code).
- **A new line sent with `"id": null`:** this is `WRONG_TYPE` at the line's path. New lines must omit `id`.
- **Envelope misuse:** sending the creation envelope to `propose`, or another type to `propose_create`, is `INVALID_ENUM` at `type`. A creation command wrapped in a normal envelope fails stage 1 on `project_id` and `base_revision_id`.
- **`command_hash`:** SHA-256 over the canonical envelope with unset optional fields omitted, so `{"fraction": 0.5}` is never hashed as `{"id": null, …}`.
- **Shared error mapping:** the snapshot validator's Pydantic-to-code mapping was extracted (`code_for_pydantic_error`) so command errors use identical codes.

**Limitations:**

- No persistence, idempotency store, preview tokens, or authorization (`MODEL-004` and the API task).
- `propose` trusts the caller to pass the right `target` snapshot for `UndoToRevision`. It checks only the ID and project.
- Messages are English-only and not part of the contract.

