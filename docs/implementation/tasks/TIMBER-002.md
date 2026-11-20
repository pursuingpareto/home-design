# TIMBER-002 — Generation rule `vs02-frame-1` and Reference House 001 v2

**Status:** Implemented (2026-11-19), together with `MODEL-005`. All five §11 proposals were approved (item 1 as [D058](../../product/decisions/D058-datum-reference-axes.md)). See §13 for implementation notes.  
**Owner module:** `timber`  
**Slice:** VS-02  
**Depends on:** [`MODEL-005`](MODEL-005.md) (agreed). The two are implemented on one branch and **merged together** (MODEL-005 §9).  
**Unblocks:** `CONN-001` (junctions need the full member set), `ART-002`, `DEP-001`, `UI-003`

## 1. Objective and user-visible behavior

Implement `vs02-frame-1`, the only generation rule after MODEL-005. It is a pure, deterministic function from a version 2 snapshot's parameters to the member inventory:

- posts and beams, unchanged from `vs01-post-beam-1`;
- the five new roles of [D052](../../product/decisions/D052-vs02-frame-members.md): sills, floor joists, principal rafters, purlins, and knee braces.

It also delivers the Reference House 001 v2 fixture with exactly the [D053](../../product/decisions/D053-reference-house-001-v2-design-intent.md) inventory of **193 members**, and an independent ECMAScript oracle, as TIMBER-001 did.

**User-visible after the merge:** new projects show the complete frame in 3D and in the schedule (MODEL-005 §9 keeps the 2D plan to posts and beams until `ART-002`). Frame, grid, footprint, story, and roof edits regenerate the new members, with IDs kept wherever a member's position survives.

## 2. Inputs and governing documents

- Decisions:
  - [D052](../../product/decisions/D052-vs02-frame-members.md) (roles and placement) and [D053](../../product/decisions/D053-reference-house-001-v2-design-intent.md) (values, counts, and the open bearing question this task settles);
  - [D025](../../product/decisions/D025-reference-house-001-vs01-fixture.md) (the house), [D026](../../product/decisions/D026-canonical-units-identity-persistence.md) (units, epsilon), [D039](../../product/decisions/D039-frame-member-defaults.md)/[D042](../../product/decisions/D042-stable-grid-line-ids.md) (defaults, line-based keys), [D046](../../product/decisions/D046-conformance-validation-stage.md) (conformance), [D048](../../product/decisions/D048-roof-plane-through-wall-line.md) (roof planes), [D055](../../product/decisions/D055-pre-release-schema-replacement.md) (replace the fixture).
- [MODEL-005](MODEL-005.md) §4–6 (records, parameters, rule interface) and §9 (merge scope); [TIMBER-001](TIMBER-001.md) (the pattern this task extends).
- [generation-rules.md](../../reference-projects/vermont-timber-house/generation-rules.md) (numeric evaluation) and [geometry.md](../../architecture/geometry.md) ("Numeric evaluation": the `tan` exception).

## 3. Scope

**In scope**

- `timber/rules/vs02_frame_1.py`: `generate`, the declared roles and junction classes, and `generate_connections` returning nothing until `CONN-001` (MODEL-005 §6.5).
- Member conformance moved into a shared, rule-independent comparison, so a rule supplies only its generator.
- A rewritten generation-rules.md for `vs02-frame-1`, replacing the VS-01 text (D055).
- The Reference House 001 v2 fixture and packaged template (§7), with a script that regenerates them and a drift check.
- The ECMAScript oracle and the inventory vector (§8).
- Updates to the existing tests that depend on the VS-01 inventory (§9).

**Non-goals**

- Connections, junction rules, and connection keys → `CONN-001`.
- Payload changes beyond MODEL-005 §9, and box orientation for the new roles in `mesh3d` → `ART-002`. D053's section orientations ("depth vertical", "depth perpendicular to the roof plane") are recorded there.
- Rafter tails over the eave overhang, ridge beams, collar ties, girts, studs, ceiling joists, floor openings, and any structural check (D052).

## 4. Reference axes and bearing (settles D053's open point)

**Proposal: every reference axis lies on a datum.** A datum is a grid station, a level or eave plane, or a D048 roof plane. Axes never move for section sizes.

