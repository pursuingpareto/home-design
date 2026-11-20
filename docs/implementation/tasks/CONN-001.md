# CONN-001 — Connection generation and `SetConnectionType`

**Status:** Approved (2026-11-20), ready to implement. All ten §11 proposals were approved; items 7–10 are recorded as [D059](../../product/decisions/D059-vs02-junction-rules-connection-type-command.md). Nothing is implemented.  
**Owner module:** `timber` (junction rules, fixture, oracle); `model` (regeneration, preview diff, `SetConnectionType`); `api` (preview response)  
**Slice:** VS-02  
**Depends on:** [`TIMBER-002`](TIMBER-002.md) and [`MODEL-005`](MODEL-005.md) (done). Merges on its own, with CI passing ([vs-02.md](../acceptance-tests/vs-02.md) §12.2).  
**Unblocks:** `ART-002` (connection markers, schedule counts, "each" estimate lines), then `DEP-001`, `UI-003`, `TEST-002`

## 1. Objective and user-visible behavior

Make `vs02-frame-1` generate the `Connection` records that [D054](../../product/decisions/D054-vs02-connection-catalog.md) defines, and add the command that switches a junction class's connection type:

- junction rules for the seven D054 classes, saying which member receives, which enters, and where `location_m` lies on the [D058](../../product/decisions/D058-datum-reference-axes.md) datum axes;
- a connection generation-key format that never collides with member keys;
- the Reference House 001 v2 connection count, **312**, with a formula;
- connection IDs that are kept, created, and retired with the members (D041, D042);
- a `connections` diff in the preview;
- `SetConnectionType {junction_class, connection_type}`, with its errors and classification.

**User-visible after this task:**
- Every project has connections, and every frame edit regenerates them.
- The preview lists added, removed, and updated connections.
- The API accepts `SetConnectionType`.

The plan, mesh, schedule, estimate, and browser do not show connections yet (`ART-002`, `UI-003`). Nothing about a connection claims capacity or adequacy (AC2-07).

## 2. Inputs and governing documents

