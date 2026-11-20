# MODEL-005 — Model schema version 2

**Status:** Implemented (2026-11-19), together with `TIMBER-002`. All six §12 proposals were approved (item 4 as [D057](../../product/decisions/D057-vs02-frame-command-roof-classification.md)). See §14 for implementation notes.  
**Owner module:** `model` (schema, validation, commands); `project` for the stored-data guard (§8.3)  
**Slice:** VS-02  
**Depends on:** VS-01 (complete). Specified before `TIMBER-002`, but **merged together with it** on one branch (§9).  
**Unblocks:** `TIMBER-002` (the `vs02-frame-1` rule fills the shapes defined here), then `CONN-001`, `ART-002`, `DEP-001`, `UI-003`, `TEST-002`

## 1. Objective and user-visible behavior

Define the version 2 semantic model that every other VS-02 task builds on, and retire version 1 ([D055](../../product/decisions/D055-pre-release-schema-replacement.md)):

- the five new member roles of [D052](../../product/decisions/D052-vs02-frame-members.md);
- the frame parameters that drive them, with supported-range bounds;
- the `Connection` record and per-junction-class connection types of [D054](../../product/decisions/D054-vs02-connection-catalog.md);
- the validation rules and detail codes for all of the above;
- the command that edits the frame parameters, and the version 2 classification table;
- committed JSON Schemas and OpenAPI for version 2;
- rejection of version 1 snapshots, and a guard against local databases that still hold them.

**User-visible behavior** arrives with the merge (§9): new projects are Reference House 001 v2, and the API accepts `SetFrameParameters`. Generating the new members is `TIMBER-002`; generating connections is `CONN-001`. Until `CONN-001`, a version 2 project has connection types but no `Connection` records.

## 2. Inputs and governing documents