- **Joists frame into beams:** joist axes lie at the Level 1 plane, level with the beam axes, and meet the beams' vertical faces. This matches D054's `joist-beam` class ("each joist end into a beam") and its default, `HOUSED_DOVETAIL`.
- **Rafters bear on the plate line:** principal rafters lie in the roof plane, from the wall line at `z_eave` to the ridge. They do not extend over the overhang.
- **Purlins lie in the roof plane,** crossing the rafter axes.
- **Braces lie in each beam's vertical plane,** from the post axis to the beam axis.

**Why:**
- **Simple junctions:** every junction is an intersection of axes, so connection locations (D054: "where the entering member's reference axis meets the receiving member's") are exact points.
- **Sections stay independent:** changing a section never moves another member. `SetMemberSection` keeps changing only sections, as in VS-01, and D056's selector for `plan2d` (axes, not sections) stays meaningful.
- **Lengths stay honest:** lengths remain reference-axis lengths, already labeled "not cut lengths".

**Alternative:** joists bearing on top of beams, raised by half of each depth. It is closer to some framing practice, but it couples geometry to sections, so a section change would move members and their connections.

## 5. Members

### 5.1 Notation and numeric evaluation

Unchanged from `vs01-post-beam-1`, with every value an IEEE-754 double evaluated **exactly as written, left to right**, with no rounding or snapping:

```text
x(line) = origin_x + width_m * line.fraction       y(line) = origin_y + depth_m * line.fraction
z0 = level[0].elevation_m    z1 = level[1].elevation_m    z_eave = level[1].elevation_m + level[1].story_height_m
y_s = origin_y               y_n = origin_y + depth_m      y_ridge = origin_y + depth_m / 2
t = tan(pitch_rad)           z_ridge = z_eave + (depth_m / 2) * t          (D048)
s = joist_spacing_m          n = purlins_per_slope         L = knee_brace_leg_m     ε = 1e-6
```

`t` is computed once per snapshot. Lines are taken in ascending-fraction order. Adjacent pairs are written `xa-xb` or `ya-yb`.

### 5.2 Geometry and keys

Axes run from `start` to `end` as written. The posts and beams rows are unchanged.

| Role | One member per | `generation_key` | Axis |
|---|---|---|---|
| `POST` | station, story | `frame/{x}/{y}/level-0/post`, `…/level-1/post` | unchanged |
| `BEAM` | bay, line, plane (L1, eave) | `frame/axis-x/{y}/{xa}-{xb}/{plane}/beam`, `frame/axis-y/{x}/{ya}-{yb}/{plane}/beam` | unchanged |
| `SILL` | bay, line | `frame/axis-x/{y}/{xa}-{xb}/plane-L0/sill`, `frame/axis-y/{x}/{ya}-{yb}/plane-L0/sill` | as the beams, at `z0` |
| `FLOOR_JOIST` | X bay, ordinal `k`, Y bay | `frame/axis-y/{xa}-{xb}/j{k}/{ya}-{yb}/plane-L1/joist` | `(xk, y(ya), z1) → (xk, y(yb), z1)`, with `xk = x(xa) + k * s` for each `k = 1, 2, …` while `xk < x(xb) − ε` |
| `PRINCIPAL_RAFTER` | X line, slope | `frame/roof/{x}/south/principal-rafter`, `frame/roof/{x}/north/principal-rafter` | south `(x, y_s, z_eave) → (x, y_ridge, z_ridge)`; north `(x, y_n, z_eave) → (x, y_ridge, z_ridge)` |
| `PURLIN` | X bay, slope, ordinal `i` | `frame/roof/{xa}-{xb}/{slope}/p{i}/purlin` | `(x(xa), yi, zi) → (x(xb), yi, zi)`, with `f = i / (n + 1)` for `i = 1 … n` (from the eave), `yi = y_e + (y_ridge − y_e) * f`, `zi = z_eave + (z_ridge − z_eave) * f`, and `y_e` = `y_s` (south) or `y_n` (north) |
| `KNEE_BRACE` | beam end, enabled plane | `{beam key without "/beam"}/brace/{end line}` | from the post to the beam, at the plane height `z`: for an X beam, end `xa` is `(x(xa), y, z − L) → (x(xa) + L, y, z)` and end `xb` is `(x(xb), y, z − L) → (x(xb) − L, y, z)`; Y beams likewise along Y |

