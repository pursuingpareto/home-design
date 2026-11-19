# VS-01 derived artifacts — DTO specification

**Version:** 0.2 draft (2026-11-16)  
**Status:** Confirmed for VS-01 ([D027](../product/decisions/D027-vs01-artifact-dtos.md)). Payloads are display and reporting views, not the authoritative building model and not construction documents.  
**Related:** [building model](building-model.md), [dependencies](dependencies.md), [interfaces](interfaces.md), [geometry](geometry.md), [D025](../product/decisions/D025-reference-house-001-vs01-fixture.md), [D026](../product/decisions/D026-canonical-units-identity-persistence.md).

## 1. Artifact types

Stable `artifact_type` keys, used in URLs, manifests, previews, and dependency nodes:

| `artifact_type` | Owner module | VS-01 purpose |
|---|---|---|
| `plan2d` | `geometry` | Plan display geometry and explicit dimensions |
| `mesh3d` | `geometry` | Display primitives for interactive 3D (not a CAD kernel) |
| `timber_schedule` | `timber` | Member inventory, reference-axis lengths, aggregates |
| `preliminary_estimate` | `estimating` | Quantity-based cost only when dated unit prices exist |

No other artifact types are required for VS-01. Do not emit empty analysis, IFC, or approval artifacts.

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
  "generator_version": "1",
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
| `CURRENT` | Fingerprint matches the inputs for `source_revision_id` | 200 with `payload` |
| `FAILED` | Derivation failed; semantic model unchanged | 200 envelope with `error`; or 503 if the failure is a dependency outage. Never invent geometry or totals |
| `STALE` | Newer applicable inputs exist for this project head | Never returned as the current artifact for head. Manifest may list `STALE` |
| `UNAVAILABLE` | Inputs insufficient (VS-01: no unit prices for the estimate) | 200 envelope, `payload` may list unpriced quantities; no grand total |
| `SUPERSEDED` | A newer computation finished; this result must not be published | Not served |

`CURRENT` requires `input_fingerprint` to match the latest applicable inputs **for that artifact**. Matching `source_revision_id` alone is not enough when price books or generator versions differ.

### 2.2 Suitability (AC-08)

`suitability` is always `"preliminary"` in VS-01. `claims.*` are always `false`. The UI must label framing and estimates as preliminary, not verified or construction-approved. Do not omit `PRELIMINARY_UNVERIFIED`.

### 2.3 Fingerprint

`input_fingerprint` is `sha256:` plus lowercase hex of SHA-256 over the canonical input object for that generator:

- `plan2d` / `mesh3d` / `timber_schedule`: `{ "revision_id", "model_schema_version", "generator_id", "generator_version", "snapshot" }` where `snapshot` is the canonical semantic building snapshot ([D030](../product/decisions/D030-canonical-snapshot-entity-order.md): `entities` sorted by `id`), not derived meshes.
- `preliminary_estimate`: the above plus `{ "price_book_id", "price_book_version", "as_of", "currency" }` or an explicit `"price_book": null`.

**Scope in VS-01** ([ART-001](../implementation/tasks/ART-001.md) §8, item 3): the input object includes `revision_id` and the whole snapshot, so a fingerprint never matches across revisions, and every revision derives its artifacts afresh. Per-artifact input selectors, where each artifact hashes only the fields it reads, are deferred. This is the intended VS-01 behavior, not a gap.

Canonical bytes: RFC 8785 JSON Canonicalization Scheme, UTF-8 ([D029](../product/decisions/D029-canonical-json-rfc8785.md)). Object keys are ordered by JCS, arrays keep their documented order, and `null` is preserved. Do not include derived artifacts in the hashed snapshot.

### 2.4 Coordinates and units

Payload geometry uses D026: meters, +X east, +Y north, +Z up, radians. Display conversion to feet-inches is a UI concern. Payloads include `"units": "m"` (or a units object on the schedule/estimate). Measurements in the plan are explicit `value_m` fields, never pixel lengths.

## 3. Manifest

`GET /api/v1/projects/{id}/artifacts?revision_id={rev}`

`revision_id` omitted means project head. Response: envelope-like records **without** `payload`, plus a top-level `head` flag for the requested revision.