- [VS-02 scope](../acceptance-tests/vs-02.md) §12 (AC2-01, AC2-02, AC2-03, AC2-07).
- Decisions:
  - [D051](../../product/decisions/D051-vs02-slice-boundary.md)–[D056](../../product/decisions/D056-dependency-selectors.md), especially D052 (roles and parameters), D053 (reference values), D054 (connections), D055 (replace, don't migrate);
  - [D035](../../product/decisions/D035-validation-stages-detail-codes.md)–[D037](../../product/decisions/D037-error-related-paths.md) (stages, codes, paths), [D038](../../product/decisions/D038-field-presence-catalog-records.md) (field presence), [D039](../../product/decisions/D039-frame-member-defaults.md)/[D040](../../product/decisions/D040-setmembersection-role-default.md) (per-role defaults), [D041](../../product/decisions/D041-deterministic-id-minting.md)/[D042](../../product/decisions/D042-stable-grid-line-ids.md) (IDs and keys), [D046](../../product/decisions/D046-conformance-validation-stage.md) (conformance), [D032](../../product/decisions/D032-vs01-numeric-bounds.md)/[D034](../../product/decisions/D034-vs01-level-bounds.md) (bounds).
- [building-model.md](../../architecture/building-model.md) §3, §5, §6; [interfaces.md](../../architecture/interfaces.md) §2, §7.1, §8; [dependencies.md](../../architecture/dependencies.md) §4.
- Existing code: `homedesign/model/schema.py`, `validation.py`, `codes.py`, `vs01.py`, `commands/`, `schema_export.py`; `homedesign/timber/rules/`.

## 3. Scope

**In scope**

- Pydantic models for version 2 (§4), exported to `docs/architecture/schemas/` with the drift check.
- Frame parameters and their bounds (§5).
- Validation stages 1–5 extended for the new records (§6), with new detail codes in `codes.py` and building-model.md §6.1.
- The rule registry interface extended so a rule declares the junction classes it generates, and returns expected connections for conformance (§6.4). `TIMBER-002` and `CONN-001` fill it in.
- `SetFrameParameters`, `SetMemberSection` for every version 2 role, and the classification table `vs02-change-classes-1` (§7).
- Retiring version 1: constants, rule registration, template, schema files, and a stored-data guard (§8).

**Non-goals (later tasks)**

- Geometry, keys, and counts for the new members, the v2 fixture, and the ECMAScript oracle → `TIMBER-002`.
- Junction rules, connection keys, connection generation, the preview's connection diff, and `SetConnectionType` → `CONN-001`.
- New payload content (connection markers, connection counts, "each" estimate lines) → `ART-002`.
- Selectors and computed `impacted_artifacts` → `DEP-001`. Until then every committing command still lists all four artifacts.
- Browser rendering and editors for the new roles and parameters → `UI-003`, except the minimum needed to keep `main` green (§9).
- Any upgrade path for version 1 data (D055).

## 4. Version 2 records

### 4.1 Changes at a glance

| Record | Change | Record `schema_version` |
|---|---|---|
| Snapshot | `model_schema_version` becomes **2** | — |
| `TimberMember` | `member_role` enum is the version 2 role set (§4.2) | **2** |
| `FrameSystem` | Adds `parameters`, `connection_ids`, and `connection_defaults` (§4.3) | **2** |
| `Connection` | New kind (§4.4) | **1** |
| `Building`, `Footprint`, `Level`, `GableRoof`, `TimberGrid`, `Section`, `Material` | Unchanged | 1 |

**Record versions are per kind:** a kind's `schema_version` changes only when its own shape changes. This keeps the meaning of building-model.md §8 ("each record has a schema version") and makes per-kind migrations possible after the first release. Every value is still checked exactly (stage 1, `UNSUPPORTED_SCHEMA_VERSION`).

### 4.2 Member roles

```text
MemberRole = POST | BEAM | SILL | FLOOR_JOIST | PRINCIPAL_RAFTER | PURLIN | KNEE_BRACE
```

- `RAFTER`, reserved but never generated in VS-01, is **removed**. It is replaced by `PRINCIPAL_RAFTER` (D052). A common-rafter role can return when a rule generates one; building-model.md §3.2 forbids pretend records.
- `FLOOR_JOIST` is now generated.
- The enum is ordered as above wherever an order is needed for display. Canonical ordering of `member_defaults` keys stays RFC 8785 key order (D029).

### 4.3 `FrameSystem` (version 2)

```json
{
  "id": "…", "kind": "FrameSystem", "schema_version": 2,
  "grid_id": "…",
  "generation_mode": "DETERMINISTIC_RULE",
  "member_ids": ["…"],
  "member_defaults": {
    "POST": {"section_id": "…", "material_id": "…"},
    "BEAM": {"section_id": "…", "material_id": "…"},
    "SILL": {"section_id": "…", "material_id": "…"},
    "FLOOR_JOIST": {"section_id": "…", "material_id": "…"},
    "PRINCIPAL_RAFTER": {"section_id": "…", "material_id": "…"},
    "PURLIN": {"section_id": "…", "material_id": "…"},
    "KNEE_BRACE": {"section_id": "…", "material_id": "…"}
  },
  "parameters": {
    "joist_spacing_m": 0.6096,
    "purlins_per_slope": 2,
    "knee_brace_leg_m": 0.9144,
    "knee_braces_level_1": true,
    "knee_braces_eave": true
  },
  "connection_ids": [],
  "connection_defaults": {
    "post-beam": "PEGGED_MORTISE_TENON",
    "post-sill": "PEGGED_MORTISE_TENON",
    "brace": "PEGGED_MORTISE_TENON",
    "joist-beam": "HOUSED_DOVETAIL",
    "rafter-peak": "BRIDLE",
    "rafter-foot": "PEGGED_MORTISE_TENON",
    "purlin-rafter": "PEGGED_MORTISE_TENON"
  }
}
```

- **`parameters`** is a strict object. All five keys are required (D038). Their meaning and bounds are §5.
- **`connection_ids`** lists every `Connection` record, in ascending `generation_key` order, exactly as `member_ids` lists members (D030).
- **`connection_defaults`** maps each junction class to its connection type, as `member_defaults` maps roles to sections (D054, D040). It must cover every class the rule generates (§6.2). Junction class names keep D054's spelling.
- **Why on `FrameSystem`:** the parameters, like `member_defaults`, are inputs to the frame's generation rule. Keeping every rule input on one record gives `DEP-001` one place to select from.

### 4.4 `Connection` (new)

```json
{
  "id": "…", "kind": "Connection", "schema_version": 1,
  "junction_class": "post-beam",
  "connection_type": "PEGGED_MORTISE_TENON",
  "member_ids": ["<receiving member>", "<entering member>"],
  "location_m": [3.6576, 0.0, 2.7432],
  "generation_key": "…"
}
```

| Field | Type | Meaning (D054) |
|---|---|---|
| `junction_class` | enum of the 7 classes | Which kind of junction this is |
| `connection_type` | enum of the 5 types | Catalog key; must equal `connection_defaults[junction_class]` (conformance) |
| `member_ids` | exactly 2 UUIDs, ordered | `[receiving, entering]` |
| `location_m` | `[x, y, z]` | Where the entering member's reference axis meets the receiving member's |
| `generation_key` | string | Derived from the two members' keys; format set by `CONN-001` |

- **Connection types:** `PEGGED_MORTISE_TENON`, `BRIDLE`, `HOUSED_DOVETAIL`, `STEEL_KNIFE_PLATE`, `JOIST_HANGER`.
- **Junction classes:** `post-beam`, `post-sill`, `brace`, `joist-beam`, `rafter-peak`, `rafter-foot`, `purlin-rafter`.
- **Allowed types per class** are the D054 catalog table, held in one constant (`CONNECTION_CATALOG`, catalog version `vs02-connections-1`) that stage 4 and `CONN-001` both use.
- **No capacity fields.** The record carries no sizes, fasteners, or ratings (D054, AC2-07).
- **IDs:** connections are generated records. Their IDs are minted from `"generation/" + generation_key` (D041), like members, so **generation keys must be unique across members and connections together** (§6.2).

### 4.5 Committed schema files

- `snapshot.v1.schema.json` is replaced by **`snapshot.v2.schema.json`**. The snapshot schema file is named after the model schema version.
- `commands.v1.schema.json`, `artifacts.v1.schema.json`, and `openapi.v1.json` keep their names. They follow the API version (`/api/v1`), which does not change (interfaces.md §8: model schema versions are independent of the API version). Their content is regenerated.
- Schema titles and descriptions say "model schema version 2" instead of "VS-01".

## 5. Frame parameters

### 5.1 Fields and bounds

| Field | Type | Reference value (D053) | Physical check (stage 3) | Supported range (stage 4, inclusive) |
|---|---|---|---|---|
| `joist_spacing_m` | number | 0.6096 (24") | > 0 | 0.3048–1.2192 (12"–48") |
| `purlins_per_slope` | integer | 2 | ≥ 0 | 0–4 |
| `knee_brace_leg_m` | number | 0.9144 (3'-0") | > 0 | 0.4572–1.2192 (1'-6"–4'-0"), and the fit rule below |
| `knee_braces_level_1` | boolean | true | — | — |
| `knee_braces_eave` | boolean | true | — | — |

These are **supported-range limits for the generator, not structural limits** (as D032). Nothing about them claims adequacy (AC2-07).

### 5.2 Cross-checks

- **Braces must fit their beams.** When either brace plane is enabled, `2 × knee_brace_leg_m` must not exceed the shortest bay on either axis (+1e-6 m), so the two braces under one beam never overlap. This is checked on the full candidate, like bay lengths (D032), so a grid or footprint change can be rejected for the braces it would produce. The error is `OUT_OF_SUPPORTED_RANGE` at `parameters.knee_brace_leg_m`, with `related_paths` naming the footprint dimension and the grid line fractions that bound the shortest bay (D037).
- **Braces always fit their posts.** The leg maximum (4') is below the minimum story height (8', D034), so no post-length check is needed. A test pins this, so a later change to either bound cannot silently break it.
- **Zero is allowed** for purlins, and both brace planes may be off. The rule then generates no members of that role. The role's `member_defaults` entry stays required, because D039 ties defaults to the roles a rule *can* generate, not to the current count. This keeps `SetMemberSection` usable before the members exist.
- **A bay may have no joists** if the spacing is not less than the bay. That is a valid configuration; `TIMBER-002` specifies the positions.

## 6. Validation

The five stages and their top-level codes are unchanged (building-model.md §6). This section lists only what version 2 adds.

### 6.1 Stage 1 — syntactic

- `model_schema_version` must be 2. Version 1 (or any other value) is `UNSUPPORTED_SCHEMA_VERSION` at `model_schema_version`. Record versions are checked per kind (§4.1).
- `Connection` is a known kind. `member_ids` has exactly two items. The new enums report `INVALID_ENUM`. `purlins_per_slope` must be an integer (`INTEGER_OUT_OF_RANGE` for 2.5, as D029).
- `parameters` and `connection_defaults` are strict: missing or unknown keys report `MISSING_FIELD` and `UNKNOWN_FIELD`. A `connection_defaults` key that is not a junction class is `INVALID_ENUM`.

### 6.2 Stage 2 — referential

| Check | Code | Path, related paths |
|---|---|---|
| Each `Connection.member_ids[i]` exists and is a `TimberMember` | `DANGLING_REFERENCE`, `WRONG_REFERENCE_KIND` (existing) | `member_ids[i]` |
| The two members differ | **`SELF_CONNECTION`** (new) | `member_ids[1]`; related: `member_ids[0]` |
| `FrameSystem.connection_ids` is exactly the set of `Connection` records | **`CONNECTION_SET_MISMATCH`** (new) | `connection_ids` |
| `connection_ids` ascend by `generation_key` | `ORDER_VIOLATION` (existing) | `connection_ids` |
| Every `Connection` is referenced from the frame | `UNREFERENCED_ENTITY` (existing) | the record |
| `generation_key` is unique across members **and** connections | `DUPLICATE_GENERATION_KEY` (existing, widened) | the later record's key; related: the first's |
| `connection_defaults` covers every class the rule generates | **`MISSING_CONNECTION_DEFAULT`** (new) | `connection_defaults`; `value` names the class |
| `member_defaults` covers every role the rule generates | `MISSING_ROLE_DEFAULT` (existing; now 7 roles) | `member_defaults` |

### 6.3 Stage 3 — geometric

- `joist_spacing_m` and `knee_brace_leg_m` must be > 0, and `purlins_per_slope` ≥ 0: `OUT_OF_RANGE`.
- `location_m` needs no geometric check here; its agreement with the members is conformance.

### 6.4 Stage 4 — domain

- Frame parameter bounds and the brace-fit rule (§5): `OUT_OF_SUPPORTED_RANGE`.
- `connection_defaults[class]` and every `Connection.connection_type` must be allowed for their class by the catalog (§4.4): `UNSUPPORTED_VALUE`. For a connection, `related_paths` names its `junction_class`.
- `generation_rule_version` must be a registered rule. After §8, only `vs02-frame-1` is registered, so `vs01-post-beam-1` is `UNSUPPORTED_VALUE` (existing behavior).
- Member roles must be generated by the rule (existing); the rule now generates all seven.

### 6.5 Stage 5 — conformance

Connections join members in conformance (D046): the records must be exactly what the rule produces. The new codes mirror the member codes:

| Code (new) | Meaning | Path |
|---|---|---|
| `MISSING_GENERATED_CONNECTION` | The rule generates a connection key that no record has | the frame's `connection_ids`; `value` is the key |
| `UNEXPECTED_CONNECTION` | A record's key is not generated by the rule | its `generation_key` |
| `CONNECTION_GEOMETRY_MISMATCH` | `location_m` differs from the rule by more than 1e-6 m in any coordinate | `location_m` |
| `CONNECTION_ASSIGNMENT_MISMATCH` | `junction_class`, `member_ids`, or `connection_type` differs from the rule | that field; for `connection_type`, related: `connection_defaults[class]` |

**Rule interface:** `Rule` gains `generated_junction_classes` and `generate_connections(snapshot, members)`. The model compares expected and actual connections generically, so the codes above are implemented here once. Until `CONN-001`, `vs02-frame-1` declares all seven classes (so the template carries the D054 defaults from the start) and generates no connections, so any `Connection` record is `UNEXPECTED_CONNECTION`.

## 7. Commands and classification

### 7.1 `SetFrameParameters` (new)

| `type` | `args` | Effect | Regenerates members |
|---|---|---|---|
| `SetFrameParameters` | `{joist_spacing_m, purlins_per_slope, knee_brace_leg_m, knee_braces_level_1, knee_braces_eave}`, all required | Replaces `FrameSystem.parameters` | Yes: joists, purlins, braces (and, after `CONN-001`, their connections). Keys and IDs on surviving positions are kept (D042) |

- **One command for all five,** like `SetGableRoofParameters`: the browser's "untouched fields send stored values" pattern (UI-002) already fits, and one "Frame" tab maps to one command.
- **Argument links:** each `args.<field>` maps to `parameters.<field>`, so a candidate error carries the argument path in `related_paths` (interfaces.md §7.1). A brace-fit error from a grid or footprint change links that command's arguments instead.
- Setting the current values is a no-op (D045).

### 7.2 Existing commands under version 2

- `CreateReferenceProject`: creates Reference House 001 v2 (§8.2).
- `SetMemberSection`: `role` may be any of the seven roles. `RAFTER` is now `INVALID_ENUM` (stage 1), not `UNSUPPORTED_VALUE`.
- `SetFootprintDimensions`, `SetStoryHeights`, `SetTimberGrid`, `AddSection`, `UndoToRevision`: unchanged arguments. More members regenerate.
- `SetGableRoofParameters`: unchanged arguments, but it now **regenerates members**: principal rafters and purlins follow the pitch (D052).
- `SetConnectionType` is specified by `CONN-001`, which adds its row to the table below.

### 7.3 Classification table `vs02-change-classes-1`

Replaces `vs01-change-classes-1` in dependencies.md §4.1. Every preview and commit records the new version.

| Command | Class | Reason |
|---|---|---|
| `AddSection` | routine | Adds a catalog record; no member changes |
| `SetGableRoofParameters` | **consequential** (was routine) | Regenerates principal rafters and purlins. dependencies.md §4 treats any roof change that regenerates framing as consequential |
| `SetFrameParameters` | consequential | Regenerates framing; may retire and create members |
| `SetFootprintDimensions`, `SetStoryHeights`, `SetTimberGrid`, `SetMemberSection`, `UndoToRevision`, `CreateReferenceProject` | consequential | As in VS-01 |

The roof change affects the browser: its roof editor applies changes directly today, so it must switch to the preview flow in the merge (§9).

## 8. Retiring version 1 (D055)

### 8.1 Code

- `MODEL_SCHEMA_VERSION = 2`, with per-kind record versions (§4.1).
- `vs01-post-beam-1` is unregistered and deleted, with its tests. `vs02-frame-1` (`TIMBER-002`) is the only registered rule.
- The constants module `model/vs01.py` is renamed `model/limits.py`. Its VS-01 bounds stay valid for version 2, and the frame parameter bounds (§5) are added beside them, each citing its decision.

### 8.2 Template and fixture

- `fixture.snapshot.json` and the packaged template become Reference House 001 v2, produced and verified by `TIMBER-002`. The v1 fixture is not kept in the tree; git history holds it.
- `CreateReferenceProject` copies the non-generated records (now including the four new sections, 4×8, 8×10, 6×8, and 4×6) with creation keys `"template/" + fixture record ID`, then generates members (and, after `CONN-001`, connections) with `"generation/" + key` (D041).

### 8.3 Stored data

D055 says local databases are recreated, not migrated. Two small tools make that explicit instead of leaving a confusing failure on first read:

- **Guard:** the migration runner (`homedesign.project.migrate`) refuses to run against a database that holds any revision with `model_schema_version` below 2. It exits non-zero with a message naming the database and the fix. Nothing is deleted.
- **Reset:** `scripts/dev.sh --reset` drops and recreates the local `homedesign` database, then migrates it. Passing the flag is the confirmation. Without it, `dev.sh` shows the guard's message and stops.
- The test database is already recreated on every run (MODEL-004 §7).

## 9. Keeping `main` green: the merge with `TIMBER-002`

Retiring version 1 breaks every VS-01 test until `vs02-frame-1` exists ([VS-02 scope](../acceptance-tests/vs-02.md) §12.2). MODEL-005 and TIMBER-002 are therefore one branch and one merge, which also carries the **smallest** changes elsewhere that keep CI passing. The later tasks still own the real work:

| Area | Change in this merge | Later owner of the full change |
|---|---|---|
| `mesh3d`, `timber_schedule` payloads | Role enums become the version 2 set. Both already list every member generically | `ART-002` (connections, markers, counts) |
| `plan2d` payload | Lists posts and beams only, as today. The other roles are left out **temporarily**, and artifacts.md §5 says so | `ART-002` adds them |
| Integration invariants (`TEST-001`) | Plan inventory compared for posts and beams only, citing the temporary note; mesh and schedule still cover every member | `ART-002` restores full coverage |
| Golden record, UI fixture, OpenAPI, frontend `schema.d.ts` | Regenerated as reviewed diffs (D055) | `TEST-002` extends the scenario |
| Browser | Roof editor switches to the preview flow (§7.3). New roles get a neutral fallback color in 3D. Role labels come from the payload | `UI-003` (real styling, Frame tab, markers) |
| Release note | Commit message tells developers to run `scripts/dev.sh --reset` | — |

## 10. Acceptance criteria and automated tests

Run on the merged branch, against the v2 fixture from `TIMBER-002`:

1. **Round trip (AC2-01):** the v2 fixture validates, and its canonical bytes are unchanged by a parse and re-serialize (building-model.md §9 test 1).
2. **Version 1 rejected (AC2-01):** a snapshot with `model_schema_version: 1` is `VALIDATION_FAILED` / `UNSUPPORTED_SCHEMA_VERSION` at `model_schema_version`. A v2 snapshot naming `vs01-post-beam-1` is `UNSUPPORTED_CONFIGURATION` / `UNSUPPORTED_VALUE`. A record with the wrong per-kind version is rejected at its `schema_version`.
3. **Every new detail code** (`SELF_CONNECTION`, `CONNECTION_SET_MISMATCH`, `MISSING_CONNECTION_DEFAULT`, and the four conformance codes) is produced by a minimal mutation of the fixture, with exact `path` and `related_paths`. So is widened `DUPLICATE_GENERATION_KEY` (a connection reusing a member's key).
4. **Catalog:** every disallowed (class, type) pair is `UNSUPPORTED_VALUE`, in `connection_defaults` and on a record. Every allowed pair passes. The constant matches D054's table.
5. **Parameter bounds:** each bound is accepted at its limit and rejected just beyond it, at stage 3 or 4 as §5 says. `purlins_per_slope: 2.5` is `INTEGER_OUT_OF_RANGE`.
6. **Brace fit:** a `SetTimberGrid` or `SetFootprintDimensions` that makes the shortest bay shorter than twice the leg is rejected, with the command's arguments in `related_paths`. Turning both brace planes off makes it valid. The leg-versus-story bound is pinned.
7. **`SetFrameParameters`:** accepted changes regenerate members and keep IDs on surviving keys (exercised with `TIMBER-002`'s rule). Current values are a no-op. Each argument's error carries its argument path.
8. **Roles:** `SetMemberSection` accepts all seven roles and rejects `RAFTER` with `INVALID_ENUM`.
9. **Classification:** the table matches dependencies.md §4.1. Committing `SetGableRoofParameters` without a preview is `PREVIEW_REQUIRED`.
10. **Stored-data guard** *(PostgreSQL only)*: the runner refuses a database holding a version 1 revision, with the message, and deletes nothing. It migrates a fresh database normally.
11. **Robustness:** property tests send random `SetFrameParameters` arguments; `propose` never raises, and every accepted candidate re-validates.
12. **Schemas:** `snapshot.v2.schema.json`, the command schema, and OpenAPI are current (drift check), and the examples in this file validate against them.

## 11. Implementation guidance (not prescriptive)

- **Order on the shared branch:**
  1. schema, codes, and stages 1–4, tested against hand-built snapshots;
  2. `TIMBER-002`'s rule and fixture;
  3. conformance and commands;
  4. the §9 changes;
  5. regenerated records last, so their diffs reflect the final code.
- **Catalog constant:** keep the junction classes, types, and allowed pairs together in `model/connections.py`, with the catalog version string, so `CONN-001` and `ART-002` import one definition.
- **Typed copies of the role enum:** payload modules currently repeat the role `Literal`. Import the model's `MemberRole` instead, so the next role change touches one line.

## 12. Proposals for approval

1. ~~**Version 2 records** (§4):~~
   - ~~roles with `RAFTER` removed;~~
   - ~~`FrameSystem` gains `parameters`, `connection_ids`, and `connection_defaults`;~~
   - ~~the `Connection` record as D054 describes it;~~
   - ~~per-kind record versions;~~
   - ~~`snapshot.v2.schema.json`, with the other schema files keeping their API-version names.~~

   **Approved** (2026-11-19); recorded in building-model.md §3.3 as a VS-02 amendment, not yet implemented.
2. ~~**Frame parameters** (§5): five fields, their bounds, the brace-fit rule, and zero purlins or braces allowed, with defaults still required.~~ **Approved** (2026-11-19); recorded in building-model.md §3.3 and §6 as a VS-02 amendment, not yet implemented.
3. ~~**Validation** (§6): three new stage 2 codes, four new stage 5 codes, `DUPLICATE_GENERATION_KEY` widened across members and connections, and generic connection conformance through the rule interface.~~ **Approved** (2026-11-19); recorded in building-model.md §6 and §6.1 as a VS-02 amendment, not yet implemented.
4. ~~**Commands and classification** (§7): one `SetFrameParameters` command; `SetGableRoofParameters` becomes consequential; table `vs02-change-classes-1`.~~ **Approved: [D057](../../product/decisions/D057-vs02-frame-command-roof-classification.md)** (2026-11-19); interfaces.md §2 and dependencies.md §4.1 carry VS-02 amendments, not yet implemented.
5. ~~**Retiring version 1** (§8): the rule deleted, `vs01.py` renamed, the v1 fixture removed, the migration guard, and `scripts/dev.sh --reset`.~~ **Approved** (2026-11-19); recorded in building-model.md §8 as a VS-02 amendment, not yet implemented.
6. ~~**Merge scope** (§9): the temporary posts-and-beams-only `plan2d`, the matching invariant, and the browser's roof flow change.~~ **Approved** (2026-11-19); the interim `plan2d` gap is noted in artifacts.md §5.

Approved items update building-model.md §3 and §6, interfaces.md §2 and §7.1, and dependencies.md §4.1. Item 4's roof reclassification changes product behavior, so it is recorded as a decision.

## 13. Definition of done

- All §10 tests pass on the merged MODEL-005 + TIMBER-002 branch, together with the regenerated VS-01 suite, Vitest, and Playwright. CI passes.
- building-model.md, interfaces.md, dependencies.md, and artifacts.md (the §9 note) are updated. The task index and status docs are updated.
- Changed files, tests, limitations, and next steps are summarized (AGENTS.md).

## 14. Implementation notes (2026-11-19)

Implemented on one branch with [TIMBER-002](TIMBER-002.md); its notes cover the rule, fixture, and oracle.

**Delivered:**
- `backend/src/homedesign/model/`:
  - `schema.py`: version 2 records, `FrameParameters`, `Connection`, and per-kind record versions;
  - `limits.py` (renamed from `vs01.py`): `MODEL_SCHEMA_VERSION = 2`, `RECORD_SCHEMA_VERSIONS`, frame parameter bounds;
  - `connections.py`: the D054 catalog (`vs02-connections-1`);
  - `codes.py` and `validation.py`: the seven new codes, and the stage 2–4 checks of §6;
  - `commands/`: `SetFrameParameters`, roof regeneration, table `vs02-change-classes-1`.
- `homedesign/project/migrate.py`: the outdated-database guard (`OutdatedDatabase`), run before any write.
- `scripts/dev.sh --reset`; a migration refusal now stops `dev.sh` with the fix.
- Regenerated: `snapshot.v2.schema.json` (renamed), `commands.v1.schema.json`, `artifacts.v1.schema.json`, `openapi.v1.json`, and `frontend/src/api/schema.d.ts`.
- §9 merge scope: payload `role` enums use the model's `MemberRole`; `plan2d` lists posts and beams only (also in the ECMAScript oracle); the integration invariants follow; the roof editor previews; the new roles share a neutral 3D color; the UI fixture, golden record, and price books in tests cover all seven timber lines.

**Tests:** 495 backend tests pass (51 more than VS-01's 444), with 51 Vitest and 15 Playwright tests, all against both stores where relevant. New or rewritten for this task:
- the mutation table: version 1 rejected, per-kind record versions, every frame parameter bound at and beyond its limit, `purlins_per_slope: 2.5`, non-boolean flags, brace fit (rejected, then valid with braces off), and every connection rule (self-connection, wrong kind, unlisted, a key shared with a member, a disallowed type in a default and on a record, wrong member count, unexpected connection);
- commands: `SetFrameParameters` (IDs kept, no-op, argument-linked errors, unknown argument), the brace-fit error linking `args.x_lines`, roof edits consequential and moving only the 8 rafters and 12 purlins, overhang moving nothing, `RAFTER` rejected, and a property test of random frame parameters;
- the outdated-database guard against a separate, name-guarded PostgreSQL database;
- the guard also refused the developer's real local `homedesign` database (6 version 1 revisions) without changing it.

**Choices made during implementation:**

- **Unlisted connections** are reported once, as `CONNECTION_SET_MISMATCH` with the record in `related_paths`, exactly as unlisted members are reported by `MEMBER_SET_MISMATCH`. §6.2 also listed `UNREFERENCED_ENTITY` for them, which would have reported the same fault twice.
- **Connection conformance runs only once members conform,** so a connection is never compared against members that are themselves wrong.
- **Three conformance codes cannot occur yet:** `MISSING_GENERATED_CONNECTION`, `CONNECTION_GEOMETRY_MISMATCH`, and `CONNECTION_ASSIGNMENT_MISMATCH` need a rule that generates connections. Until `CONN-001`, a direct test of the shared comparison exercises them, and the catalog-coverage test records that.
- **D036 paths:** junction classes contain hyphens, so their paths are quoted, for example `connection_defaults["post-beam"]`.
- **Roof edits:** one command covers pitch and overhang, so an overhang-only edit is consequential too, although it moves no member (D058: no rafter tails).
- **Routine commands in tests:** tests that needed a routine commit used the roof command; they now use `AddSection`, the only routine command left.

**Consequences to know:**

- **Braces constrain the grid.** With the reference house's 3'-0" legs, every bay must be at least 6'-0" while braces are on. A narrower grid is rejected with the brace leg's path, linked to the grid and footprint, until the leg is shortened or the braces are turned off.
- **Local databases must be recreated:** `scripts/dev.sh --reset` (D055).

**Limitations:**

- No connections are generated, and the preview has no connection diff (`CONN-001`).
- `plan2d` shows posts and beams only (`ART-002`).
- The browser has no Frame tab yet, and a frame-parameter error from another tab points to the Sections tab, where `FrameSystem` fields map today (`UI-003`). *Resolved by UI-003 (2026-11-20): `FrameSystem` paths map by field, so `parameters…` points to the Frame tab (UI-003 §7.3).*
- `impacted_artifacts` still lists all four artifacts (`DEP-001`).

