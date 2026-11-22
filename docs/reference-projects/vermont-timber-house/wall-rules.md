# Wall generation rules — `vs02b-walls-1`

**Status:** Approved, **not yet implemented** ([ASM-001](../../implementation/tasks/ASM-001.md), approved 2026-11-22; implemented together with [MODEL-006](../../implementation/tasks/MODEL-006.md)). Governing decisions: [D065](../../product/decisions/D065-vs02b-wall-placement.md), [D066](../../product/decisions/D066-vs02b-wall-framing.md), [D076](../../product/decisions/D076-vs02b-framed-opening-geometry.md), [D078](../../product/decisions/D078-vs02b-opening-framing-details.md), [D079](../../product/decisions/D079-vs02b-no-stacked-openings.md), and [D080](../../product/decisions/D080-vs02b-wall-key-formats.md).  
**Not** a structural design procedure. Walls and wall framing are geometric inventory only (AC-08). The jack threshold is a declared value, not derived from any code (D066).

The rule applies when `WallSystem.generation_rule_version` is `vs02b-walls-1`, the only registered wall rule. It sits beside the frame rule, [`vs02-frame-1`](generation-rules.md), and leaves the frame unchanged.

## Inputs

- The frame's inputs, as `vs02-frame-1` reads them: footprint, levels, grid lines, and the brace parameters `knee_brace_leg_m`, `knee_braces_level_1`, and `knee_braces_eave`. The rule reads no roof value and no member section.
- `WallSystem.default_assembly_definition_id`: every wall takes this definition. Its framing layer supplies the sections, spacing, girt count, and jack threshold (MODEL-006 §4.3).
- The `Opening` records: rough opening, sill height, and offset from the wall's start post axis.

## Numeric evaluation

The frame's rules apply ([generation-rules.md](generation-rules.md), "Numeric evaluation"): exact IEEE-754 formulas as written, no rounding or snapping, and generator output stored. **There is no `tan` exception**, so every coordinate is bit-identical across implementations. ε = 1e-6 m.

```text
For a wall on level i:  z_lo = level[i].elevation_m      H = level[i].story_height_m
For a wall in bay a-b:  A = x(a) or y(a)                 B = x(b) or y(b)        W = B - A
L = knee_brace_leg_m    braced = knee_braces_level_1 (level 0) or knee_braces_eave (level 1)
(u, v) ↦ (A + u, y, z_lo + v) along X;  (x, A + u, z_lo + v) along Y.  Post-axis ends use A and B directly.
```

## Walls

One wall in every perimeter bay of each story: `2 · ((nx − 1) + (ny − 1))` per story. Each wall runs from `(A, z_lo)` to `(B, z_lo)` along its grid line, starting at the lower station (west or south), with `height_m = H`. Its definition is the default. With its brace plane on, it has a brace at each top corner.

## Wall framing

The symbols come from the framing layer. `S` is the stud spacing and `n` the girt count. `t` is the stud section's `actual_width_m` and `t_g` the girt section's. `d` is the header's `actual_depth_m`, vertical. `b` is the buck section's `actual_width_m`. `T` is the jack threshold. An opening has rough opening `[o, o + w] × [s, s + h]`, and `j = 1` when `w > T + ε`.

```text
top(u) = (H - L) + u          if braced and u < L - ε
       = (H - L) + (W - u)    if braced and u > W - L + ε
       = H                    otherwise
```

- **Layout studs** (stud infill only) at `p_k = k * S`, for `k = 1, 2, …` while `A + k * S < B − ε`, from `v = 0` to `top(p_k)`.
- **Girts** (stud infill) at `v_i = H * f_i`, with `f_i = i / (n + 1)`. Each runs post axis to post axis, cut at openings. Girts are let in across every vertical piece they cross.
- **Stud infill opening framing:**

  | Piece | Position |
  |---|---|
  | Kings | `o - t / 2` and `o + w + t / 2` (j = 0); `o - 3 * t / 2` and `o + w + 3 * t / 2` (j = 1); from 0 to `top(u)` |
  | Jacks (j = 1) | `o - t / 2` and `o + w + t / 2`, from 0 to `s + h` |
  | Header | `o` to `o + w` (j = 0), or `o - t` to `o + w + t` (j = 1), at `s + h + d / 2` |
  | Rough sill (window) | `o` to `o + w`, at `s - t / 2` |
  | Cripples | At a claimed layout position: from `s + h + d` to `top(p_k)` above; for a window, from 0 to `s - t` below |