```json
{
  "project_id": "17ac32e0-0b3b-518e-b568-adf98f41bcd0",
  "revision_id": "01b311c6-7a51-528d-befe-b2e592819b66",
  "head": true,
  "artifacts": [
    {"artifact_type": "plan2d", "status": "CURRENT", "source_revision_id": "01b311c6-7a51-528d-befe-b2e592819b66", "generator_version": "1", "input_fingerprint": "sha256:…"},
    {"artifact_type": "mesh3d", "status": "COMPUTING", "source_revision_id": "01b311c6-7a51-528d-befe-b2e592819b66", "generator_version": "1", "input_fingerprint": null},
    {"artifact_type": "timber_schedule", "status": "CURRENT", "source_revision_id": "01b311c6-7a51-528d-befe-b2e592819b66", "generator_version": "1", "input_fingerprint": "sha256:…"},
    {"artifact_type": "preliminary_estimate", "status": "UNAVAILABLE", "source_revision_id": "01b311c6-7a51-528d-befe-b2e592819b66", "generator_version": "1", "input_fingerprint": "sha256:…"}
  ]
}
```

All four types appear on every VS-01 revision manifest. Commit responses use the same four keys in `artifact_statuses` (status only; no payload).

## 4. View consistency (AC-01, AC-02, AC-07)

The browser may render 2D and 3D together only when `plan2d` and `mesh3d` share the same `source_revision_id` and both are `CURRENT`. If either is `COMPUTING`, `STALE`, or `FAILED`, the UI must show that status and must not pair a current view with a previous revision’s geometry.

Historical `GET` with an explicit `revision_id` returns the artifact **for that revision**. That payload may be `CURRENT` for the requested revision after head has moved; it must not be labeled as the live project head, and its envelope carries `head: false`.

## 5. `plan2d` payload

`generator_id`: `plan2d-vs01`. `generator_version`: `1`.

```json
{
  "units": "m",
  "planes": [
    {
      "plane_id": "level-0",
      "level_id": "bb53ff6a-c109-5f1a-a6fb-e16fd8d7f4ed",
      "z_m": 0.0,
      "posts": [
        {
          "member_id": "…",
          "generation_key": "frame/x0/y0/level-0/post",
          "xy_m": [0.0, 0.0],
          "section_id": "…"
        }
      ],
      "beams": []
    },
    {
      "plane_id": "level-1",
      "level_id": "85281672-fc1f-5723-a2e1-f85e25b1d336",
      "z_m": 3.048,
      "posts": [],
      "beams": [
        {
          "member_id": "…",
          "generation_key": "frame/axis-x/y0/x0-x1/plane-L1/beam",
          "start_xy_m": [0.0, 0.0],
          "end_xy_m": [3.6576, 0.0],
          "section_id": "…"
        }
      ]
    },
    {
      "plane_id": "eave",
      "level_id": null,
      "z_m": 5.7912,
      "posts": [],
      "beams": []
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
    "eave_ring_m": [
      [0.0, -0.6096],
      [10.9728, -0.6096],
      [10.9728, 7.9248],
      [0.0, 7.9248]
    ]
  },
  "dimensions": [
    {
      "id": "footprint-width",
      "start_m": [0.0, 0.0],
      "end_m": [10.9728, 0.0],
      "value_m": 10.9728
    },
    {
      "id": "footprint-depth",
      "start_m": [0.0, 0.0],
      "end_m": [0.0, 7.3152],
      "value_m": 7.3152
    }
  ]
}
```

Plane rules (must match `vs01-post-beam-1`):

- `level-0`: posts with `generation_key` containing `/level-0/post`; no beams.
- `level-1`: posts with `/level-1/post`; beams with `/plane-L1/`.
- `eave`: no posts; beams with `/plane-eave/`.

`footprint.ring_m` is the wall rectangle, counterclockwise from origin, **not** including eave overhang. `roof_plan.eave_ring_m` includes the 2'-0" north/south overhang (D025). Member `xy` values are reference-axis projections.

Further rules ([GEOM-001](../implementation/tasks/GEOM-001.md) §3, approved as §7 item 4):

