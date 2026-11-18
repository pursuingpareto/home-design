# VS-01 framing generation rules — `vs01-post-beam-1`

**Status:** Confirmed for Reference House 001 / VS-01 (D025).  
**Not** a structural design procedure. Generated members are geometric inventory only.

Applies when `TimberGrid.generation_rule_version` is `vs01-post-beam-1` and `FrameSystem.generation_mode` is `DETERMINISTIC_RULE`.

## Inputs

- Rectangular `Footprint` origin, width (X), depth (Y); the rule requires `origin_m = [0, 0]` and `rotation_rad = 0` ([D031](../../product/decisions/D031-vs01-unsupported-configurations.md))
- Two `Level` records, indices 0 and 1, elevations strictly increasing
- `GableRoof` (used for derived roof geometry; not for member generation in this rule version)
- Regular `TimberGrid` lines `x_lines` / `y_lines` (`{id, fraction}`, fractions strictly ascending from 0 to 1 inclusive; [D042](../../product/decisions/D042-stable-grid-line-ids.md))
- `FrameSystem.member_defaults` entries for `POST` and `BEAM` ([D039](../../product/decisions/D039-frame-member-defaults.md))

Eave plane: `z_eave = level[1].elevation_m + level[1].story_height_m` ([D033](../../product/decisions/D033-level-story-height.md)).

Station coordinates:

```text
x(line) = origin_x + width_m * line.fraction    for each line in x_lines
y(line) = origin_y + depth_m * line.fraction    for each line in y_lines
```

For this fixture the stored snapshot uses the exact 12'-0" station decimals (`0`, `3.6576`, `7.3152`, `10.9728`) so bay lengths match the accepted imperial intent. Regenerators must match those endpoints within the model comparison tolerance.

## Posts

At every grid station `(x, y)`, where `{x}` and `{y}` are line IDs (D042):

| `generation_key` | Axis |
|---|---|
| `frame/{x}/{y}/level-0/post` | `(x, y, level[0].elevation_m)` → `(x, y, level[1].elevation_m)` |
| `frame/{x}/{y}/level-1/post` | `(x, y, level[1].elevation_m)` → `(x, y, z_eave)` |

Role: `POST`. Section and material: `member_defaults.POST.section_id` and `member_defaults.POST.material_id`.

## Beams

Two planes only: `plane-L1` at `level[1].elevation_m`, `plane-eave` at `z_eave`. No members at Z = 0.

X-span (one member per X bay, each Y line; `{x_a}` and `{x_b}` are the bay's adjacent lines in ascending-fraction order):

```text
frame/axis-x/{y}/{x_a}-{x_b}/{plane}/beam
(x(x_a), y, z) → (x(x_b), y, z)
```

Y-span (one member per Y bay, each X line):

```text
frame/axis-y/{x}/{y_a}-{y_b}/{plane}/beam
(x, y(y_a), z) → (x, y(y_b), z)
```

Role: `BEAM`. Section and material: `member_defaults.BEAM.section_id` and `member_defaults.BEAM.material_id`. Beam `actual_depth_m` is vertical.

## Identity

Keys use stable line IDs, so members on lines that survive a grid edit keep their keys and IDs; splitting or merging a bay retires its beams and creates new ones (D042). Preserve `TimberMember.id` when the `generation_key` still exists after regeneration. Create a new ID for a new key. Never reuse a retired ID for a different key. Geometry and section may change without changing ID.

Sort inventories and `FrameSystem.member_ids` by `generation_key` ascending.

## Out of scope for this rule version

Joists, rafters, braces, sills, connections, machining, walls, and any structural adequacy check. `FLOOR_JOIST` and `RAFTER` must not be emitted.