- [VS-02 scope](../acceptance-tests/vs-02.md): §9 (the connection proposal), §12.1 (AC2-03, AC2-06, AC2-07), §12.2 (this task's scope).
- Decisions:
  - [D054](../../product/decisions/D054-vs02-connection-catalog.md) (records, catalog, and the open junction rules this task settles);
  - [D058](../../product/decisions/D058-datum-reference-axes.md) (every junction is an intersection of axes);
  - [D041](../../product/decisions/D041-deterministic-id-minting.md)/[D042](../../product/decisions/D042-stable-grid-line-ids.md) (IDs and keys), [D044](../../product/decisions/D044-undo-to-revision.md) (undo), [D045](../../product/decisions/D045-no-op-commits.md) (no-ops);
  - [D046](../../product/decisions/D046-conformance-validation-stage.md) (conformance), [D057](../../product/decisions/D057-vs02-frame-command-roof-classification.md) (classification table), [D039](../../product/decisions/D039-frame-member-defaults.md)/[D040](../../product/decisions/D040-setmembersection-role-default.md) (per-role defaults, the pattern for per-class types).
- [MODEL-005](MODEL-005.md) §4.4, §6.2–6.5, §14 and [TIMBER-002](TIMBER-002.md) §5, §6, §8, §13.
- [generation-rules.md](../../reference-projects/vermont-timber-house/generation-rules.md); [building-model.md](../../architecture/building-model.md) §3.3, §6; [interfaces.md](../../architecture/interfaces.md) §2–3, §7.1; [dependencies.md](../../architecture/dependencies.md) §4.
- Code:
  - `model/connections.py` (the catalog);
  - `timber/rules/vs02_frame_1.py` (`generate_connections` returns nothing yet);
  - `timber/inventory.py` (`GeneratedConnection`, `connection_conformance`);
  - `model/commands/propose.py` (`_regenerate`, `_diff`), `model/commands/envelope.py`, `api/models.py` (`PreviewResponse`);
  - `timber/fixture.py` and `tests/vectors/jcs/generate.mjs`.

## 3. Scope

**In scope**

- The junction rules (§4), keys and identity (§5), and counts (§6) in `vs02-frame-1`.
- Connection regeneration in `propose`, and the preview's `connections` diff (§7).
- `SetConnectionType` and its classification row (§8).
- The Reference House 001 v2 fixture with its 312 connections, and the ECMAScript oracle extended to connections (§9).
- Updates to the existing tests and documents that assume no connections (§10).

**Non-goals**

- Connection markers in `plan2d` and `mesh3d`, connection lists and counts in `timber_schedule`, "each" lines in `preliminary_estimate`, and price-book units → `ART-002`. The schedule's `NO_CONNECTIONS` assumption ("Joinery and machining are not included") stays until `ART-002` replaces it. When it does, the schedule and estimate assumptions must also say that junctions with no class (§4.4) are not counted, for example "Post splices and sill joints at grid stations are not counted" (§11 item 9).
- Selectors and exact `impacted_artifacts` → `DEP-001`. Until then every committing command, `SetConnectionType` included, lists all four artifacts.
- Browser display of connections, the connection-type editor, and connection counts in the confirmation dialog → `UI-003`. The browser receives the new preview field and ignores it.
- Placing, editing, or overriding individual connections (D054: not in VS-02).
- New junction classes or connection types: a new catalog version (D054). See §4.4.
- Peg, dowel, plate, and fastener sizes, machining, cut lengths, and any capacity or code check (D054, AC2-07).

## 4. Junction rules

### 4.1 Principle: one connection per entering member end

A connection is generated **for each member end that lands on another member's axis** and that one of the seven classes covers. The member whose end it is **enters**. The member it lands on **receives**. Where an end lands on several candidate members, exactly one receives, chosen by a fixed rule (§4.3).

- **Why:** a connection is one joint at one member end (D054: "where one member's end meets the other"). Counting ends ties the count directly to the frame: every beam, brace, joist, and purlin has two connections, every Level 0 post one, and every rafter pair three (§6). That reconciliation is what AC2-03 and AC2-06 ask for.
- **Alternative:** one connection per pair of members that meet at an end. A post foot at an interior station would then have four `post-sill` connections, one for each sill end there, and a rafter foot three (post, plate, and tie beam). This avoids choosing a receiving member, but counts joints that a builder would not cut, which inflates the per-piece estimate (D054 §"Estimate").

### 4.2 Rules per class

Notation follows generation-rules.md: lines are taken in ascending-fraction order, `xa-xb` and `ya-yb` are adjacent pairs, and `{plane}` is `plane-L1` or `plane-eave`. "The post below" a plane at station `(x, y)` is `frame/{x}/{y}/level-0/post` for `plane-L1` and `frame/{x}/{y}/level-1/post` for `plane-eave`.

| Class | Entering member and end | Receiving member | `location_m` | Per |
|---|---|---|---|---|
| `post-beam` | A beam, at each end. The end at `xa` (or `ya`) is the start, and the end at `xb` (or `yb`) is the end | The post below the beam's plane at that end's station | The beam's endpoint, which is the post's top | beam end |
| `post-sill` | A Level 0 post, at its foot | The **Y-direction sill in the post's bent** (on its X line): the sill of the Y bay that starts at the post's Y line, `frame/axis-y/{x}/{y}-{y_next}/plane-L0/sill`, or, on the last Y line, the bay that ends there | The post's start, which is the sill's endpoint | Level 0 post |
| `brace` | A knee brace, at its lower end | The post below the brace's plane, at the brace's end line | The brace's start `(…, z − L)`, on the post's axis | brace |
| `brace` | A knee brace, at its upper end | The brace's own beam: its key with `/brace/{end line}` replaced by `/beam` | The brace's end, on the beam's axis, `L` from the beam's end | brace |
| `joist-beam` | A floor joist, at each end | The X-direction Level 1 beam on that end's Y line, in the joist's X bay: `frame/axis-x/{ya}/{xa}-{xb}/plane-L1/beam` at the start and `frame/axis-x/{yb}/{xa}-{xb}/plane-L1/beam` at the end | The joist's endpoint, on the beam's axis | joist end |
| `rafter-peak` | The **north** principal rafter, at its top end | The **south** principal rafter on the same X line | The north rafter's end, `(x, y_ridge, z_ridge)`, which is also the south rafter's end | X line |
| `rafter-foot` | A principal rafter, at its foot | The **eave beam in the rafter's bent** (the tie beam): `frame/axis-y/{x}/{ya}-{yb}/plane-eave/beam` for the first Y bay (south) or the last Y bay (north) | The rafter's start, `(x, y_s or y_n, z_eave)`, which is the tie beam's endpoint | rafter |
| `purlin-rafter` | A purlin, at each end | The principal rafter on that end's X line and the purlin's slope: `frame/roof/{xa}/{slope}/principal-rafter` at the start and `frame/roof/{xb}/{slope}/principal-rafter` at the end | The purlin's endpoint, on the rafter's axis | purlin end |

- **Locations are copied, not computed.** `location_m` is the entering member's generated endpoint, bit for bit. No new formula is introduced, so the numeric rules of generation-rules.md carry over unchanged. Only the `z` of `rafter-peak` and `purlin-rafter` locations depends on `tan(pitch_rad)`.
- **They lie on both axes.** By D058, each location lies on the receiving member's axis, within its extent. A scratch check against the current generator found every one of the 312 within 1e-9 m. `post-beam`, `post-sill`, `rafter-peak`, and `rafter-foot` locations are exact, because both members' endpoints come from the same expressions.
- **Type and members:** `connection_type` is `connection_defaults[junction_class]`, as sections come from `member_defaults` (D039). `member_ids` is `[receiving ID, entering ID]`, from the candidate's members.
- **Zero cases:** braces off, zero purlins, or a bay without joists generate no members of that role, and so no connections of that class. The class's `connection_defaults` entry is still required (MODEL-005 §5.2, as for `member_defaults`).

### 4.3 Receiving members where an end meets several

Four ends land where more than one member could receive. The rules above choose as follows:

| End | Candidates | Chosen | Why |
|---|---|---|---|
| Beam end on `plane-L1` | Level 0 post (its top), Level 1 post (its foot) | **The post below** | The `plane-L1` braces run down the Level 0 posts (TIMBER-002 §5.2), so a beam, its brace, and its post form one triangle. On the eave plane the post below is the only candidate, so one rule covers both planes |
| Post foot | One to four sills ending at the station (two X, two Y) | **The Y sill in the post's bent** | Every station has one, and it is unique once "starts here, else ends here" is fixed. It matches the rafter-foot choice: the bent's own members receive |
| Rafter foot | Level 1 post (its top), the eave plate (X beam), the tie beam (Y beam in the bent) | **The tie beam** | It lies in the rafter's vertical plane, as braces lie in their beam's plane (D058). It is the traditional principal-rafter-to-tie-beam joint, and every bent has one |
| Rafter peak | Either rafter | **South receives, north enters** | A bridle has one receiving and one entering member; the choice is arbitrary but must be fixed |

### 4.4 Junctions that no class covers

The posts and sills are split at every story and station (D052, TIMBER-002), so some members meet with no D054 class to describe them:

- **Post to post at Level 1:** each Level 1 post's foot stands on a Level 0 post's top, at 12 stations in the reference house.
- **Sill to sill at stations,** and the eave plate and Level 1 post at a rafter foot, beyond the one receiving member chosen above.

**Approved (§11 item 9, option A):** generate no record for these. The task file, generation-rules.md, the reference house README, and D059 say so, and the count (§6) excludes them. `ART-002` adds an assumption line to the schedule and estimate, so their per-piece lines are not read as complete. Adding a class, for example `post-post` with a splice type, is a new catalog version (D054) and needs its own decision. It also needs a traditional and an engineered type, which the catalog does not have.

## 5. Keys, IDs, and identity

### 5.1 Generation key

```text
connection/{junction_class}/{receiving member key}/{entering member key}
```

For example, `connection/post-beam/frame/x1/y0/level-0/post/frame/axis-x/y0/x0-x1/plane-L1/beam`.

- **Derived from both members' keys** (D054), plus the class for readability, so a key survives exactly when both members survive and still meet.
- **No collision with members:** every member key starts with `frame/`, and every connection key with `connection/`. Generation keys stay unique across members and connections together (MODEL-005 §6.2).
- **Unique among connections:** in §4.2, no two connections share a (receiving, entering) pair. The two ends of a beam, joist, or purlin meet different members, and a brace's two ends meet a post and a beam.
- **Readable and parseable:** no member key contains `/frame/`, so the two member keys split at the second `/frame/`. A test pins this, so a later key format cannot make connection keys ambiguous.
- **Length:** at most 100 characters in the reference house. That is longer than member keys, but keys are never used in URLs.
- **Order:** `connection_ids` and inventories are sorted by key in code-unit order (D030), as for members. Connections therefore group by class: `brace`, `joist-beam`, `post-beam`, `post-sill`, `purlin-rafter`, `rafter-foot`, `rafter-peak`.

**Alternative:** a shorter key built from the entering member alone, such as `{entering key}/end/{line}`. It is shorter, but it does not name the receiving member, contrary to D054. It would also need a second form for brace ends.

### 5.2 IDs (D041)

- **Minting:** a new key gets `UUIDv5(…, "generation/" + key)` under purpose `"entity"`, exactly as members do. Creation keys are `generation/connection/…` and `generation/frame/…`, so the two never collide.
- **Regenerated with members:** whenever members regenerate, connections regenerate from the new members. A connection whose key survives keeps its ID. New keys get minted IDs, and removed keys are retired. A retired ID is never reused.
- **`CreateReferenceProject`:** already drops the template's connections and clears `connection_ids`. Its regeneration now mints all 312 (interfaces.md §2: "connections likewise").
- **Undo** restores the target revision's records, with their original IDs (D044). This needs no new code.
- **Invariant:** a surviving connection's `member_ids` never change. Its key names both members, and a member keeps its ID while its key survives. A test pins this.

### 5.3 Identity under edits

| Edit | Connections |
|---|---|
| Footprint, story heights, roof pitch | Every key survives; locations move (`updated`). A bay that gains or loses joists gains or loses their `joist-beam` connections |
| Joist spacing | Connections of surviving joist ordinals survive and move; the rest are added or retired |
| Purlins per slope | Likewise for purlin ordinals |
| A brace plane off, then on | Off: two connections per brace are retired. On: they return **with new IDs** (D041). Undo restores the originals (D044) |
| Insert or remove a grid line | Connections of the retired members are retired, and those of the new members are created. A post whose bent sill is in a split or merged Y bay gets a new `post-sill` key |
| `SetMemberSection` | No connection changes (D058: sections never move axes) |
| `SetConnectionType` | Every connection of the class is `updated` (type only); none is added or removed |
| Overhang only | No change (D058: no rafter tails) |

## 6. Counts

With `nx`, `ny` stations, `B = ny·(nx − 1) + nx·(ny − 1)` bay-lines per plane, and the TIMBER-002 member counts:

| Class | Count | Reference House 001 v2 |
|---|---|---|
| `post-beam` | 2 × beams = `4·B` | 68 |
| `post-sill` | Level 0 posts = `nx·ny` | 12 |
| `brace` | 2 × braces | 136 |
| `joist-beam` | 2 × joists | 60 |
| `rafter-peak` | `nx` | 4 |
| `rafter-foot` | rafters = `2·nx` | 8 |
| `purlin-rafter` | 2 × purlins | 24 |
| **Total** | `4·B + nx·ny + 3·nx + 2·(braces + joists + purlins)` | **312** |

**Reconciliation with the frame:** two connections per beam, brace, joist, and purlin; one per Level 0 post; three per rafter pair. Level 1 posts, sills, and the X-direction eave and Level 1 beams appear only as receiving members.

**Largest supported case** (TIMBER-002 §5.3: 7 × 7 stations, 12" joists, 4 purlins, both brace planes): `B = 84`, so 336 + 49 + 21 + 2 × (336 + 468 + 48) = **2,110 connections**, beside 1,216 members. Derivation stays synchronous (D051). This task measures `propose` for that case and reports the time; `TEST-002` sets any budget.

**Fixture size:** the fixture grows from 206 records to 518.

## 7. Regeneration and the preview diff

### 7.1 Regeneration

- **Order:** `_regenerate` generates members, then connections from the candidate with those members. It resolves `member_ids` through the new member IDs.
- **Commands that set `regenerate`:** every frame-changing command, and `SetConnectionType` (§8). A candidate whose only failures are stage 5 (stale members or connections) is regenerated, as today.
- **Validation:** the regenerated candidate is validated in full. Connection conformance (MODEL-005 §6.5) then compares real records for the first time. `MISSING_GENERATED_CONNECTION`, `CONNECTION_GEOMETRY_MISMATCH`, and `CONNECTION_ASSIGNMENT_MISMATCH` become reachable from fixture mutations.

### 7.2 `connections` in the preview (interfaces.md §3)

The preview response gains a required field beside `members`, with the same shape and ordering:

```json
"connections": {
  "added":   [{"id": "…", "generation_key": "connection/joist-beam/…"}],
  "removed": [{"id": "…", "generation_key": "connection/brace/…"}],
  "updated": ["…"]
}
```

- **`added` and `removed`:** `{id, generation_key}` entries, sorted by `generation_key`. Added IDs are exactly the IDs the commit will create (D041).
- **`updated`:** IDs of surviving connections whose record changed (canonical comparison), sorted by ID. Under §5.2, only `location_m` and `connection_type` can change.
- **Not in `changes`:** connection records are excluded from `changes`, as members are. The frame's `connection_ids` and `connection_defaults` still appear there, as `member_ids` and `member_defaults` do.
- **No-op:** all three lists are empty (D045).
- **Contract changes:**
  - interfaces.md §3 gains the field;
  - `api/models.py` gains `ConnectionChanges` on `PreviewResponse`;
  - OpenAPI and `frontend/src/api/schema.d.ts` are regenerated.

  The change is additive for clients. The browser ignores the field until `UI-003`.

## 8. `SetConnectionType`

### 8.1 Command

| `type` | `args` | Effect |
|---|---|---|
| `SetConnectionType` | `{junction_class, connection_type}`, both required | Sets `FrameSystem.connection_defaults[junction_class]` and regenerates connections. Members are unchanged. Every connection of the class gets the new type and keeps its ID |

- **Per class, never per connection** (D054, as D040 for sections).
- **Argument link:** `args.connection_type` maps to `connection_defaults[<class>]` (D036 quotes the hyphenated key, for example `connection_defaults["joist-beam"]`), so candidate errors carry it in `related_paths` (interfaces.md §7.1).
- **A class with no connections** (for example `brace` with both brace planes off) is accepted. Only the default changes, and the `connections` lists are empty. This matches `SetMemberSection` for a role with no members (MODEL-005 §5.2).

### 8.2 Errors

| Situation | Top-level code | Detail |
|---|---|---|
| Missing, unknown, or wrong-type argument | `VALIDATION_FAILED` (stage 1) | `MISSING_FIELD`, `UNKNOWN_FIELD`, `WRONG_TYPE` at `args.<name>` |
| `junction_class` not one of the seven classes, or `connection_type` not one of the five types | `VALIDATION_FAILED` (stage 1) | `INVALID_ENUM` at `args.junction_class` or `args.connection_type` |
| A known type not allowed for the class, for example `{"junction_class": "joist-beam", "connection_type": "BRIDLE"}` | `UNSUPPORTED_CONFIGURATION` (stage 4) | `UNSUPPORTED_VALUE` at `entities[<frame>].connection_defaults["joist-beam"]`, `value` `"BRIDLE"`, `related_paths` `["args.connection_type"]` |
| The class's current type | — | A no-op (D045): `is_noop`, no revision, no confirmation |

- **No new detail codes.** The disallowed pair is reported by the existing stage 4 catalog check on the candidate, like any candidate error (interfaces.md §7.1). It is not a separate argument check.
- **No "class not generated" check,** unlike `SetMemberSection`'s role check. `vs02-frame-1` generates all seven classes, and stage 2 already requires a default for each.

### 8.3 Classification

**Approved (§11 item 10, [D059](../../product/decisions/D059-vs02-junction-rules-connection-type-command.md)): consequential.** The row is added to `vs02-change-classes-1`, as D057 and dependencies.md §4.1 anticipated, so the table version does not change.

- **Why:**
  - it changes every connection of a class at once, as `SetMemberSection` changes every member of a role;
  - switching a class between traditional and engineered joinery changes the per-piece estimate lines, and dependencies.md §4 names "potentially significant budget implications" as consequential;
  - the policy is conservative by default.
- **Alternative: routine.** No member or location moves, and undo restores the type in one step, so applying it directly with undo would be quicker in the browser. This would make it the second routine command, after `AddSection`.

## 9. Rule interface, fixture, and oracle

- **One internal pass:** `vs02_frame_1.py` builds members and connections together, so a receiving member's key is built from the same variables as the member's own key. No key is parsed. `generate` and `generate_connections` return the two parts, with signatures unchanged (TIMBER-002 §13).
- **Conformance needs no new code:** `connection_conformance` in `timber/inventory.py` already compares keys, classes, members, types, and locations (MODEL-005 §14).
- **Fixture:** `uv run python -m homedesign.timber.fixture` adds the 312 connections to Reference House 001 v2 and to the packaged template. Their IDs are fixed UUIDv5 values from their keys, under the fixture namespace, with names distinct from members'. `--check` keeps guarding drift in `scripts/check.sh` and CI. A created project still equals the fixture exactly, apart from IDs and revision metadata.
- **Oracle:** `tests/vectors/jcs/generate.mjs` implements §4–5 independently. The `inventories` vector gains the reference house's connections, named by member keys (`generation_key`, `junction_class`, `connection_type`, `member_keys`, `location_m`). The Python test compares them under TIMBER-002 §8's rule: bit-identical, except the `z` of `rafter-peak` and `purlin-rafter` locations, within 1e-12 m. `vectors.json` grows by an estimated 60–100 KB.

## 10. Changes to existing tests and documents

**Tests** (test-only changes need no approval):

- **Counts and identity:** expected counts and diffs that assume no connections, for example MODEL-003's width-change test and the grid insertion and removal tests, gain their connection counts, recomputed and asserted with their reasons.
- **Conformance codes:** the catalog-coverage note in `test_mutations.py`, which says three conformance codes are reachable only through a direct test, now points to fixture mutations.
- **Integration suite** (`TEST-001`):
  - `invariants.py` checks after every step that the connection count matches §6 and that every connection's location lies on both members' axes;
  - the golden record is regenerated as a reviewed diff: only IDs, fingerprints, and the new `connections` lists change;
  - the property-based sequences draw `SetConnectionType`.
- **UI fixture and Playwright:** regenerated. No browser behavior changes.

**Documents** (the approved contracts were recorded on 2026-11-20, marked "not yet implemented"; implementation removes the markers):

- generation-rules.md: a "Connections" section with §4–6.
- building-model.md:
  - §3.3: the key format;
  - §6.1: drop the note that three codes cannot occur.
- interfaces.md:
  - §2: the `SetConnectionType` row;
  - §3: the `connections` diff.
- dependencies.md §4.1: the classification row.
- The reference house README: 312 connections, and the unclassed junctions (§4.4).
- D054's "What this does not decide": point to the new decision.

## 11. Proposals for approval

**Routine** (they follow from D041, D042, D046, D054, D058, and MODEL-005). **All six approved together (2026-11-20).**

1. ~~**Rules per class** (§4.2): the entering and receiving members of each class, `location_m` copied from the entering member's endpoint, `connection_type` from `connection_defaults`, and no connections for absent members.~~ **Approved** (2026-11-20). The table's receiving members for ends that meet several candidates, and the count it implies, still depend on items 7–9. It goes into generation-rules.md once they are settled.
2. ~~**Key format** (§5.1): `connection/{junction_class}/{receiving key}/{entering key}`, code-unit order, and the pinned no-`/frame/` property.~~ **Approved** (2026-11-20); recorded in building-model.md §3.3 and generation-rules.md as a VS-02 amendment, not yet implemented.
3. ~~**IDs and identity** (§5.2–5.3): IDs minted from `"generation/" + key`, regenerated with the members, and the invariant that surviving connections keep their `member_ids`.~~ **Approved** (2026-11-20); recorded in building-model.md §3.3 and generation-rules.md, not yet implemented.
4. ~~**Preview diff** (§7.2): `connections: {added, removed, updated}`, shaped like `members`, with connection records excluded from `changes`.~~ **Approved** (2026-11-20); recorded in interfaces.md §3 as a VS-02 amendment, not yet implemented.
5. ~~**`SetConnectionType` arguments and errors** (§8.1–8.2): no new detail codes, and classes without connections accepted.~~ **Approved** (2026-11-20); recorded in interfaces.md §2 as a VS-02 amendment, not yet implemented. Its classification is item 10.
6. ~~**Fixture, oracle, and tests** (§9–10): the 312-connection fixture by script, the ECMAScript connections vector with the `tan` exception, and the test updates.~~ **Approved** (2026-11-20). The fixture's count follows items 7–9.

**Your judgment** (one at a time, in this order):

7. ~~**One connection per entering member end** (§4.1). This gives 312 connections, and 12 `post-sill` connections rather than 34. *Alternative:* one per meeting pair of members (more connections, no receiving choice, an inflated per-piece estimate).~~ **Approved: option A** (2026-11-20), to be recorded in D059 with items 8–10. The alternative would have given 388 connections for the reference house: 102 `post-beam`, 34 `post-sill`, and 28 `rafter-foot`, with the other classes unchanged.
8. ~~**Receiving members where several meet** (§4.3): the post below for beams and braces, the bent's Y sill for post feet, the bent's tie beam for rafter feet, and the south rafter at the peak.~~ **Approved** (2026-11-20): all four as proposed, to be recorded in D059. They fix `member_ids` and keys only; the count (312) and every `location_m` are unaffected.
9. ~~**Junctions with no class get no record** (§4.4): Level 1 post-to-post splices and sill-to-sill meetings. A `post-post` class would be a new catalog version and a decision of its own.~~ **Approved: option A** (2026-11-20), to be recorded in D059. The omission is documented, and `ART-002` adds a schedule and estimate assumption line for it. A `post-post` class can follow later as its own decision.
10. ~~**`SetConnectionType` is consequential** (§8.3). *Alternative:* routine, applied with undo.~~ **Approved: consequential** (2026-11-20); recorded in D059 and as an amendment note in dependencies.md §4.1; the table row is added with the implementation.

Items 7–9 settle D054's open point ("exact junction rules … and so the connection counts"), and item 10 its open classification. They are recorded together as **[D059](../../product/decisions/D059-vs02-junction-rules-connection-type-command.md)**. The approved contracts are in generation-rules.md, building-model.md §3.3, interfaces.md §2–3, dependencies.md §4.1, and the reference house README, each marked "not yet implemented"; implementation removes those markers and the building-model.md §6.1 note (§10).

## 12. Acceptance criteria and automated tests

1. **Fixture connections (AC2-03, AC2-06):** the rule's connections for the fixture are exactly the fixture's 312 records: keys, classes, member IDs, types, and bit-identical locations, with the §6 counts per class. The fixture validates and `--check` passes. A created project equals the fixture exactly, apart from IDs and revision metadata.
2. **Junction rules (§4.2):** for every connection, the entering member's endpoint equals `location_m`, the location lies on the receiving member's axis within its extent (1e-9 m), and the two members' roles match the class.
3. **Counts (§6):** across grids of 2–7 stations per axis and frame parameters at their bounds, the count per class matches the formula, keys are unique across members and connections, and the largest supported case gives 2,110 connections. Its `propose` time is reported.
4. **Keys (§5.1):** every key starts with `connection/`, no member key contains `/frame/`, and every connection key splits back into its two member keys.
5. **Identity (§5.3):** each edit in the table gives the stated adds, removals, and updates. Surviving connections keep their IDs and `member_ids`. A brace toggle followed by undo restores the original connection IDs.
6. **Preview diff (§7.2):** `connections` lists exactly the added, removed, and updated records, in the stated orders. Added IDs equal those the commit creates. `changes` contains no `Connection` records. A no-op has empty lists. The API response validates against OpenAPI.
7. **`SetConnectionType` (§8):** each class switches to its alternative and back. Only that class's connections are updated, and no member changes. Each §8.2 error has its exact code, path, and `related_paths`. The current type is a no-op. A class with no connections is accepted. Committing without a preview is `PREVIEW_REQUIRED` (item 10).
8. **Conformance (D046, MODEL-005 §6.5):** minimal fixture mutations produce all four connection conformance codes, with exact paths: a removed record, an extra key, a moved `location_m`, and a wrong `junction_class`, `member_ids`, or `connection_type`.
9. **Oracle (§9):** the ECMAScript connections match under the `tan` exception.
10. **Zero cases:** braces off, zero purlins, and a bay without joists generate no connections of those classes, and the result validates.
11. **Determinism and robustness:** connections are identical across runs and entity orderings. Never-raises property tests send random `SetConnectionType` arguments and random frame parameters, and every accepted candidate re-validates.
12. **Still preliminary (AC2-07):** `Connection` records and the preview carry no capacity, size, or fastener field, and every preview still carries `PRELIMINARY_UNVERIFIED`.

## 13. Implementation guidance (not prescriptive)

- **Order:**
  1. the rule's connections, with the §12 test 2 checks;
  2. the fixture and oracle;
  3. regeneration and the preview diff;
  4. `SetConnectionType`;
  5. regenerated records last, so their diffs reflect the final code.
- **Cost:** conformance and regeneration each call the rule. If profiling the largest case shows it matters, compute the members and connections once per snapshot.
- **Diff:** `_diff` currently puts every non-member record into `changes`. Split connections out the same way members are.

## 14. Definition of done

- All §12 tests pass, with the updated VS-01 and VS-02 suites, Vitest, and Playwright. The vector and fixture checks pass, and `scripts/check.sh` and CI pass.
- D059 is recorded. The documents in §10 and the roadmap are updated.
- Changed files, tests, limitations, and next steps are summarized (AGENTS.md).
