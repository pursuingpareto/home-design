# VS-01 framing generation rules — `vs01-post-beam-1`

**Status:** Confirmed for Reference House 001 / VS-01 (D025).  
**Not** a structural design procedure. Generated members are geometric inventory only.

Applies when `TimberGrid.generation_rule_version` is `vs01-post-beam-1` and `FrameSystem.generation_mode` is `DETERMINISTIC_RULE`.

## Inputs

- Rectangular `Footprint` origin, width (X), depth (Y); the rule requires `origin_m = [0, 0]` and `rotation_rad = 0` ([D031](../../product/decisions/D031-vs01-unsupported-configurations.md))
- Two `Level` records, indices 0 and 1, elevations strictly increasing
- `GableRoof` (used for derived roof geometry; not for member generation in this rule version)
- Regular `TimberGrid` fractions from 0 to 1 inclusive

Eave plane: `z_eave = level[1].elevation_m + level[1].clear_height_m`.

Station coordinates:

```text
x_i = origin_x + width_m * x_fractions[i]
y_j = origin_y + depth_m * y_fractions[j]
```

For this fixture the stored snapshot uses the exact 12'-0" station decimals (`0`, `3.6576`, `7.3152`, `10.9728`) so bay lengths match the accepted imperial intent. Regenerators must match those endpoints within the model comparison tolerance.

## Posts

At every grid station `(i, j)`:

| `generation_key` | Axis |
|---|---|
| `frame/x-{i}/y-{j}/level-0/post` | `(x_i, y_j, level[0].elevation_m)` → `(x_i, y_j, level[1].elevation_m)` |
| `frame/x-{i}/y-{j}/level-1/post` | `(x_i, y_j, level[1].elevation_m)` → `(x_i, y_j, z_eave)` |

Section: post section. Role: `POST`.

## Beams

Two planes only: `plane-L1` at `level[1].elevation_m`, `plane-eave` at `z_eave`. No members at Z = 0.

X-span (one member per X bay, each Y station):

```text
frame/axis-x/y-{j}/bay-{i}/{plane}/beam
(x_i, y_j, z) → (x_{i+1}, y_j, z)
```

Y-span (one member per Y bay, each X station):

```text
frame/axis-y/x-{i}/bay-{j}/{plane}/beam
(x_i, y_j, z) → (x_i, y_{j+1}, z)
```

Section: beam section. Role: `BEAM`. Beam `actual_depth_m` is vertical.

## Identity

Preserve `TimberMember.id` when the `generation_key` still exists after regeneration. Create a new ID for a new key. Never reuse a retired ID for a different key. Geometry and section may change without changing ID.

Sort inventories and `FrameSystem.member_ids` by `generation_key` ascending.

## Out of scope for this rule version

Joists, rafters, braces, sills, connections, machining, walls, and any structural adequacy check. `FLOOR_JOIST` and `RAFTER` must not be emitted.
