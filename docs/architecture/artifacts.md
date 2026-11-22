# Derived artifacts — DTO specification (VS-01, version 2 payloads for VS-02)

**Version:** 0.3 draft (2026-11-20)  
**Status:** Confirmed for VS-01 ([D027](../product/decisions/D027-vs01-artifact-dtos.md)); version 2 payloads (generator version `"2"`) for the complete VS-02 frame and its connections, from [ART-002](../implementation/tasks/ART-002.md) and [D060](../product/decisions/D060-vs02-artifact-payloads.md). **VS-02b (approved 2026-11-22, not yet implemented):** a fifth artifact, `assembly_schedule`, walls and wall framing in `plan2d` and `mesh3d`, and wall estimate lines, from [ART-003](../implementation/tasks/ART-003.md) and [D082](../product/decisions/D082-vs02b-framing-layer-fill-quantity.md)–[D086](../product/decisions/D086-vs02b-wall-framing-ids-in-views.md); marked in each section below. Payloads are display and reporting views, not the authoritative building model and not construction documents.  
**Related:** [building model](building-model.md), [dependencies](dependencies.md), [interfaces](interfaces.md), [geometry](geometry.md), [D025](../product/decisions/D025-reference-house-001-vs01-fixture.md), [D026](../product/decisions/D026-canonical-units-identity-persistence.md).

## 1. Artifact types

Stable `artifact_type` keys, used in URLs, manifests, previews, and dependency nodes:

| `artifact_type` | Owner module | VS-01 purpose |
|---|---|---|
| `plan2d` | `geometry` | Plan display geometry and explicit dimensions |
| `mesh3d` | `geometry` | Display primitives for interactive 3D (not a CAD kernel) |
| `timber_schedule` | `timber` | Member inventory, reference-axis lengths, aggregates |
| `preliminary_estimate` | `estimating` | Quantity-based cost only when dated unit prices exist |
| `assembly_schedule` (VS-02b; not yet implemented) | `assemblies` | Walls, openings, wall framing pieces, aggregates, assumptions, and D071's thermal figures (§7A) |

**VS-02b (not yet implemented):** the order becomes `plan2d`, `mesh3d`, `timber_schedule`, `assembly_schedule`, `preliminary_estimate` ([D070](../product/decisions/D070-vs02b-quantities-and-outputs.md); [ART-003](../implementation/tasks/ART-003.md) §8.2). No other artifact types are required for VS-01. Do not emit empty analysis, IFC, or approval artifacts.

## 2. Common envelope

Every artifact response, including 202 bodies, uses this envelope. `payload` is present only when `status` is `CURRENT` for the requested revision.

```json
{
  "artifact_type": "timber_schedule",
  "schema_version": 1,
  "project_id": "17ac32e0-0b3b-518e-b568-adf98f41bcd0",
  "source_revision_id": "01b311c6-7a51-528d-befe-b2e592819b66",
  "head": true,
  "generator_id": "schedule-vs01",
  "generator_version": "2",
  "input_fingerprint": "sha256:…",
  "generated_at": "2026-11-16T00:00:00Z",
  "status": "CURRENT",
  "suitability": "preliminary",
  "claims": {
    "structurally_verified": false,
    "construction_approved": false,
    "permit_ready": false
  },
  "warnings": [
    {
      "code": "PRELIMINARY_UNVERIFIED",
      "message": "Framing and estimates are preliminary. Structural adequacy has not been assessed."
    }
  ],
  "error": null,
  "payload": {}
}
```

`head` is `true` only when `source_revision_id` is the project's current head at the time of the request. An artifact requested for an older revision is served with `head: false` (§4; approved from [ART-001](../implementation/tasks/ART-001.md) §8, item 4).

### 2.1 Status