- **Ordering:** within each plane, `posts` and `beams` are each sorted by `generation_key`.
- **Positions:** a post's `xy_m` is its `start_m` x and y. A beam's `start_xy_m` and `end_xy_m` are the plan projections of its `start_m` and `end_m`.
- **Roof plan:** the ridge runs along X at `y = origin_y + depth_m / 2`, from `origin_x` to `origin_x + width_m`. The eave ring extends `eave_overhang_m` to the north and south only. There is **no rake (gable-end) overhang** in VS-01.

`dimensions` contains **exactly** `footprint-width` and `footprint-depth`, with `value_m` copied from the footprint, never measured from rendered geometry (AC-01). Bay and grid dimension lines are not part of VS-01.

## 6. `mesh3d` payload

`generator_id`: `mesh3d-vs01`. `generator_version`: `1`.

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

Box orientation:

- Member axis is `axis_start_m` → `axis_end_m` (same as semantic `start_m` / `end_m`).
- Beams: `section_depth_m` is **vertical** (world +Z); `section_width_m` is horizontal and perpendicular to the plan projection of the axis.
- Posts: square section; `section_width_m` along +X, `section_depth_m` along +Y.

`members` order: `generation_key` ascending. Count and IDs must match the semantic inventory. Envelope numbers for Reference House 001 must match D025 (ridge `z = 8.5344 m`).

Roof surfaces ([D048](../product/decisions/D048-roof-plane-through-wall-line.md)): each plane passes through the wall line at `z_eave_m` at `pitch_rad`, so the overhang edge is at `z_eave − eave_overhang_m · tan(pitch_rad)` (5.334 m for Reference House 001) and the ridge at `z_eave + (depth_m / 2) · tan(pitch_rad)` (8.5344 m). `z_eave_m` stays the eave plate height.

## 7. `timber_schedule` payload

`generator_id`: `schedule-vs01`. `generator_version`: `1`.

```json
{
  "units": { "length": "m", "count": "1" },
  "length_basis": "reference_axis",
  "assumptions": [
    {
      "code": "REFERENCE_AXIS_LENGTH",
      "message": "Lengths are reference-axis distances, not fabrication cut lengths."
    },
    {
      "code": "NO_CONNECTIONS",
      "message": "Joinery and machining are not included."
    }
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
    { "role": "BEAM", "nominal_section": "8x12", "count": 34, "total_length_m": 124.3584 },
    { "role": "POST", "nominal_section": "8x8", "count": 24, "total_length_m": 69.4944 }
  ]
}
```

Invariants:

- `members` sorted by `generation_key`. One row per semantic `TimberMember`. `quantity` is 1.
- `length_m` is the Euclidean length of `start_m`–`end_m`, computed as `sqrt(dx*dx + dy*dy + dz*dz)` with `d = end_m − start_m`, evaluated exactly as written in IEEE-754 doubles. Library `hypot`/`dist` functions are not used, because they can differ in the last bit across languages ([EST-001](../implementation/tasks/EST-001.md) §3, approved as §7 item 1). Compared with 1e-6 m.
- `sum(members.quantity)` equals inventory size; `aggregates.count` sums to the same; `aggregates.total_length_m` equals the sum of `length_m` within 1e-6 m × n.
- Exactly **one aggregate per role and section**; posts are never split by story. `count` and `total_length_m` are summed over the member rows in `generation_key` order ([EST-001](../implementation/tasks/EST-001.md) §3, approved as §7 item 2; closes C6).
- `aggregates` sorted by `role`, then `nominal_section`.
- Same snapshot + same `generator_version` yields the same IDs, keys, roles, sections, and lengths (numeric tolerance 1e-6 m).

Reference House 001 expected aggregates (D025):

| Role | Section | Count | Total (m) |
|---|---|---|---|
| BEAM | 8×12 | 34 | 124.3584 (34 × 3.6576) |
| POST | 8×8 | 24 | 69.4944 (12 × 3.048 on level 0 + 12 × 2.7432 on level 1; informational breakdown, not separate rows) |

## 8. `preliminary_estimate` payload

`generator_id`: `estimate-vs01`. `generator_version`: `1`.

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

- **Line amounts:** `amount_minor` is `unit_price_minor × quantity_value`, multiplied **exactly**, using the double's exact binary value in decimal arithmetic. It is then rounded once to an integer with **round-half-even**.
- **Totals:** `priced_amount_minor` and `grand_total_minor` are sums of the rounded line amounts, so totals always equal the visible lines.
- **Reproducible:** the rule gives the same result in any language with exact decimal or big-integer arithmetic (for example Python `Decimal`, ECMAScript `BigInt`). It never uses binary floating-point rounding.