- **Joists** sit between the X-direction beams of each Y bay, never on a beam line. The `ε` test excludes a position that lands on the next line, as 5 × 24" does on a 12' bay. A bay at least as short as the spacing has no joists (MODEL-005 §5.2).
- **Brace planes:** `knee_braces_level_1` controls `plane-L1` braces (down along Level 0 posts) and `knee_braces_eave` controls `plane-eave` braces (down along Level 1 posts). MODEL-005's brace-fit rule guarantees that the two braces under one beam do not overlap, and the leg bound guarantees that they end on their posts.
- **Ordinals** start at 1 and are not zero-padded, like line numbers (D042). Ordering is by key in code-unit order, as in VS-01.
- **Section and material:** from `member_defaults[role]` (D039).

### 5.3 Counts

With `nx`, `ny` stations, and `B = ny·(nx − 1) + nx·(ny − 1)` bay-lines per plane:

| Role | Count | Reference House 001 v2 |
|---|---|---|
| Posts | `2·nx·ny` | 24 |
| Beams | `2·B` | 34 |
| Sills | `B` | 17 |
| Floor joists | `(ny − 1) · Σ joists per X bay` | 30 (3 bays × 5, × 2 spans) |
| Principal rafters | `2·nx` | 8 |
| Purlins | `2·n·(nx − 1)` | 12 |
| Knee braces | `2·B` × enabled planes | 68 |
| **Total** | | **193** |

Reference checks: `z_ridge` = 8.5344 m (D048), the rafter axis is 15'-0" (D053: purlins every 5'), and joists fall at 2', 4', 6', 8', and 10' within each 12' bay.

**Largest supported inventory:** 7 × 7 stations, 80' × 80', 12" joists, 4 purlins, and both brace planes give **1,216 members** (468 of them joists). Derivation stays synchronous (D051); `TEST-002` times this case.

### 5.4 Identity under edits (D041, D042)

| Edit | Effect on keys and IDs |
|---|---|
| Footprint, story heights, roof pitch | Every key survives; members move. Joists may appear or disappear at the end of a bay whose length changes |
| Joist spacing | `j1…jm` survive and move; extra ordinals are added or retired at the far end of each bay |
| Purlins per slope | `p1…pm` survive and move (the fractions change); others are added or retired |
| A brace plane off, then on | Its braces are retired, then re-added **with new IDs** (D041). `UndoToRevision` restores the original IDs (D044) |
| Insert or remove an X line | Joists, purlins, sills, and braces of the split or merged bays are retired and recreated; members on surviving bays keep IDs |
| `SetMemberSection` | Sections change only; no key or coordinate changes (§4) |

## 6. Rule interface

- **Registration:** `Rule(version="vs02-frame-1", generated_roles=<all seven>, generated_junction_classes=<all seven>, generate, generate_connections)`, as MODEL-005 §6.5 defines.
- **Shared conformance:** member conformance moves from the rule module into one comparison in `timber/inventory.py`, used for members now and for connections by `CONN-001`. Its codes and paths are unchanged from D046.
- **Connections:** `generate_connections` returns an empty tuple until `CONN-001`.
- **Retirement:** `vs01_post_beam_1.py` and its registration are deleted (MODEL-005 §8).

## 7. Reference House 001 v2 fixture

- **Content:** the D025 records, plus the four new sections (4×8, 8×10, 6×8, and 4×6) and the version 2 `FrameSystem` (D053 parameters, seven `member_defaults` entries, and D054 `connection_defaults`), with 193 generated members.
- **Stored members are exact generator output.** The VS-01 fixture's hand-entered decimals (`3.6576` where the generator gives `3.6575999999999995`; TIMBER-001 §4.2) are not carried forward. A created project then equals the fixture **exactly**, apart from IDs and revision metadata, and the "within 1e-6 m" caveats in interfaces.md §2 and MODEL-003 §6 go away.
- **A script produces it:** `uv run python -m homedesign.timber.fixture [--check]` builds the fixture and the packaged template from the D025 and D053 inputs. Non-generated record IDs keep their current fixed values, new records get fixed IDs chosen once, and member IDs are deterministic from their keys. `--check` runs in `scripts/check.sh` and CI, like the golden record.
- **Docs:** the reference house README's inventory table and generation-rules.md are rewritten for version 2.