Same machine as [dependencies](dependencies.md#3-artifact-status-machine), plus estimate coverage:

| Status | Meaning | HTTP for `GET …/artifacts/{type}` |
|---|---|---|
| `MISSING` | Never computed for this revision | 202 with envelope, `payload` omitted |
| `QUEUED` / `COMPUTING` | Derivation in flight | 202, `payload` omitted |
| `CURRENT` | Fingerprint matches the inputs for `source_revision_id`, whether the payload was derived for this revision or reused from another revision of the project with the same fingerprint (§2.3) | 200 with `payload` |
| `FAILED` | Derivation failed; semantic model unchanged | 200 envelope with `error`; or 503 if the failure is a dependency outage. Never invent geometry or totals |
| `STALE` | Newer applicable inputs exist for this project head | Never returned as the current artifact for head. Manifest may list `STALE` |
| `UNAVAILABLE` | Inputs insufficient (VS-01: no unit prices for the estimate) | 200 envelope, `payload` may list unpriced quantities; no grand total |
| `SUPERSEDED` | A newer computation finished; this result must not be published | Not served |

A `FAILED` envelope's `error` is `{code, message}` with code `DERIVATION_FAILED` (the derivation raised or produced a payload that is not I-JSON) or `UPSTREAM_NOT_CURRENT` (a declared dependency, such as the schedule for the estimate, is not `CURRENT`). Messages never expose internals. The manifest only reports stored state and never derives. Reading an individual artifact derives it when it is `MISSING` or `STALE` ([ART-001](../implementation/tasks/ART-001.md) §4, §6).

`CURRENT` requires `input_fingerprint` to match the latest applicable inputs **for that artifact**. Matching `source_revision_id` alone is not enough when price books or generator versions differ.

### 2.2 Suitability (AC-08)

`suitability` is always `"preliminary"` in VS-01. `claims.*` are always `false`. The UI must label framing and estimates as preliminary, not verified or construction-approved. Do not omit `PRELIMINARY_UNVERIFIED`.

### 2.3 Fingerprint

`input_fingerprint` is `sha256:` plus lowercase hex of SHA-256 over the canonical input object for that generator ([D056](../product/decisions/D056-dependency-selectors.md), [D061](../product/decisions/D061-vs02-selector-contents.md), [DEP-001](../implementation/tasks/DEP-001.md) §5):

```json
{"selection": { "…": "§2.5" }, "generator_id": "plan2d-vs01", "generator_version": "2", "model_schema_version": 2}
```

- `preliminary_estimate` adds its external inputs: `{ "price_book_id", "price_book_version", "as_of", "currency" }`, or an explicit `"price_book": null`.
- The object holds no `revision_id`, no snapshot, no `project_id`, and no selector version. A selector change changes fingerprints, so stored rows read as `STALE` and are recomputed on read, as after a generator version change.
- **Reuse** (DEP-001 §7): when a revision's artifact has the fingerprint and generator version of a stored `CURRENT` or `UNAVAILABLE` row of any revision **of the same project**, that row is copied for the new revision (payload, warnings, and `generated_at` included) instead of being derived again. `FAILED` rows are never copied. The envelope is the new revision's own: `source_revision_id` and `head` name the requested revision (AC-07). Lazy recompute on read uses the same lookup; the manifest never derives or copies.

*Before VS-02* (ART-001 §8, item 3), the input object held `revision_id` and the whole snapshot, so fingerprints never matched across revisions and every revision derived its artifacts afresh.

Canonical bytes: RFC 8785 JSON Canonicalization Scheme, UTF-8 ([D029](../product/decisions/D029-canonical-json-rfc8785.md)). Object keys are ordered by JCS, arrays keep their documented order, and `null` is preserved. Selections hold no derived artifacts, except the estimate's copy of the schedule's three lists (§2.5).

### 2.4 Coordinates and units

Payload geometry uses D026: meters, +X east, +Y north, +Z up, radians. Display conversion to feet-inches is a UI concern. Payloads include `"units": "m"` (or a units object on the schedule/estimate). Measurements in the plan are explicit `value_m` fields, never pixel lengths.

### 2.5 Selections (VS-02)

Each derivation declares a pure **selector**: it extracts exactly the values its builder reads, after the projections the builder itself applies, and nothing else ([D061](../product/decisions/D061-vs02-selector-contents.md)). The builder takes the selection as its only model input. The selectors are the dependency graph ([dependencies.md](dependencies.md) §2). Arrays of members and connections are in `generation_key` order; numbers are the stored doubles.

| Artifact | Selection |
|---|---|
| `plan2d` | `footprint` (`origin_m`, `width_m`, `depth_m`, `rotation_rad`); `levels` (both IDs and elevations, Level 1's `story_height_m`); `roof.eave_overhang_m`; per member `id`, `generation_key`, `role`, `start_xy_m`, and `end_xy_m` except for posts; per connection `id`, `generation_key`, `junction_class`, `connection_type`, `xy_m`, `entering_member_id` |
| `mesh3d` | `footprint` (`origin_m`, `width_m`, `depth_m`); `levels` (elevations, Level 1's `story_height_m`); `roof` (`ridge_axis`, `pitch_rad`, `eave_overhang_m`); per member `id`, `generation_key`, `role`, `start_m`, `end_m`, and its section's `actual_width_m` and `actual_depth_m` (not its `section_id`); per connection `id`, `generation_key`, `junction_class`, `connection_type`, `location_m` |
| `timber_schedule` | per member `id`, `generation_key`, `role`, `length_m` (its reference-axis length, not its axis), `section_id`, `nominal_label`, `material_id`, `species`, `grade`; per connection `id`, `generation_key`, `junction_class`, `connection_type`, `member_ids` |
| `preliminary_estimate` | `{"timber_schedule": {aggregates, connection_aggregates, assumptions}}`, copied from the same revision's schedule payload, or `{"timber_schedule": null}` when the schedule is not `CURRENT`. It reads no snapshot. The price book is an external input (§2.3) |

**VS-02b selections ([ART-003](../implementation/tasks/ART-003.md) §8.1; not yet implemented).** The version 2 contents above are unchanged, and `timber_schedule`'s selection and generator version (`"2"`) do not change:

| Artifact | Added to the selection |
|---|---|
| `plan2d` | Per wall `id`, `generation_key`, `level_id`, `start_xy_m`, `end_xy_m`, `outward_xy`, and its definition's `exterior_m` and `interior_m` (§5, computed by the selector); per opening `id`, `wall_id`, `opening_kind`, `offset_m`, `width_m`; per piece `id`, `generation_key` (for order), `wall_id`, `piece_kind`, and its plan projection |
| `mesh3d` | Per wall `id`, `generation_key`, `start_m`, `end_m`, `height_m`, `outward_xy`, and its definition's layers (`name`, `function`, `thickness_m`, the framing layer's index); per opening `id`, `wall_id`, `opening_kind`, `offset_m`, `width_m`, `sill_height_m`, `height_m`; per piece `id`, `generation_key`, `wall_id`, `piece_kind`, `start_m`, `end_m`, `section_in_plane_m`, `section_through_wall_m` |
| `assembly_schedule` | Per wall `id`, `generation_key`, `level_id`, `level_index`, `elevation_side`, `assembly_definition_id`, `length_m`, `height_m`, and `framing_face_area_m2` (computed by the selector); per opening `id`, `opening_kind`, `wall_id`, `width_m`, `height_m`, `has_jacks` (from the pieces); per piece `id`, `generation_key`, `wall_id`, `piece_kind`, `opening_id`, `section_id`, `nominal_label`, `material_id`, `species`, `grade`, `length_m`; per definition in use, what §7A prints |
| `preliminary_estimate` | `{"timber_schedule": {…}, "assembly_schedule": {layer_aggregates, framing_aggregates, assumptions}}`, each copied from the same revision's payload, or `null` when not `CURRENT` |

Not selected: the `WallSystem` record, unused definitions, opening positions in the schedule, and piece positions anywhere but the views.

No selection holds the `TimberGrid`, the `FrameSystem`, unused sections and materials, record `schema_version` fields, or revision metadata: their effects reach payloads only through the members and connections. The exact shapes, with examples, are in [DEP-001](../implementation/tasks/DEP-001.md) §4.2.

## 3. Manifest

`GET /api/v1/projects/{id}/artifacts?revision_id={rev}`

`revision_id` omitted means project head. Response: envelope-like records **without** `payload`, plus a top-level `head` flag for the requested revision.

```json
{
  "project_id": "17ac32e0-0b3b-518e-b568-adf98f41bcd0",
  "revision_id": "01b311c6-7a51-528d-befe-b2e592819b66",
  "head": true,
  "artifacts": [
    {"artifact_type": "plan2d", "status": "CURRENT", "source_revision_id": "01b311c6-7a51-528d-befe-b2e592819b66", "generator_version": "2", "input_fingerprint": "sha256:…"},
    {"artifact_type": "mesh3d", "status": "COMPUTING", "source_revision_id": "01b311c6-7a51-528d-befe-b2e592819b66", "generator_version": "2", "input_fingerprint": null},
    {"artifact_type": "timber_schedule", "status": "CURRENT", "source_revision_id": "01b311c6-7a51-528d-befe-b2e592819b66", "generator_version": "2", "input_fingerprint": "sha256:…"},
    {"artifact_type": "preliminary_estimate", "status": "UNAVAILABLE", "source_revision_id": "01b311c6-7a51-528d-befe-b2e592819b66", "generator_version": "2", "input_fingerprint": "sha256:…"}
  ]
}
```

All four types appear on every VS-01 revision manifest; with VS-02b, five, `assembly_schedule` included (D070; not yet implemented). Commit responses use the same four keys in `artifact_statuses` (status only; no payload).

## 4. View consistency (AC-01, AC-02, AC-07)

The browser may render 2D and 3D together only when `plan2d` and `mesh3d` share the same `source_revision_id` and both are `CURRENT`. If either is `COMPUTING`, `STALE`, or `FAILED`, the UI must show that status and must not pair a current view with a previous revision’s geometry.

Historical `GET` with an explicit `revision_id` returns the artifact **for that revision**. That payload may be `CURRENT` for the requested revision after head has moved; it must not be labeled as the live project head, and its envelope carries `head: false`.

## 5. `plan2d` payload

`generator_id`: `plan2d-vs01`. `generator_version`: `2` ([ART-002](../implementation/tasks/ART-002.md) §4; [D060](../product/decisions/D060-vs02-artifact-payloads.md)).

Four planes, each with one array per member role and a `connections` array. Every plane has every array; arrays with no members are empty. Abridged to one entry per array for Reference House 001 v2:

```json
{
  "units": "m",
  "planes": [
    {
      "plane_id": "level-0",
      "level_id": "bb53ff6a-c109-5f1a-a6fb-e16fd8d7f4ed",
      "z_m": 0.0,
      "posts": [{ "member_id": "…", "generation_key": "frame/x0/y0/level-0/post", "xy_m": [0.0, 0.0] }],
      "beams": [],
      "sills": [{ "member_id": "…", "generation_key": "frame/axis-x/y0/x0-x1/plane-L0/sill", "start_xy_m": [0.0, 0.0], "end_xy_m": [3.6575999999999995, 0.0] }],
      "joists": [], "braces": [], "rafters": [], "purlins": [],
      "connections": [
        {
          "connection_id": "…",
          "generation_key": "connection/post-sill/frame/axis-y/x0/y0-y1/plane-L0/sill/frame/x0/y0/level-0/post",
          "junction_class": "post-sill",
          "connection_type": "PEGGED_MORTISE_TENON",
          "xy_m": [0.0, 0.0]
        }
      ]
    },
    {
      "plane_id": "level-1",
      "level_id": "85281672-fc1f-5723-a2e1-f85e25b1d336",
      "z_m": 3.048,
      "posts": [{ "member_id": "…", "generation_key": "frame/x0/y0/level-1/post", "xy_m": [0.0, 0.0] }],
      "beams": [{ "member_id": "…", "generation_key": "frame/axis-x/y0/x0-x1/plane-L1/beam", "start_xy_m": [0.0, 0.0], "end_xy_m": [3.6575999999999995, 0.0] }],
      "sills": [],
      "joists": [{ "member_id": "…", "generation_key": "frame/axis-y/x0-x1/j1/y0-y1/plane-L1/joist", "start_xy_m": [0.6096, 0.0], "end_xy_m": [0.6096, 3.6576] }],
      "braces": [{ "member_id": "…", "generation_key": "frame/axis-x/y0/x0-x1/plane-L1/brace/x0", "start_xy_m": [0.0, 0.0], "end_xy_m": [0.9144, 0.0] }],
      "rafters": [], "purlins": [],
      "connections": ["… 162 markers: post-beam, brace, joist-beam"]
    },
    {
      "plane_id": "eave", "level_id": null, "z_m": 5.7912,
      "posts": [], "beams": ["… 17"], "sills": [], "joists": [], "braces": ["… 34"], "rafters": [], "purlins": [],
      "connections": ["… 102 markers: post-beam, brace"]
    },
    {
      "plane_id": "roof",
      "level_id": null,
      "z_m": 5.7912,
      "posts": [], "beams": [], "sills": [], "joists": [], "braces": [],
      "rafters": [{ "member_id": "…", "generation_key": "frame/roof/x0/north/principal-rafter", "start_xy_m": [0.0, 7.3152], "end_xy_m": [0.0, 3.6576] }],
      "purlins": [{ "member_id": "…", "generation_key": "frame/roof/x0-x1/north/p1/purlin", "start_xy_m": [0.0, 6.096], "end_xy_m": [3.6575999999999995, 6.096] }],
      "connections": ["… 36 markers: rafter-peak, rafter-foot, purlin-rafter"]
    }
  ],
  "footprint": {
    "origin_m": [0.0, 0.0],
    "width_m": 10.9728,
    "depth_m": 7.3152,
    "rotation_rad": 0.0,
    "ring_m": [[0.0, 0.0], [10.9728, 0.0], [10.9728, 7.3152], [0.0, 7.3152]]
  },
  "roof_plan": {
    "ridge_m": { "start_xy_m": [0.0, 3.6576], "end_xy_m": [10.9728, 3.6576] },
    "eave_ring_m": [[0.0, -0.6096], [10.9728, -0.6096], [10.9728, 7.9248], [0.0, 7.9248]]
  },
  "dimensions": [
    { "id": "footprint-width", "start_m": [0.0, 0.0], "end_m": [10.9728, 0.0], "value_m": 10.9728 },
    { "id": "footprint-depth", "start_m": [0.0, 0.0], "end_m": [0.0, 7.3152], "value_m": 7.3152 }
  ]
}
```

(Strings such as `"… 17"` stand for omitted entries; a payload never contains them.)

**Planes and members** (ART-002 §4.1). The role picks the array and a key segment picks the plane:

| Plane | `level_id` | `z_m` | Arrays (key segment) | Reference House 001 v2 |
|---|---|---|---|---|
| `level-0` | Level 0 | Level 0 elevation | `posts` (`/level-0/post`), `sills` (`/plane-L0/sill`) | 12 posts, 17 sills |
| `level-1` | Level 1 | Level 1 elevation | `posts` (`/level-1/post`), `beams` (`/plane-L1/beam`), `joists` (`/plane-L1/joist`), `braces` (`/plane-L1/brace/`) | 12, 17, 30, 34 |
| `eave` | `null` | `z_eave` | `beams` (`/plane-eave/beam`), `braces` (`/plane-eave/brace/`) | 17, 34 |
| `roof` | `null` | `z_eave` | `rafters` (`PRINCIPAL_RAFTER`, `/principal-rafter`), `purlins` (`PURLIN`, `/purlin`) | 8, 12 |

- **One entry per member:** 193 for Reference House 001 v2, the same IDs as the snapshot, `mesh3d`, and `timber_schedule`. A member whose role and key match no row fails the derivation (`FAILED`, `DERIVATION_FAILED`). The role is matched first, because a joist's or brace's key also contains its beam plane's segment.
- **Shapes:** posts are `{member_id, generation_key, xy_m}`; every other array holds `{member_id, generation_key, start_xy_m, end_xy_m}`.
- **No `section_id`:** the plan reads member axes and roles, not sections, so a section change leaves `plan2d` byte-identical ([D056](../product/decisions/D056-dependency-selectors.md); ART-002 §4.3). Clients join on `member_id` with the schedule or mesh for sections.
- **The roof plane** ([D060](../product/decisions/D060-vs02-artifact-payloads.md)) is the roof framing view. Its `z_m` is `z_eave`, the plate line where the roof framing bears ([D058](../product/decisions/D058-datum-reference-axes.md)). Rafters and purlins rise from it; their entries are plan projections. A rafter projects from the wall line to the ridge line.

**Connection markers** (ART-002 §4.2): `connections` holds one marker per `Connection`, `{connection_id, generation_key, junction_class, connection_type, xy_m}`.

- **Plane:** the plane of the **entering** member (`member_ids[1]`, [D059](../product/decisions/D059-vs02-junction-rules-connection-type-command.md)). So `post-sill` is on `level-0`; `post-beam`, `brace`, and `joist-beam` on their member's plane; `rafter-foot`, `rafter-peak`, and `purlin-rafter` on `roof`.
- **Position:** `xy_m` is the plan projection of the record's `location_m`.
- **Reference House 001 v2:** 12 on `level-0`, 162 on `level-1` (34 post-beam, 68 brace, 60 joist-beam), 102 on `eave` (34 post-beam, 68 brace), and 36 on `roof` (4 peak, 8 foot, 24 purlin-rafter): 312 in all.
- **Coincident markers** are all kept (up to eight share an interior Level 1 station). How to draw them is the client's concern (`UI-003`).
- **No `member_ids`:** the schedule lists them (§7), and clients join on `connection_id`.

`footprint.ring_m` is the wall rectangle, counterclockwise from origin, **not** including eave overhang. `roof_plan.eave_ring_m` includes the 2'-0" north/south overhang (D025).

Further rules ([GEOM-001](../implementation/tasks/GEOM-001.md) §3, approved as §7 item 4; ART-002 §4):

- **Ordering:** planes in the order `level-0`, `level-1`, `eave`, `roof`. Within each plane, every member array and `connections` is sorted by `generation_key` (UTF-16 code units).
- **Positions:** a post's `xy_m` is its `start_m` x and y. Every other entry's `start_xy_m` and `end_xy_m` are the plan projections of its `start_m` and `end_m`. No plan position depends on the roof pitch.
- **Roof plan:** the ridge runs along X at `y = origin_y + depth_m / 2`, from `origin_x` to `origin_x + width_m`. The eave ring extends `eave_overhang_m` to the north and south only. There is **no rake (gable-end) overhang**.

`dimensions` contains **exactly** `footprint-width` and `footprint-depth`, with `value_m` copied from the footprint, never measured from rendered geometry (AC-01). Bay and grid dimension lines are not part of the payload.

### VS-02b: walls, openings, and wall framing ([ART-003](../implementation/tasks/ART-003.md) §5; not yet implemented)

`generator_version` moves to `3`. The `level-0` and `level-1` planes gain `walls` and `wall_framing`; every plane has both arrays, empty on `eave` and `roof`. Each wall and piece is on its own level's plane.

```json
{"wall_id": "…", "generation_key": "wall/axis-x/y0/x0-x1/level-0",
 "start_xy_m": [0.0, 0.0], "end_xy_m": [3.6576, 0.0], "outward_xy": [0.0, -1.0],
 "exterior_m": 0.2667, "interior_m": 0.254,
 "openings": [{"opening_id": "…", "opening_kind": "WINDOW", "start_xy_m": [1.0668, 0.0], "end_xy_m": [2.5908, 0.0]}]}
```

- **Layer placement** ([D083](../product/decisions/D083-vs02b-layer-placement.md)): the framing layer is centered on the reference plane (the grid line); earlier layers stack toward the exterior (away from the footprint) and later ones toward the interior. `exterior_m` and `interior_m` are the build-up's extents on each side: 10½" and 10" for `straw-bale`, 4" and 3¼" for `stud-infill`.
- **Outline and gaps:** the wall is the band from `start_xy_m` to `end_xy_m`, `exterior_m` outward and `interior_m` inward, with a gap through its full thickness at each rough opening, at `start + offset_m` and `start + (offset_m + width_m)` along the wall. Walls are sorted by key; their openings by `offset_m`, then ID.
- **Wall framing:** one entry per piece, sorted by the piece's key: vertical pieces (`STUD`, `KING`, `JACK`, `CRIPPLE`, `BUCK_JAMB`) as `{piece_id, piece_kind, xy_m}`, horizontal ones (`GIRT`, `HEADER`, `ROUGH_SILL`, `BUCK_HEAD`, `BUCK_SILL`) as `{piece_id, piece_kind, start_xy_m, end_xy_m}`. **No key and no section** ([D086](../product/decisions/D086-vs02b-wall-framing-ids-in-views.md)): clients join on `piece_id` with the assembly schedule.
- **The two switches** ([D066](../product/decisions/D066-vs02b-wall-framing.md)): `walls` and `wall_framing` are separate arrays, so "Wall layers" and "Wall framing" each hide one.

## 6. `mesh3d` payload

`generator_id`: `mesh3d-vs01`. `generator_version`: `2` ([ART-002](../implementation/tasks/ART-002.md) §5).

This is a **display primitive** list. The client (or a later adapter) tessellates. It is not OpenCascade, glTF, or a Three.js scene graph.

```json
{
  "units": "m",
  "members": [
    {
      "member_id": "…",
      "generation_key": "frame/x0/y0/level-0/post",
      "role": "POST",
      "primitive": "oriented_box",
      "axis_start_m": [0.0, 0.0, 0.0],
      "axis_end_m": [0.0, 0.0, 3.048],
      "section_width_m": 0.2032,
      "section_depth_m": 0.2032
    }
  ],
  "connections": [
    {
      "connection_id": "…",
      "generation_key": "connection/rafter-peak/frame/roof/x0/south/principal-rafter/frame/roof/x0/north/principal-rafter",
      "junction_class": "rafter-peak",
      "connection_type": "BRIDLE",
      "location_m": [0.0, 3.6576, 8.5344]
    }
  ],
  "envelope": {
    "footprint_ring_m": [[0.0, 0.0], [10.9728, 0.0], [10.9728, 7.3152], [0.0, 7.3152]],
    "level_z_m": [0.0, 3.048],
    "z_eave_m": 5.7912,
    "roof": {
      "kind": "gable",
      "ridge_axis": "X",
      "pitch_rad": 0.6435011087932844,
      "ridge_start_m": [0.0, 3.6576, 8.5344],
      "ridge_end_m": [10.9728, 3.6576, 8.5344],
      "surfaces": [
        {
          "id": "south",
          "ring_m": [
            [0.0, -0.6096, 5.334],
            [10.9728, -0.6096, 5.334],
            [10.9728, 3.6576, 8.5344],
            [0.0, 3.6576, 8.5344]
          ]
        },
        {
          "id": "north",
          "ring_m": [
            [0.0, 7.9248, 5.334],
            [0.0, 3.6576, 8.5344],
            [10.9728, 3.6576, 8.5344],
            [10.9728, 7.9248, 5.334]
          ]
        }
      ]
    }
  }
}
```

Box orientation (one rule for every role; ART-002 §5.1):

- The member axis is `axis_start_m` → `axis_end_m` (the semantic `start_m` / `end_m`).
- **Vertical axis (posts):** `section_width_m` along +X, `section_depth_m` along +Y.
- **Any other axis:** `section_width_m` is horizontal and perpendicular to the axis's plan projection. `section_depth_m` is along `axis × width`, perpendicular to both, taken with a non-negative Z component.

What the rule gives each role:

| Role | Width | Depth |
|---|---|---|
| `BEAM`, `SILL`, `FLOOR_JOIST` | Horizontal, across the member | Vertical ([D053](../product/decisions/D053-reference-house-001-v2-design-intent.md): joists "depth vertical") |
| `PRINCIPAL_RAFTER` | Along X (across the bent) | Perpendicular to the roof plane (D053) |
| `KNEE_BRACE` | Perpendicular to its beam's vertical plane | In that plane, perpendicular to the brace ([D058](../product/decisions/D058-datum-reference-axes.md)) |
| `PURLIN` | Horizontal, along Y | Vertical: purlins are plumb ([D060](../product/decisions/D060-vs02-artifact-payloads.md)) |

The boxes carry `section_width_m` and `section_depth_m` only; the orientation is the rule, not a payload field. The client's `memberMatrix` (`frontend/src/views/meshScene.ts`) implements it.

`members` order: `generation_key` ascending. Count and IDs must match the semantic inventory. Envelope numbers for Reference House 001 must match D025 (ridge `z = 8.5344 m`).

**Connection markers** (ART-002 §5.2): `connections`, beside `members`, has one `{connection_id, generation_key, junction_class, connection_type, location_m}` per `Connection`, sorted by `generation_key`. `location_m` is the record's, copied exactly. There is no size, primitive, or shape: the payload says where a connection is and what type it has, and the client chooses a marker ([D054](../product/decisions/D054-vs02-connection-catalog.md)). Count and IDs equal the snapshot's connections (312 for Reference House 001 v2).

Roof surfaces ([D048](../product/decisions/D048-roof-plane-through-wall-line.md)): each plane passes through the wall line at `z_eave_m` at `pitch_rad`, so the overhang edge is at `z_eave − eave_overhang_m · tan(pitch_rad)` (5.334 m for Reference House 001) and the ridge at `z_eave + (depth_m / 2) · tan(pitch_rad)` (8.5344 m). `z_eave_m` stays the eave plate height.

### VS-02b: walls and wall framing ([ART-003](../implementation/tasks/ART-003.md) §6; not yet implemented)

`generator_version` moves to `3`. Two top-level arrays join `members` and `connections`, each sorted by key:

```json
{"wall_id": "…", "generation_key": "wall/axis-x/y0/x0-x1/level-0", "primitive": "layered_wall",
 "base_start_m": [0.0, 0.0, 0.0], "base_end_m": [3.6576, 0.0, 0.0], "height_m": 3.048, "outward_xy": [0.0, -1.0],
 "layers": [{"name": "lime-plaster", "function": "FINISH", "inner_m": 0.2286, "outer_m": 0.2667},
            {"name": "bales", "function": "FRAMING", "inner_m": -0.2286, "outer_m": 0.2286},
            {"name": "clay-plaster", "function": "FINISH", "inner_m": -0.254, "outer_m": -0.2286}],
 "voids": [{"opening_id": "…", "opening_kind": "WINDOW", "u_m": [1.0668, 2.5908], "v_m": [0.9144, 2.1336]}]}
{"piece_id": "…", "piece_kind": "KING", "wall_id": "…", "axis_start_m": [1.35255, 0.0, 0.0], "axis_end_m": [1.35255, 0.0, 3.048],
 "section_in_plane_m": 0.0381, "section_through_wall_m": 0.1397}
```

- **`walls`:** a `layered_wall` is one box per layer, along the wall from `base_start_m` to `base_end_m`, up `height_m`, and from `inner_m` to `outer_m` along `outward_xy` (D083). The framing layer's box is its fill. `voids` are the rough openings in wall-local `u` (along the wall) and `v` (up), through every layer, sorted by `u_m[0]`, then ID.
- **`wall_framing`:** one oriented box per piece, with no key and no `primitive` field (D086). `section_through_wall_m` lies along its wall's `outward_xy`, and `section_in_plane_m` in the wall's plane, perpendicular to the axis. In-plane is the section's `actual_width_m` and through-wall its `actual_depth_m`, reversed for a header (D076).

## 7. `timber_schedule` payload

`generator_id`: `schedule-vs01`. `generator_version`: `2` ([ART-002](../implementation/tasks/ART-002.md) §6).

```json
{
  "units": { "length": "m", "count": "1" },
  "length_basis": "reference_axis",
  "assumptions": [
    { "code": "REFERENCE_AXIS_LENGTH", "message": "Lengths are reference-axis distances, not fabrication cut lengths." },
    { "code": "CONNECTIONS_REPRESENTATIONAL", "message": "Connections are listed by type and count only. Types are representational: no capacity, sizes, fasteners, or machining." },
    { "code": "UNCLASSED_JOINTS_NOT_COUNTED", "message": "Joints without a junction class, such as post splices and sill joints at grid stations, are not counted." }
  ],
  "members": [
    {
      "member_id": "…",
      "generation_key": "frame/axis-x/y0/x0-x1/plane-L1/beam",
      "role": "BEAM",
      "nominal_section": "8x12",
      "section_id": "…",
      "material_id": "…",
      "species": "eastern-white-pine",
      "grade": null,
      "length_m": 3.6576,
      "quantity": 1
    }
  ],
  "aggregates": [
    { "role": "BEAM", "nominal_section": "8x12", "count": 34, "total_length_m": 124.3584 }
  ],
  "connections": [
    {
      "connection_id": "…",
      "generation_key": "connection/brace/frame/axis-x/y0/x0-x1/plane-L1/beam/frame/axis-x/y0/x0-x1/plane-L1/brace/x0",
      "junction_class": "brace",
      "connection_type": "PEGGED_MORTISE_TENON",
      "member_ids": ["<receiving>", "<entering>"],
      "quantity": 1
    }
  ],
  "connection_aggregates": [
    { "junction_class": "brace", "connection_type": "PEGGED_MORTISE_TENON", "count": 136 }
  ],
  "connection_catalog": {
    "catalog_version": "vs02-connections-1",
    "types": [
      { "connection_type": "BRIDLE", "family": "traditional", "description": "Bridle joint. Representational only: no capacity, sizes, or fasteners." }
    ]
  }
}
```

Invariants for members:

- `members` sorted by `generation_key`. One row per semantic `TimberMember`. `quantity` is 1.
- `length_m` is the Euclidean length of `start_m`–`end_m`, computed as `sqrt(dx*dx + dy*dy + dz*dz)` with `d = end_m − start_m`, evaluated exactly as written in IEEE-754 doubles. Library `hypot`/`dist` functions are not used, because they can differ in the last bit across languages ([EST-001](../implementation/tasks/EST-001.md) §3, approved as §7 item 1). Compared with 1e-6 m.
- `sum(members.quantity)` equals inventory size; `aggregates.count` sums to the same; `aggregates.total_length_m` equals the sum of `length_m` within 1e-6 m × n.
- Exactly **one aggregate per role and section**; posts are never split by story. `count` and `total_length_m` are summed over the member rows in `generation_key` order ([EST-001](../implementation/tasks/EST-001.md) §3, approved as §7 item 2; closes C6).
- `aggregates` sorted by `role`, then `nominal_section`.
- Same snapshot + same `generator_version` yields the same IDs, keys, roles, sections, and lengths (numeric tolerance 1e-6 m).

Connections (ART-002 §6.1–6.3; [D054](../product/decisions/D054-vs02-connection-catalog.md), [D059](../product/decisions/D059-vs02-junction-rules-connection-type-command.md)):

- **`connections`:** one row per `Connection`, sorted by `generation_key`. `member_ids` is the record's `[receiving, entering]` pair. There is **no location**: positions belong to the views, so a change that only moves the frame leaves the connection rows unchanged. `quantity` is 1.
- **`connection_aggregates`:** one row per (`junction_class`, `connection_type`) pair with at least one connection, with its `count`, sorted by class, then type. Zero rows are omitted. A class has one type at a time, so a class's count is its row, and a type's count is the sum of its rows. The counts sum to the number of connection rows and of `Connection` records, and each class's count equals CONN-001 §6's formula.
- **`connection_catalog`:** the catalog version and, for exactly the types in `connection_aggregates`, sorted by type, each type's `family` (`traditional` or `engineered`) and `description`. Every description says the type is representational only.

| Type | Family | Description |
|---|---|---|
| `PEGGED_MORTISE_TENON` | `traditional` | Pegged mortise and tenon. Representational only: no capacity, sizes, or fasteners. |
| `BRIDLE` | `traditional` | Bridle joint. Representational only: no capacity, sizes, or fasteners. |
| `HOUSED_DOVETAIL` | `traditional` | Housed dovetail. Representational only: no capacity, sizes, or fasteners. |
| `STEEL_KNIFE_PLATE` | `engineered` | Concealed steel knife plate with dowels. Representational only: no capacity, sizes, or fasteners. |
| `JOIST_HANGER` | `engineered` | Joist hanger. Representational only: no capacity, sizes, or fasteners. |

- **`assumptions`:** exactly the three lines above, in that order. `UNCLASSED_JOINTS_NOT_COUNTED` is the line D059 requires: post splices and sill joints are not counted.

Reference House 001 v2 expected aggregates ([D053](../product/decisions/D053-reference-house-001-v2-design-intent.md); compared within 1e-6 m × n):

| Role | Section | Count | Total (m) |
|---|---|---|---|
| `BEAM` | 8×12 | 34 | 124.3584 (34 × 3.6576) |
| `FLOOR_JOIST` | 4×8 | 30 | 109.728 (30 × 3.6576) |
| `KNEE_BRACE` | 4×6 | 68 | 87.934668 (68 × 0.9144 √2) |
| `POST` | 8×8 | 24 | 69.4944 (12 × 3.048 on Level 0 + 12 × 2.7432 on Level 1; informational breakdown, not separate rows) |
| `PRINCIPAL_RAFTER` | 8×10 | 8 | 36.576 (8 × 4.572) |
| `PURLIN` | 6×8 | 12 | 43.8912 (12 × 3.6576) |
| `SILL` | 8×8 | 17 | 62.1792 (17 × 3.6576) |

And connection aggregates, with the default types:

| `junction_class` | `connection_type` | `count` |
|---|---|---|
| `brace` | `PEGGED_MORTISE_TENON` | 136 |
| `joist-beam` | `HOUSED_DOVETAIL` | 60 |
| `post-beam` | `PEGGED_MORTISE_TENON` | 68 |
| `post-sill` | `PEGGED_MORTISE_TENON` | 12 |
| `purlin-rafter` | `PEGGED_MORTISE_TENON` | 24 |
| `rafter-foot` | `PEGGED_MORTISE_TENON` | 8 |
| `rafter-peak` | `BRIDLE` | 4 |

## 7A. `assembly_schedule` payload (VS-02b; not yet implemented)

`generator_id`: `assembly-schedule-vs02b`. `generator_version`: `1`. Owner: `assemblies` ([D070](../product/decisions/D070-vs02b-quantities-and-outputs.md), [D071](../product/decisions/D071-vs02b-thermal-moisture-values.md)). The full contract, with an example, the reference house figures, and the numeric rules, is [ART-003](../implementation/tasks/ART-003.md) §4; in brief:

- **Units:** `{length: m, area: m2, volume: m3, count: 1, thermal_transmittance: W/(m2.K), thermal_resistance: m2.K/W, heat_flow: W/K}`, and `quantity_basis: "reference"`.
- **`walls`** (by key): `level_id`, `level_index`, `elevation_side`, the definition, `length_m`, `height_m`, gross, opening, and net areas, `framing_face_area_m2`, `framing_fraction`, and the parallel-path `u_value_w_m2_k`, `r_value_m2_k_w`, `ua_w_k` (or `null`).
- **`openings`** (by wall key, then ID): kind, wall, rough-opening `width_m` and `height_m`, `area_m2`, and `has_jacks` (from the generated pieces). No position.
- **`wall_framing`** (by key): one row per piece, shaped like the timber schedule's member rows plus `wall_id` and `opening_id`. Reference-axis lengths, no position.
- **Face areas:** a piece's face is its in-plane dimension times its axis. Per wall, faces are summed in key order, less each girt-to-vertical-piece overlap, so crossings count once (ASM-001 §5.6).
- **`definitions`:** only those used by a wall, with the installation note, unverified climate details, layers (declared values as stored, with provenance), and framing parameters.
- **Aggregates:** `definition_aggregates`, `layer_aggregates` (non-framing layers at net area; the framing layer's fill net of framing, [D082](../product/decisions/D082-vs02b-framing-layer-fill-quantity.md); volume = area × thickness), `framing_aggregates` (count and length per kind and section), `opening_aggregates`, and `totals`.
- **`assumptions`**, in order: `WALLS_ONLY`, `REFERENCE_AREA`, `REFERENCE_AXIS_LENGTH`, `FILL_NET_OF_FRAMING`, `NO_PLATES_OR_NOTCHES`, `FASTENINGS_NOT_COUNTED`, `JACK_THRESHOLD_DECLARED`, `OPENINGS_ARE_VOIDS`, `FIT_TO_AXES_ONLY` (worded in ART-003 §4.7).
- **`thermal`** (`parallel-path-1`): layer resistances from a declared conductivity or resistance; `R_fill` and `R_framing` summed exterior to interior, with **no surface air films** ([D084](../product/decisions/D084-vs02b-no-surface-air-films.md)); per wall `U = f / R_framing + (1 − f) / R_fill`; per definition the center-of-cavity and framing-path values and area-weighted figures, and the same for all walls. A figure is `null` unless every input it uses is known, with `missing_inputs` naming the definition, layer, and fields. `method.notes` carry D071's labels.
- **Envelope warning:** every envelope carries `CLIMATE_DETAILS_UNVERIFIED` after `PRELIMINARY_UNVERIFIED`.
- **Reference House 001 v3:** 20 walls, 20 openings, 79 buck pieces (246 with stud infill); 187.29252864 m² (2,016 sf) net; framing fraction 1.86% overall with straw bale (10.76% with stud infill); every figure but `f` is `null`.

## 8. `preliminary_estimate` payload

`generator_id`: `estimate-vs01`. `generator_version`: `2` ([ART-002](../implementation/tasks/ART-002.md) §7).

VS-01 does **not** introduce a `CostDataset` entity. Optional dated unit prices live in **project estimate configuration**, outside the semantic snapshot. Default for new reference projects: **no price book**.

### 8.1 Gating

| Price configuration | Envelope `status` | `coverage` | `totals.grand_total_minor` |
|---|---|---|---|
| None | `UNAVAILABLE` | `none` | `null` |
| Some line items have unit prices, others do not | `CURRENT` | `partial` | `null` (must not imply a complete project cost) |
| Every emitted line item has a unit price | `CURRENT` | `complete` | integer minor units |

Never set a missing total to `0`. Never invent Vermont prices. Open question 6 (dataset licensing) stays open.

Money: integer minor units + ISO 4217 code (D026). VS-01 uses `USD` when a book is present; `currency` is `null` when coverage is `none`.

**Rounding** ([EST-001](../implementation/tasks/EST-001.md) §4, approved as §7 item 5):

- **Line amounts:** `amount_minor` is `unit_price_minor × quantity_value`, multiplied **exactly**, using the double's exact binary value in decimal arithmetic. It is then rounded once to an integer with **round-half-even**. For a connection line the quantity is an integer count, so the product is exact and no rounding applies.
- **Totals:** `priced_amount_minor` and `grand_total_minor` are sums of the rounded line amounts, so totals always equal the visible lines.
- **Reproducible:** the rule gives the same result in any language with exact decimal or big-integer arithmetic (for example Python `Decimal`, ECMAScript `BigInt`). It never uses binary floating-point rounding.

Line items are discriminated by `kind` ([D060](../product/decisions/D060-vs02-artifact-payloads.md); ART-002 §7.1):

- **`timber`:** one line per schedule aggregate, `key` `timber.<ROLE>.<nominal_section>`, with `role` and `nominal_section`, and the aggregate's `total_length_m` as `quantity_value` in `m`.
- **`connection`:** one line per connection type with a non-zero count ([D054](../product/decisions/D054-vs02-connection-catalog.md): "one line per type"), `key` `connection.<TYPE>`, with `connection_type`. `quantity_value` is the integer sum of that type's `connection_aggregates` counts, and `quantity_unit` is `each`. There is no `role` or `nominal_section`.

Abridged for Reference House 001 v2 with no book (ten lines: three connection lines, then the seven timber lines of §7):

```json
{
  "coverage": "none",
  "currency": null,
  "price_book": null,
  "line_items": [
    {
      "kind": "connection",
      "key": "connection.BRIDLE",
      "connection_type": "BRIDLE",
      "quantity_value": 4,
      "quantity_unit": "each",
      "unit_price_minor": null,
      "amount_minor": null,
      "priced": false
    },
    {
      "kind": "timber",
      "key": "timber.BEAM.8x12",
      "role": "BEAM",
      "nominal_section": "8x12",
      "quantity_value": 124.35840000000005,
      "quantity_unit": "m",
      "unit_price_minor": null,
      "amount_minor": null,
      "priced": false
    }
  ],
  "totals": {
    "priced_amount_minor": null,
    "unpriced_line_count": 10,
    "grand_total_minor": null
  },
  "assumptions": ["… the schedule's three lines, copied"]
}
```

- **Ordering:** line items are sorted by `key` in code-unit order, so connection lines precede timber lines.
- **Coverage:** the §8.1 rule applies to every emitted line. A book that prices only timber is `partial` once connection lines exist, with `grand_total_minor: null` and `COST_INPUTS_MISSING`. Unpriced lines are never 0 (AC2-06).
- **Same revision:** quantities come from the timber schedule for the **same** `source_revision_id`. If the schedule is not `CURRENT`, the estimate is `STALE` or `QUEUED`, not a fabricated quantity.
- **`assumptions`:** a copy of the schedule's list (§7), so the reader of a per-piece total sees that joints without a junction class are not counted (D059).
- **Large amounts:** an amount outside ±(2⁵³ − 1) fails the payload's validation, and the estimate is `FAILED` with `DERIVATION_FAILED`.

### 8.2 Price book

Approved from [EST-001](../implementation/tasks/EST-001.md) §5, §7 item 4:

- **Book-level metadata:** a project's price book carries `currency`, `as_of` (ISO date), `source`, and `geography` once for the whole book. Rows are `{key, unit, unit_price_minor}`, with `key` as `timber.<ROLE>.<nominal_label>` (unique labels, D049) or `connection.<TYPE>`, keys unique, and `unit_price_minor` a non-negative integer within ±(2⁵³ − 1). In VS-01, `currency` must be `USD`.
- **Units** ([ART-002](../implementation/tasks/ART-002.md) §7.3): `unit` is `m` or `each`. A `timber.` key needs `m` (price per meter) and a `connection.` key needs `each` (price per piece). A mismatch is rejected with `PRICE_UNIT_MISMATCH` at `rows[k].unit`, with `related_paths` `["rows[k].key"]` and the unit as `value`, because it would otherwise misprice a line or silently drop a price. Keys of other families take either unit, and are unused.
- **In the payload:** the book-level fields, `price_book_id`, and `price_book_version` are copied onto the estimate payload's `price_book`, and the estimate fingerprint includes `price_book_id`, `price_book_version`, `as_of`, and `currency` (§2.3).
- **Versions:** books are versioned per project and append-only. Setting a book creates version n+1 and keeps a stable `price_book_id`. Clearing a book is not supported in VS-01.
- **Outside the model:** setting a book is not a model command and creates no revision. It makes only the head's `preliminary_estimate` `STALE`, which is then recomputed on read; the other artifacts are unaffected.
- **Unused rows:** rows whose key matches no line item are ignored and listed in a `PRICE_ROWS_UNUSED` warning, not rejected. That includes a `connection.` row for a type with no connections, so switching a class's type (`SetConnectionType`) can turn a priced line into an unused row and a new unpriced line.
- **Validation:** invalid books are rejected with D035 codes and paths relative to the book: shape and type errors first, then `DUPLICATE_PRICE_KEY` for repeated row keys and `PRICE_UNIT_MISMATCH` (both stage 2, reported together), then `OUT_OF_RANGE` for negative prices ([EST-001](../implementation/tasks/EST-001.md) §8).

If coverage is `none` or `partial`, include warning code `COST_INPUTS_MISSING`.

### 8.3 VS-02b: wall lines and `m2` rows ([ART-003](../implementation/tasks/ART-003.md) §7; not yet implemented)

`generator_version` moves to `3`.

- **`assembly` lines:** one per `layer_aggregates` row of the assembly schedule, fill included (D082), key `assembly.<label>.<layer>`, with `assembly_label`, `layer`, `layer_function`, `material_name`, and the area as `quantity_value` in `m2`.
- **`wallframing` lines:** one per `framing_aggregates` row, key `wallframing.<piece_kind>.<nominal_section>`, with `piece_kind`, `nominal_section`, `count`, and the total length as `quantity_value` in `m`.
- **Inputs:** the estimate depends on `timber_schedule` and `assembly_schedule`; either not `CURRENT` makes it `FAILED` with `UPSTREAM_NOT_CURRENT`. Its `assumptions` are the timber schedule's list, then the assembly schedule's.
- **Price books:** `unit` gains `m2`. `assembly.` keys need `m2` and `wallframing.` keys `m`; a mismatch is `PRICE_UNIT_MISMATCH`, as for the other families. Rows for the family not in use are named in `PRICE_ROWS_UNUSED`.
- **Reference House 001 v3:** 16 lines with straw bale, 21 with stud infill. Openings are not priced (D070).

## 9. HTTP details

| Request | Behavior |
|---|---|
| `GET …/artifacts?revision_id=` | Manifest of all four types (five with VS-02b's `assembly_schedule`; not yet implemented) |
| `GET …/artifacts/{type}?revision_id=` | Envelope + payload when `CURRENT` or `UNAVAILABLE` |
| Unknown `{type}` | 404 |
| Unknown revision | 404 |
| Derivation in flight | 202 + envelope, `payload` omitted |

Do not return another revision’s payload with `status: CURRENT` for a newer head.

## 10. Acceptance tests (additions to VS-01)

These hold against Reference House 001 v2 (AC2-05), with its counts:

1. Reference House 001 manifest lists exactly `plan2d`, `mesh3d`, `timber_schedule`, `preliminary_estimate`.
2. Plan width/depth `value_m` and mesh envelope footprint match the semantic footprint within 1e-6 m.
3. Plan member IDs, mesh `members`, and schedule `members` are the same 193 IDs as the snapshot inventory.
4. Schedule aggregates match §7; estimate with default (no book) is `UNAVAILABLE`, `grand_total_minor` null, not `0`.
5. After `SetFootprintDimensions`, artifacts for the old head are not served as `CURRENT` for the new head; new plan/mesh/schedule fingerprints differ.
6. 2D and 3D clients refuse to composite views with mismatched `source_revision_id`.
7. Every `CURRENT` envelope has `suitability: "preliminary"` and `claims.structurally_verified === false`.
8. Estimate `line_items` quantities match schedule aggregates for the same revision: timber lines the role and section totals, connection lines the per-type sums of `connection_aggregates`.

Version 2 reconciliation ([ART-002](../implementation/tasks/ART-002.md) §13; checked after every step of the integration suite). These are VS-02 checks, traced as `ART2-1` to `ART2-3` in [vs-02-traceability.md](../implementation/acceptance-tests/vs-02-traceability.md) (TEST-002), not rows of the VS-01 matrix:

- Plan markers, mesh markers, and schedule connection rows are exactly the snapshot's 312 connections, with their IDs, keys, classes, and types. Mesh `location_m` is bit-identical to the record's, plan `xy_m` is its projection, and each plan marker is on its entering member's plane.
- `connection_aggregates` counts sum to the number of connection rows and of `Connection` records, and each class's count equals CONN-001 §6's formula.
- The estimate's `assumptions` equal its schedule's, and no payload carries a capacity, size, or fastener field.

**VS-02b interim (MODEL-006 §10):** model schema version 3 adds walls, wall framing, and openings, but no payload reads them yet. The four payloads are unchanged in shape and content for the v3 house (their fingerprints change with the model schema version), and `SetWallAssembly`, `AddOpening`, `SetOpening`, and `RemoveOpening` impact no artifact. `ART-003` adds the assembly schedule, walls in `plan2d` and `mesh3d`, estimate lines, and their selectors. **Approved to end with ART-003 (not yet implemented):** the five payloads of §1 then present walls, openings, and wall framing, the four wall commands impact the artifacts whose payloads they change (ART-003 §8.3), and every step of the integration suite reconciles the views' and the assembly schedule's walls, openings, and pieces with the snapshot by ID, the areas and aggregates with their rows, and the estimate's wall quantities with the aggregates.

## 11. Out of scope

glTF/IFC/DXF download, triangle buffers as the interchange format, cost databases, embodied carbon, drawing sheets, dimension styles, and kernel B-rep. Changing those requires a new document; it does not silently extend these DTOs.