- **Straw bale opening framing (bucks):**

  | Piece | Position |
  |---|---|
  | Jambs | `o - b / 2` and `o + w + b / 2`, from `s - b` (window) or 0 (door) to `s + h + b` |
  | Head | `o` to `o + w`, at `s + h + b / 2` |
  | Sill (window) | `o` to `o + w`, at `s - b / 2` |

- **Framed rectangle** (D076): `u0 = o − (1 + j)·t` and `u1 = o + w + (1 + j)·t`; `v1 = s + h + d`; `v0 = s − t` for a window or 0 for a door. For straw bale, `u0, u1 = o ∓ b`, `v1 = s + h + b`, and `v0 = s − b` or 0. One helper computes it for both the pieces and the fit rules.
- **Pieces meet at faces** (D078 1a). Every piece meets the frame at a datum or a brace axis.
- **Layout studs at an opening** (D078 1b) are taken as bands `[p − t/2, p + t/2]`:
  - a band that overlaps a king by more than ε is dropped;
  - a band between the kings becomes an upper cripple and, for a window, a lower cripple;
  - the lower cripple is dropped where the band overlaps a jack.
- **Girt cuts** (D078 1c): a girt is cut when its band `[v − t_g/2, v + t_g/2]` overlaps `[v0, v1]` by more than ε. Its pieces stop at `u0` and `u1`.
- **Openings in one wall** never overlap along the wall (D079, checked by MODEL-006), so a stud or girt meets at most one opening.
- **No zero-length or negative pieces.** The rule never raises on a snapshot that passes stages 1–3.
- **Section and material:**
  - kings, jacks, cripples, and rough sills take the stud section; girts the girt section; headers the header section; bucks the buck section;
  - every piece takes the framing material.

## Keys and identity (D080)

| Record | `generation_key` |
|---|---|
| Wall | `wall/axis-x/{y}/{xa}-{xb}/level-{i}`, `wall/axis-y/{x}/{ya}-{yb}/level-{i}` |
| Layout stud | `{wall key}/stud/s{k}` |
| Girt piece | `{wall key}/girt/g{i}/start`, `{wall key}/girt/g{i}/after/{opening id}` |
| Opening framing | `{wall key}/opening/{opening id}/{piece}`. `{piece}` is `king/start\|end`, `jack/start\|end`, `header`, `rough-sill`, `cripple/s{k}/above\|below`, `buck-jamb/start\|end`, `buck-head`, or `buck-sill` |

- IDs are minted from `"generation/" + key` (D041), and kept while the key survives.
- Walls keep their keys under every edit except inserting or removing a perimeter grid line. Openings keep their wall's ID with it, and are removed with a removed wall (MODEL-006 §8.5).
- Restored layout studs get new IDs; `UndoToRevision` restores the originals (D044).
- The behavior under each edit is ASM-001 §6.2.

## Reference House 001 v3

- 20 walls, 1 door, and 19 windows ([D072](../../product/decisions/D072-reference-house-001-v3-design-intent.md)).
- **79** buck pieces with the straw bale default.
- **246** pieces with stud infill: 76 studs, 40 girts, 40 kings, 4 jacks, 20 headers, 19 rough sills, and 47 cripples.

The worked example is ASM-001 §5.8.

## Fixture and cross-language check

- **Fixture:** `uv run python -m homedesign.timber.fixture [--check]` builds the v3 fixture and the packaged template from both rules (ASM-001 §8.3).
- **Oracle:** `tests/vectors/jcs/generate.mjs` implements this rule independently. Its walls and wall framing, for the fixture and for a stud infill variant, must match Python bit for bit (ASM-001 §9).

## Out of scope for this rule version

Gable-end, interior, and off-grid walls; plates, let-in notches, fastenings, and bale counts; stacked or combined openings; code-dependent jack rules (open question 5); and any structural, fire, energy-code, or moisture claim.