```json
{
  "coverage": "none",
  "currency": null,
  "price_book": null,
  "line_items": [
    {
      "key": "timber.POST.8x8",
      "role": "POST",
      "nominal_section": "8x8",
      "quantity_value": 69.4944,
      "quantity_unit": "m",
      "unit_price_minor": null,
      "amount_minor": null,
      "priced": false
    },
    {
      "key": "timber.BEAM.8x12",
      "role": "BEAM",
      "nominal_section": "8x12",
      "quantity_value": 124.3584,
      "quantity_unit": "m",
      "unit_price_minor": null,
      "amount_minor": null,
      "priced": false
    }
  ],
  "totals": {
    "priced_amount_minor": null,
    "unpriced_line_count": 2,
    "grand_total_minor": null
  }
}
```

Line items are aggregated by `role` + `nominal_section`, sorted by `key`. Quantities come from the timber schedule for the **same** `source_revision_id`. If the schedule is not `CURRENT`, the estimate is `STALE` or `QUEUED`, not a fabricated quantity.

### 8.2 Price book

Approved from [EST-001](../implementation/tasks/EST-001.md) §5, §7 item 4:

- **Book-level metadata:** a project's price book carries `currency`, `as_of` (ISO date), `source`, and `geography` once for the whole book. Rows are `{key, unit: "m", unit_price_minor}`, with `key` as `timber.<ROLE>.<nominal_label>` (unique labels, D049), keys unique, and `unit_price_minor` a non-negative integer within ±(2⁵³ − 1). In VS-01, `currency` must be `USD`.
- **In the payload:** the book-level fields, `price_book_id`, and `price_book_version` are copied onto the estimate payload's `price_book`, and the estimate fingerprint includes `price_book_id`, `price_book_version`, `as_of`, and `currency` (§2.3).
- **Versions:** books are versioned per project and append-only. Setting a book creates version n+1 and keeps a stable `price_book_id`. Clearing a book is not supported in VS-01.
- **Outside the model:** setting a book is not a model command and creates no revision. It makes only the head's `preliminary_estimate` `STALE`, which is then recomputed on read; the other artifacts are unaffected.
- **Unused rows:** rows whose key matches no line item are ignored and listed in a warning, not rejected.

If coverage is `none` or `partial`, include warning code `COST_INPUTS_MISSING`.

## 9. HTTP details

| Request | Behavior |
|---|---|
| `GET …/artifacts?revision_id=` | Manifest of all four types |
| `GET …/artifacts/{type}?revision_id=` | Envelope + payload when `CURRENT` or `UNAVAILABLE` |
| Unknown `{type}` | 404 |
| Unknown revision | 404 |
| Derivation in flight | 202 + envelope, `payload` omitted |

Do not return another revision’s payload with `status: CURRENT` for a newer head.

## 10. Acceptance tests (additions to VS-01)

1. Reference House 001 manifest lists exactly `plan2d`, `mesh3d`, `timber_schedule`, `preliminary_estimate`.
2. Plan width/depth `value_m` and mesh envelope footprint match the semantic footprint within 1e-6 m.
3. Plan member IDs, mesh `members`, and schedule `members` are the same 58 IDs as the snapshot inventory.
4. Schedule aggregates match §7; estimate with default (no book) is `UNAVAILABLE`, `grand_total_minor` null, not `0`.
5. After `SetFootprintDimensions`, artifacts for the old head are not served as `CURRENT` for the new head; new plan/mesh/schedule fingerprints differ.
6. 2D and 3D clients refuse to composite views with mismatched `source_revision_id`.
7. Every `CURRENT` envelope has `suitability: "preliminary"` and `claims.structurally_verified === false`.
8. Estimate `line_items` quantities match schedule aggregates for the same revision.

## 11. Out of scope

glTF/IFC/DXF download, triangle buffers as the interchange format, cost databases, embodied carbon, drawing sheets, dimension styles, and kernel B-rep. Changing those requires a new document; it does not silently extend these DTOs.