## 8. Cross-language oracle

- **Independent implementation:** `tests/vectors/jcs/generate.mjs` gains an ECMAScript implementation of §5. The `inventories` vector becomes the v2 fixture's inventory, with its canonical bytes and `sha256:` fingerprint.
- **The `tan` exception** (geometry.md): every coordinate must be bit-identical, except the `z` coordinates of principal rafters and purlins, which depend on `tan(pitch_rad)` and must agree within **1e-12 m**. The Python test compares the vector field by field under that rule; other fields are compared exactly.
- **Platform note:** the golden record and the fixture store one platform's `tan` result. Linux CI and macOS already agree on the reference pitch, because the existing ridge height depends on it. If a platform ever differs, the fixture check reports a coordinate difference under 1e-12 m, not a silent change.

## 9. Changes to existing tests

- **Moved to the v2 house** (D055: VS-01 criteria keep their meaning):
  - expected counts: 58 → 193, 24 posts and 34 beams unchanged;
  - MODEL-003's width-change test (48 members updated → the v2 count, recomputed and asserted with its reason);
  - grid-line insertion and removal (now also joists, sills, purlins, and braces);
  - TEST-001's golden record and sequences, and the UI fixture, regenerated as reviewed diffs.
- **Removed:** the 38 bit-level fixture differences (TIMBER-001 test 1), since the fixture is now exact.
- **`conftest.regenerate`** uses the v2 rule.

## 10. Acceptance criteria and automated tests

1. **Fixture inventory (AC2-02, AC2-06):** `generate(fixture)` yields exactly the fixture's 193 members (keys, roles, sections, materials, and bit-identical endpoints), with the §5.3 counts per role.
2. **The fixture conforms,** and the fixture check (`--check`) passes. A created project equals the fixture exactly, apart from IDs and revision metadata.
3. **Reference values:** `z_ridge` = 8.5344 m within 1e-12 m, the rafter axis is 15'-0" within 1e-9 m, the purlins sit at 5' and 10' along the slope, the joists are at the listed positions, and the brace legs are 3'-0" with axes at 45°.
4. **Oracle:** the ECMAScript inventory matches under the §8 rule.
5. **Count formulas:** across grids of 2–7 stations per axis and parameters at their bounds, counts match §5.3, keys are unique, and no joist lies within ε of a line.
6. **Identity (§5.4):** spacing and purlin changes keep the surviving ordinals' IDs, a line removal retires exactly the affected bays' members, and a brace toggle followed by undo restores the original IDs.
7. **Datum axes (§4):** a section change moves no coordinate, every joist end lies on a beam axis, every purlin crosses each of its rafters' axes at the purlin's end points, and every brace end lies on its post or beam axis, all within 1e-9 m.
8. **Zero cases:** zero purlins, both brace planes off, and a bay too short for joists generate no members of those kinds, and the result validates.
9. **Determinism:** identical output across runs and entity orderings; canonical bytes identical.
10. **Conformance:** the D046 mutations from TIMBER-001 test 8, applied to one member of each new role, give the same codes and paths.
11. **Robustness:** never-raises property tests cover the v2 rule with random parameters within bounds.

## 11. Proposals for approval

1. ~~**Datum reference axes** (§4): every axis lies on a station, plane, or roof plane; joists frame into beams; rafters bear on the plate line, without tails; sections never move axes.~~ **Approved: [D058](../../product/decisions/D058-datum-reference-axes.md)** (2026-11-19); noted in generation-rules.md and D053.
2. ~~**Geometry** (§5.1–5.3): the formulas, the joist ε rule, purlins at `i / (n + 1)` of the rafter, braces from post to beam at 45°, and axis directions.~~ **Approved** (2026-11-19); recorded in generation-rules.md.
3. ~~**Keys and identity** (§5.2, §5.4): the seven key formats, unpadded ordinals, and the behavior under each edit.~~ **Approved** (2026-11-19); recorded in generation-rules.md.
4. ~~**An exact, scripted fixture** (§7): the v2 fixture stores generator output, built and drift-checked by a script, ending the VS-01 hand-entered decimals.~~ **Approved** (2026-11-19); recorded in generation-rules.md and the reference house README.
5. ~~**The oracle with the `tan` exception** (§8): the 1e-12 m allowance for rafter and purlin heights only.~~ **Approved** (2026-11-19); recorded in geometry.md and generation-rules.md.

