# Framing generation rules — `vs02-frame-1`

**Status:** Confirmed for Reference House 001 v2 / VS-02 ([D052](../../product/decisions/D052-vs02-frame-members.md), [D053](../../product/decisions/D053-reference-house-001-v2-design-intent.md), [D058](../../product/decisions/D058-datum-reference-axes.md); [TIMBER-002](../../implementation/tasks/TIMBER-002.md)). It replaces `vs01-post-beam-1`, which is retired ([D055](../../product/decisions/D055-pre-release-schema-replacement.md)).  
**Not** a structural design procedure. Generated members are geometric inventory only (AC-08).

Applies when `TimberGrid.generation_rule_version` is `vs02-frame-1` and `FrameSystem.generation_mode` is `DETERMINISTIC_RULE`. It is the only registered rule.

## Inputs

- Rectangular `Footprint` origin, width (X), and depth (Y). The rule requires `origin_m = [0, 0]` and `rotation_rad = 0` ([D031](../../product/decisions/D031-vs01-unsupported-configurations.md)).
- Two `Level` records, indices 0 and 1, with elevations strictly increasing.
- `GableRoof`: the pitch places principal rafters and purlins. The ridge runs along X and is centered (D031). The overhang moves no member.
- Regular `TimberGrid` lines `x_lines` / `y_lines` (`{id, fraction}`, fractions strictly ascending from 0 to 1 inclusive; [D042](../../product/decisions/D042-stable-grid-line-ids.md)).
- `FrameSystem.member_defaults`: one entry for each of the seven roles ([D039](../../product/decisions/D039-frame-member-defaults.md)).
- `FrameSystem.parameters`: `joist_spacing_m`, `purlins_per_slope`, `knee_brace_leg_m`, `knee_braces_level_1`, and `knee_braces_eave`. Bounds are in [building-model.md §3.3](../../architecture/building-model.md#33-version-2-records).

## Numeric evaluation

Approved from [TIMBER-001](../../implementation/tasks/TIMBER-001.md) §10, item 2, and kept for version 2.

- **Exact formulas:** generated coordinates are IEEE-754 doubles, evaluated exactly as written below and left to right. There is no fused multiply-add, no reordering, and **no rounding or snapping**.
- **The one exception is `tan(pitch_rad)`.** It is computed once per snapshot. The `z` coordinates of principal rafters and purlins depend on it, so they must agree across implementations within **1e-12 m** ([geometry.md](../../architecture/geometry.md), "Numeric evaluation"). Every other coordinate is bit-identical in any IEEE-754 language.
- **Generator output is stored:** every snapshot produced by a command, and the fixture itself, stores generator output exactly ([TIMBER-002](../../implementation/tasks/TIMBER-002.md) §7). A command that changes no parameter is then a true no-op ([D045](../../product/decisions/D045-no-op-commits.md)). The VS-01 fixture's hand-entered decimals (`3.6576` where the generator gives `3.6575999999999995`) are not carried forward.
- **Display:** conversion to feet and inches, and any display rounding, happens in the UI and is never written back.

```text
x(line) = origin_x + width_m * line.fraction       y(line) = origin_y + depth_m * line.fraction
z0 = level[0].elevation_m    z1 = level[1].elevation_m    z_eave = level[1].elevation_m + level[1].story_height_m
y_s = origin_y               y_n = origin_y + depth_m      y_ridge = origin_y + depth_m / 2
t = tan(pitch_rad)           z_ridge = z_eave + (depth_m / 2) * t          (D048)
s = joist_spacing_m          n = purlins_per_slope         L = knee_brace_leg_m
```

## Reference axes (D058)

Every reference axis lies on a datum: a grid station, the Level 0, Level 1, or eave plane, or a D048 roof plane. **Section sizes never move an axis.**

- **Floor joists frame into beams,** level with them on the Level 1 plane.
- **Principal rafters bear on the plate line:** they run from the wall line at `z_eave` to the ridge, with no tails over the overhang.
- **Purlins** lie in the roof plane and cross the rafter axes.
- **Knee braces** lie in their beam's vertical plane, from the post axis to the beam axis.

Lengths are reference-axis lengths, not fabrication cut lengths.

## Members

Lines are taken in ascending-fraction order. Adjacent pairs are written `xa-xb` or `ya-yb`. Axes run from start to end as written. Section and material come from `member_defaults[role]`.

| Role | One member per | `generation_key` | Axis |
|---|---|---|---|
| `POST` | station, story | `frame/{x}/{y}/level-0/post`, `frame/{x}/{y}/level-1/post` | `(x, y, z0) → (x, y, z1)`; `(x, y, z1) → (x, y, z_eave)` |
| `BEAM` | bay-line, plane | `frame/axis-x/{y}/{xa}-{xb}/{plane}/beam`, `frame/axis-y/{x}/{ya}-{yb}/{plane}/beam`, with `{plane}` = `plane-L1` (at `z1`) or `plane-eave` (at `z_eave`) | `(x(xa), y, z) → (x(xb), y, z)`; Y beams likewise |
| `SILL` | bay-line | `frame/axis-x/{y}/{xa}-{xb}/plane-L0/sill`, `frame/axis-y/{x}/{ya}-{yb}/plane-L0/sill` | As the beams, at `z0` |
| `FLOOR_JOIST` | X bay, ordinal `k`, Y bay | `frame/axis-y/{xa}-{xb}/j{k}/{ya}-{yb}/plane-L1/joist` | `(xk, y(ya), z1) → (xk, y(yb), z1)`, with `xk = x(xa) + k * s` for `k = 1, 2, …` while `xk < x(xb) − 1e-6` |
| `PRINCIPAL_RAFTER` | X line, slope | `frame/roof/{x}/south/principal-rafter`, `frame/roof/{x}/north/principal-rafter` | South `(x, y_s, z_eave) → (x, y_ridge, z_ridge)`; north `(x, y_n, z_eave) → (x, y_ridge, z_ridge)` |
| `PURLIN` | X bay, slope, ordinal `i` | `frame/roof/{xa}-{xb}/{south\|north}/p{i}/purlin` | `(x(xa), yi, zi) → (x(xb), yi, zi)`, with `f = i / (n + 1)` for `i = 1 … n` (`p1` nearest the eave), `yi = y_e + (y_ridge − y_e) * f`, `zi = z_eave + (z_ridge − z_eave) * f`, and `y_e` = `y_s` (south) or `y_n` (north) |
| `KNEE_BRACE` | beam end, enabled plane | The beam's key with `/beam` replaced by `/brace/{end line}` | From the post to the beam, at the plane height `z`. For an X beam, end `xa` is `(x(xa), y, z − L) → (x(xa) + L, y, z)` and end `xb` is `(x(xb), y, z − L) → (x(xb) − L, y, z)`. Y beams likewise along Y |

- **Joists** never lie on a beam line: the `1e-6` test excludes a position that lands on the next line, as 6 × 24" does on a 12' bay. A bay no longer than the spacing has no joists.
- **Brace planes:** `knee_braces_level_1` controls the `plane-L1` braces (down along Level 0 posts) and `knee_braces_eave` the `plane-eave` braces (down along Level 1 posts). Validation guarantees that two braces fit under every beam and that braces end on their posts ([building-model.md §3.3](../../architecture/building-model.md#33-version-2-records)).
- **Ordinals** start at 1 and are not zero-padded, like line numbers (D042).
- **Counts:** with `B = ny·(nx − 1) + nx·(ny − 1)`: posts `2·nx·ny`, beams `2·B`, sills `B`, joists `(ny − 1)·Σ joists per X bay`, rafters `2·nx`, purlins `2·n·(nx − 1)`, and braces `2·B` per enabled plane. Reference House 001 v2: 24 + 34 + 17 + 30 + 8 + 12 + 68 = **193**.

## Identity

Keys use stable line IDs plus ordinals, so members keep their IDs wherever their position survives (D041, D042):

- Footprint, story, and pitch edits keep every key; members move. A bay whose length changes may gain or lose joists at its far end.
- Spacing and purlin-count edits keep the lower ordinals (which move) and add or retire the rest.
- Turning a brace plane off and on re-adds its braces with new IDs; `UndoToRevision` restores the originals (D044).
- Inserting or removing a line recreates the members of the split or merged bays.
- Section changes move nothing (D058).

Preserve `TimberMember.id` when the `generation_key` still exists after regeneration. Create a new ID for a new key, and never reuse a retired ID for a different key. Inventories and `FrameSystem.member_ids` are sorted by `generation_key` in code-unit order.

## Connections

The rule declares all seven D054 junction classes, so projects carry their connection types from the start. It generates no `Connection` records until [CONN-001](../../implementation/tasks/README.md).

## Fixture and cross-language check

- **Fixture:** `uv run python -m homedesign.timber.fixture [--check]` builds `fixture.snapshot.json` and the packaged template from the D025 and D053 inputs. `--check` runs in `scripts/check.sh` and CI.
- **Oracle:** `tests/vectors/jcs/generate.mjs` implements this rule independently in ECMAScript. Its inventory vector must match the Python generator under the numeric rules above.

## Out of scope for this rule version

Connections (`CONN-001`), girts and studs (VS-02b), ridge beams, collar ties, rafter tails, dormers, hips, valleys, ceiling joists, floor openings, machining, walls, and any structural adequacy check.