Approved items update generation-rules.md and the reference house README. Item 1 settles D053's open point, so it is recorded as a decision.

## 12. Definition of done

- All §10 tests pass on the merged MODEL-005 + TIMBER-002 branch, together with the regenerated VS-01 suite, Vitest, and Playwright. The vectors and fixture checks pass, and CI passes.
- generation-rules.md, the reference house README, interfaces.md §2, MODEL-003 §6 (exact equality), the decision register, and the status docs are updated.
- Changed files, tests, limitations, and next steps are summarized (AGENTS.md).

## 13. Implementation notes (2026-11-19)

Implemented on one branch with [MODEL-005](MODEL-005.md); its notes cover the schema, validation, commands, and the merge scope.

**Delivered:**
- `backend/src/homedesign/timber/`:
  - `rules/vs02_frame_1.py`: the §5 generator, all seven roles and junction classes declared, `generate_connections` returning nothing;
  - `rules/__init__.py`: `Rule` gains `generated_junction_classes` and `generate_connections`, and its `conformance` uses the shared comparison;
  - `inventory.py`: `GeneratedConnection`, `member_conformance`, and `connection_conformance` (codes and paths unchanged from D046);
  - `fixture.py`: builds the fixture and the packaged template; `--check` runs in `scripts/check.sh` and CI;
  - `rules/vs01_post_beam_1.py` deleted.
- `docs/reference-projects/vermont-timber-house/fixture.snapshot.json` and the packaged template: Reference House 001 v2, 206 records (193 members), exact generator output.
- `tests/vectors/jcs/generate.mjs`: an independent ECMAScript `vs02-frame-1`. The `inventories` vector now carries the full 193-member inventory (50,271 canonical bytes), so `vectors.json` grows from about 41 KB to 203 KB.
- generation-rules.md rewritten for `vs02-frame-1`; the reference house README updated.

**Tests:** `test_timber.py` was rewritten for §10 (70 tests):
- the fixture is bit-identical to the rule, with the D053 counts, and the fixture check passes;
- reference values: ridge at 8.5344 m, 15'-0" rafters, purlins at 5' and 10', joists at 2'–10', 3'-0" braces at 45°;
- the ECMAScript inventory matches (it is in fact bit-identical, including the `tan`-derived heights, on this platform);
- counts for all 36 grid sizes, for parameters at each bound, and for the largest supported inventory (1,216 members, 468 joists);
- identity under line insertion and removal, spacing and purlin changes, and section changes;
- datum axes: every joist end on a Level 1 beam, every purlin end on a rafter, every brace end on its post and beam, every rafter foot on an eave beam;
- zero purlins, braces off, and a bay too short for joists;
- the D046 mutations for one member of each role;
- a property test of random parameters within bounds.

The VS-01 tests now run against the v2 house (D055): for example, a 40' width updates 155 members and adds six joists, and removing `x2` retires 92 members and adds 47. The golden scenario was regenerated and reviewed: every step keeps its HTTP status and code, and only IDs and fingerprints change. Step 6, the roof edit, now goes through a preview (D057).

**Choices made during implementation:**

- **Fixture IDs:** the D025 records keep their IDs. The four new sections and every member get UUIDv5 IDs under a fixed fixture namespace, so the VS-01 member IDs are not carried over. Nothing references them across versions (D055).
- **The fixture is written by script only:** hand edits fail the drift check in CI.

**Limitations:**

- No connections yet (`CONN-001`).
- New roles render in one neutral color, and the plan omits them (`UI-003`, `ART-002`).
- `TEST-002` adds `SetFrameParameters` and the new roles to the golden scenario; the property-based sequences already draw both.

