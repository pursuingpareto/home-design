# MODEL-006 — Model schema version 3: assemblies, walls, wall framing, and openings

**Status:** Done (2026-11-22), merged together with [ASM-001](ASM-001.md); implementation notes in §15. All five judgment items were approved as recommended ([D073](../../product/decisions/D073-vs02b-wall-system-record.md)–[D077](../../product/decisions/D077-vs02b-definition-supported-ranges.md)), and routine items 6–13 together (§13), on 2026-11-21. The contracts are recorded in building-model.md §3.4, §6, §6.1, and §8, interfaces.md §2–3, and dependencies.md §4.1.  
**Refined by:** [D079](../../product/decisions/D079-vs02b-no-stacked-openings.md) (2026-11-22, from [ASM-001](ASM-001.md) §13 item 2): `OPENINGS_OVERLAP` compares framed ranges along the wall only (§5.2).  
**Owner module:** `model` (schema, validation, commands); `assemblies` (new package: the wall-rule registry and its interface, §7); `project` for the stored-data guard (§9.3)  
**Slice:** VS-02b ([vs-02b.md](../acceptance-tests/vs-02b.md), agreed 2026-11-21)  
**Depends on:** VS-02 (complete). Specified before `ASM-001`, but **merged together with it** on one branch (§10), as MODEL-005 and TIMBER-002 were.  
**Unblocks:** `ASM-001` (the wall rule fills the shapes defined here), then `ART-003`, `UI-004`, `TEST-003`

## 1. Objective and user-visible behavior

Define the version 3 semantic model that every other VS-02b task builds on, and retire version 2 ([D055](../../product/decisions/D055-pre-release-schema-replacement.md)):

- **assembly definitions** with ordered layers, a framing layer, and declared property values ([D066](../../product/decisions/D066-vs02b-wall-framing.md), [D067](../../product/decisions/D067-vs02b-assembly-definitions.md), [D071](../../product/decisions/D071-vs02b-thermal-moisture-values.md));
- **walls**, generated in every perimeter bay ([D065](../../product/decisions/D065-vs02b-wall-placement.md)), and their **wall framing**, one record per piece (D066);
- **openings**, the first user-authored records ([D069](../../product/decisions/D069-vs02b-openings.md));
- the **project-wide wall assembly** ([D068](../../product/decisions/D068-vs02b-wall-assembly-choice.md));
- validation stages and detail codes for all of the above, including the **girt fit** (D066) and the **framed-opening fit** (D069);
- the commands `SetWallAssembly`, `AddOpening`, `SetOpening`, and `RemoveOpening`, and the classification table `vs02b-change-classes-1`;
- the committed `snapshot.v3.schema.json`, and rejection of version 2 snapshots and databases.

**User-visible behavior** arrives with the merge (§10): new projects are Reference House 001 v3, with 20 straw bale walls, 20 openings, and 79 buck pieces ([D072](../../product/decisions/D072-reference-house-001-v3-design-intent.md)). The API accepts the four new commands. Frame edits that would leave an opening without room are rejected. No artifact shows walls yet: that is `ART-003`, and the browser is `UI-004`.

## 2. Inputs and governing documents

- [VS-02b scope](../acceptance-tests/vs-02b.md): §6 (routine items 10–15), §15 (AC2b-01 to AC2b-04, AC2b-07 to AC2b-09), §16 (the task breakdown and "Keeping `main` green").
- Decisions:
  - [D064](../../product/decisions/D064-vs02b-slice-boundary.md)–[D072](../../product/decisions/D072-reference-house-001-v3-design-intent.md), the VS-02b decisions. D066–D069 and D071 drive this task's records and rules;
  - [D035](../../product/decisions/D035-validation-stages-detail-codes.md)–[D038](../../product/decisions/D038-field-presence-catalog-records.md) (stages, codes, paths, related paths, field presence), [D039](../../product/decisions/D039-frame-member-defaults.md) (defaults), [D041](../../product/decisions/D041-deterministic-id-minting.md)/[D042](../../product/decisions/D042-stable-grid-line-ids.md) (IDs and keys), [D044](../../product/decisions/D044-undo-to-revision.md)/[D045](../../product/decisions/D045-no-op-commits.md) (undo, no-ops), [D046](../../product/decisions/D046-conformance-validation-stage.md) (conformance), [D049](../../product/decisions/D049-unique-section-labels.md) (labels), [D055](../../product/decisions/D055-pre-release-schema-replacement.md) (replace, don't migrate), [D058](../../product/decisions/D058-datum-reference-axes.md) (datum axes, which D066 amends for wall framing only).
- [building-model.md](../../architecture/building-model.md) §3 (§3.3 is the version 2 precedent), §5, §6, §6.1, §8; [interfaces.md](../../architecture/interfaces.md) §1, §2, §3, §7.1; [dependencies.md](../../architecture/dependencies.md) §4.1.
- Precedent: [MODEL-005](MODEL-005.md) (version 2, merged with [TIMBER-002](TIMBER-002.md)); [CONN-001](CONN-001.md) §7.2 (a generated kind's preview diff).
- Existing code: `homedesign/model/schema.py`, `limits.py`, `codes.py`, `validation.py`, `commands/envelope.py`, `commands/propose.py`, `schema_export.py`; `homedesign/timber/rules/__init__.py` and `inventory.py` (the rule and conformance pattern); `homedesign/project/migrate.py` (the guard).

## 3. Scope

**In scope**

- Pydantic models for version 3 (§4), exported to `docs/architecture/schemas/snapshot.v3.schema.json` with the drift check.
- Validation stages 1–5 extended for the new records (§6), with new detail codes in `codes.py` and building-model.md §6.1, including the girt fit and the framed-opening fit (§5).
- The `assemblies` package skeleton: a wall-rule registry keyed by `WallSystem.generation_rule_version`, the rule interface, and the shared conformance comparison for walls and wall framing (§7). `ASM-001` registers the rule.
- The command pipeline for the new generated kinds: regeneration of walls and wall framing on every regenerating command, removal of openings whose wall is removed, and the preview diffs (§8.5–8.6).
- `SetWallAssembly`, `AddOpening`, `SetOpening`, `RemoveOpening`, and table `vs02b-change-classes-1` (§8).
- Retiring version 2: constants, schema file, messages, and the stored-data guard test (§9).

**Non-goals (later tasks)**

- Wall and wall-framing geometry, generation keys, section offsets, jack placement, and the rule `vs02b-walls-1` → `ASM-001`.
- The template definitions, sections, and materials; the Reference House 001 v3 fixture and template; the ECMAScript oracle → `ASM-001`.
- Payloads (`assembly_schedule`, walls in `plan2d` and `mesh3d`, estimate lines), price-book units, selectors, and the thermal figures → `ART-003`. Until then no artifact reads walls, and the new commands impact no artifact (§10).
- Browser: walls, framing, openings, the assembly selector, and the opening editor → `UI-004`.
- Traceability, the golden scenario's new commands, sequences, and budgets → `TEST-003`.
- Any upgrade path for version 2 data (D055).
- User-authored or edited definitions and layers (D067), per-wall assemblies (D068), and walls off the perimeter grid (D065).

### 3.1 The seam with `ASM-001`

| Concern | MODEL-006 | ASM-001 |
|---|---|---|
| Records | Every field, type, enum, and record version (§4) | Fills them: the fixture's values (D072) |
| Wall rule | Registry, interface, version field, generic conformance and its codes (§7) | `vs02b-walls-1`: walls, framing pieces, keys, section offsets, jack threshold, cripples, girt cuts, bucks |
| Framed-opening extents | The fit rules and their codes and paths (§5); they call the rule for each opening's framed rectangle and each wall's girt heights | Computes those rectangles and heights from D066, consistent with the pieces it generates |
| Openings under regeneration | The pipeline: openings stay with a surviving wall ID, and are removed with a removed wall (§8.5) | Keys that survive the D042 edits, so walls keep their IDs; tests of survival per edit |
| Fixture and template | `MODEL_SCHEMA_VERSION = 3`; `CreateReferenceProject` copies the non-generated records, now including openings (§9.2) | The v3 fixture by script, with a drift check; the oracle |

Since the two merge together (§10), MODEL-006's tests may use a stub rule until `vs02b-walls-1` exists on the branch, and run against the real rule before the merge.

## 4. Version 3 records

`WallSystem` ([D073](../../product/decisions/D073-vs02b-wall-system-record.md)), embedded layers ([D074](../../product/decisions/D074-vs02b-embedded-layers.md)), and the property-value fields ([D075](../../product/decisions/D075-vs02b-declared-property-values.md)) are decided. The framing sections follow [D076](../../product/decisions/D076-vs02b-framed-opening-geometry.md); the supported ranges are [D077](../../product/decisions/D077-vs02b-definition-supported-ranges.md). If an item is decided otherwise, this section changes with it.

### 4.1 Changes at a glance

| Record | Change | Record `schema_version` |
|---|---|---|
| Snapshot | `model_schema_version` becomes **3** | — |
| `Building` | Adds `wall_system_id` (§4.2) | **2** |
| `WallSystem` | New kind: the wall rule version, the project-wide default definition, and the lists of walls and openings (§4.2; [D073](../../product/decisions/D073-vs02b-wall-system-record.md)) | **1** |
| `AssemblyDefinition` | New kind, a catalog record, with its `layers` inside it (§4.3; [D074](../../product/decisions/D074-vs02b-embedded-layers.md), [D075](../../product/decisions/D075-vs02b-declared-property-values.md)) | **1** |
| `Wall` | New generated kind (§4.4) | **1** |
| `WallFramingPiece` | New generated kind, one record per piece (§4.5) | **1** |
| `Opening` | New user-authored kind (§4.6) | **1** |
| `Footprint`, `Level`, `GableRoof`, `TimberGrid`, `FrameSystem`, `TimberMember`, `Connection`, `Section`, `Material` | Unchanged | As in version 2 |

- **Record versions stay per kind** (MODEL-005 §4.1): only `Building` moves.
- **The timber frame is unchanged** (D066): `FrameSystem`, `TimberMember`, `Connection`, `vs02-frame-1`, 193 members, and 312 connections.
- **`AssemblyInstance`** (reserved in building-model.md §3.2) is not used. A `Wall` names its definition directly, as D068 has one definition for every wall.

### 4.2 `Building` and `WallSystem`

```json
{
  "id": "…", "kind": "WallSystem", "schema_version": 1,
  "generation_rule_version": "vs02b-walls-1",
  "default_assembly_definition_id": "<the straw bale definition>",
  "wall_ids": ["…"],
  "opening_ids": ["…"]
}
```

- **`Building.wall_system_id`** references the single `WallSystem`, as `frame_system_id` references the frame.
- **`generation_rule_version`** names the registered wall rule (§7), as `TimberGrid.generation_rule_version` names the frame rule.
- **`default_assembly_definition_id`** is D068's project-wide default. Every wall takes it, as members take `member_defaults` (D039).
- **`wall_ids`** lists every `Wall`, ascending by `generation_key` (D030), as `member_ids` lists members.
- **`opening_ids`** lists every `Opening`, ascending by ID. Openings have no generation key, and ID order keeps the stage 2 check independent of geometry, so two openings at one offset are reported by the fit (§5), not as an order error.
- **Why a new record** ([D073](../../product/decisions/D073-vs02b-wall-system-record.md)): the frame rule and `FrameSystem` stay untouched (D066), the wall rule gets a home for its version, and `ART-003`'s selectors have one record of wall inputs to read.

### 4.3 `AssemblyDefinition` and `Layer`

```json
{
  "id": "…", "kind": "AssemblyDefinition", "schema_version": 1,
  "family": "STUD_INFILL",
  "label": "stud-infill",
  "installation_note": "…",
  "unverified_climate_details": ["…"],
  "layers": [
    {"name": "siding", "function": "FINISH", "material_id": "…", "thickness_m": 0.01905,
     "thermal_conductivity_w_m_k": null, "thermal_resistance_m2_k_w": null, "vapor_permeance_kg_pa_s_m2": null,
     "framing": null},
    {"name": "framing", "function": "FRAMING", "material_id": "<dense-pack cellulose: the fill>", "thickness_m": 0.1397,
     "thermal_conductivity_w_m_k": null, "thermal_resistance_m2_k_w": null, "vapor_permeance_kg_pa_s_m2": null,
     "framing": {
       "type": "STUD",
       "framing_material_id": "<spruce-pine-fir>",
       "framing_thermal_conductivity_w_m_k": null,
       "stud_section_id": "<2x6>", "stud_spacing_m": 0.6096,
       "girt_count": 1, "girt_section_id": "<2x6>",
       "header_section_id": "<2x8>",
       "jack_threshold_width_m": 1.2192
     }}
  ]
}
```

| Field | Type | Meaning |
|---|---|---|
| `family` | `STRAW_BALE` \| `STUD_INFILL` | D067's two families |
| `label` | slug, `^[a-z0-9]+(-[a-z0-9]+)*$` | Unique within the project (D067). It is a token of the estimate key `assembly.<label>.<layer>` (D070), so it can contain no dot |
| `installation_note` | string | Text, not checked (D067) |
| `unverified_climate_details` | list of strings | Shown with every figure, under the unverified-climate warning (D071) |
| `layers` | non-empty list of `Layer`, exterior to interior | D067 |

**`Layer`** is an object inside its definition ([D074](../../product/decisions/D074-vs02b-embedded-layers.md)), not a separate record:

| Field | Type | Meaning |
|---|---|---|
| `name` | slug, as `label` | Unique within the definition; the `<layer>` token of the estimate key |
| `function` | `FINISH` \| `SHEATHING` \| `INSULATION` \| `FRAMING` | D067's examples. Exactly one layer is `FRAMING`, and only it has `framing` |
| `material_id` | UUID of a `Material` | The layer's material. For the framing layer, the **fill** (D071): cellulose between studs, or the bales themselves |
| `thickness_m` | number | Through the wall |
| `thermal_conductivity_w_m_k`, `thermal_resistance_m2_k_w`, `vapor_permeance_kg_pa_s_m2` | `DeclaredValue` or `null` | D071; shape is [D075](../../product/decisions/D075-vs02b-declared-property-values.md) |
| `framing` | `StudFraming`, `BuckFraming`, or `null` | Non-null exactly on the `FRAMING` layer |

**`DeclaredValue`** ([D075](../../product/decisions/D075-vs02b-declared-property-values.md)): `{"value": number, "source": string, "date": "YYYY-MM-DD", "note": string | null}`. The unit is fixed by the field name, in SI (D026): W/(m·K), m²·K/W, and kg/(Pa·s·m²). Unknown is `null`, never 0 (D071). A layer declares a conductivity **or** a resistance, not both. The framing layer declares conductivities only, because its two paths are computed from the fill's and the framing material's conductivities over the layer's thickness (D071).

**Framing** (D066, D067, D071):

| `type` | Fields | Used by |
|---|---|---|
| `STUD` | `framing_material_id`, `framing_thermal_conductivity_w_m_k`, `stud_section_id`, `stud_spacing_m`, `girt_count`, `girt_section_id` (`null` when `girt_count` is 0), `header_section_id`, `jack_threshold_width_m` | `STUD_INFILL` |
| `BUCK` | `framing_material_id`, `framing_thermal_conductivity_w_m_k`, `buck_section_id`, `girt_count` (always 0 in VS-02b, D066) | `STRAW_BALE` |

- **Sections and materials** are ordinary `Section` and `Material` records. Kings, jacks, cripples, and rough sills take the stud section, and bucks the buck section ([D076](../../product/decisions/D076-vs02b-framed-opening-geometry.md)). Section labels stay unique (D049), which `ART-003`'s `wallframing.<kind>.<section label>` key relies on.
- **Catalog record:** a definition may be unreferenced (D038). VS-02b's template has exactly two, and no command edits them (D067).

### 4.4 `Wall` (generated)

```json
{
  "id": "…", "kind": "Wall", "schema_version": 1,
  "generation_key": "…",
  "level_id": "…",
  "start_m": [0.0, 0.0, 0.0], "end_m": [3.6576, 0.0, 0.0], "height_m": 3.048,
  "assembly_definition_id": "…",
  "framing_ids": ["…"]
}
```

- **Geometry:** `start_m` and `end_m` are the wall's lower edge in its reference plane, from the start post axis to the end post axis, at the story's lower datum (D065). The start is the lower grid station (west for walls along X, south for walls along Y; D066). `height_m` is the datum-to-datum height. The reference rectangle is these three values.
- **`level_id`** is the story the wall belongs to.
- **`assembly_definition_id`** equals the `WallSystem` default (conformance, as `section_id` equals `member_defaults`).
- **`framing_ids`** lists the wall's `WallFramingPiece` records, ascending by `generation_key`. Every piece belongs to exactly one wall.
- **IDs** are minted from `"generation/" + generation_key` (D041). The key format is `ASM-001`'s, from grid-line IDs and the level (D042). Keys must be unique across members, connections, walls, and wall framing together (§6.2).

### 4.5 `WallFramingPiece` (generated)

```json
{
  "id": "…", "kind": "WallFramingPiece", "schema_version": 1,
  "generation_key": "…",
  "piece_kind": "KING",
  "opening_id": "<the opening it frames, or null>",
  "start_m": [1.3335, 0.0, 0.0], "end_m": [1.3335, 0.0, 3.048],
  "section_id": "…", "material_id": "…"
}
```

- **`piece_kind`:** `STUD`, `GIRT`, `KING`, `JACK`, `HEADER`, `ROUGH_SILL`, `CRIPPLE`, `BUCK_JAMB`, `BUCK_HEAD`, `BUCK_SILL` (D070's list).
- **`opening_id`:** the opening a piece frames (kings, jacks, headers, rough sills, cripples, and bucks); `null` for layout studs and girts, including girt pieces cut by openings.
- **Axes** lie in the wall's reference plane. Lengths are reference-axis lengths (D066). Section offsets at openings are D066's exception to D058, applied by `ASM-001`.
- **Section and material** come from the wall's definition (D066). `material_id` is the framing layer's `framing_material_id`.
- **No connection records** (D066 3e).

### 4.6 `Opening` (user-authored)

```json
{
  "id": "…", "kind": "Opening", "schema_version": 1,
  "opening_kind": "WINDOW",
  "wall_id": "…",
  "width_m": 0.9144, "height_m": 1.2192,
  "sill_height_m": 0.9144, "offset_m": 1.3716
}
```

- **Rough-opening dimensions** (D066, D069): `width_m` and `height_m`. `sill_height_m` is above the wall's lower datum, and is 0 for a door. `offset_m` is the rough opening's start edge, measured along the wall from its start post axis.
- **No generation key.** The ID is minted from the command (§8.2), and `UndoToRevision` restores it (D044).
- **Voids, not products** (D069): no unit size, frame, glazing, or hardware fields.

### 4.7 Committed schema files

- `snapshot.v2.schema.json` is replaced by **`snapshot.v3.schema.json`**. The file is named after the model schema version (MODEL-005 §4.5).
- `commands.v1.schema.json`, `artifacts.v1.schema.json`, and `openapi.v1.json` keep their names (they follow `/api/v1`) and are regenerated.
- Schema titles and messages say "model schema version 3".

## 5. Fit rules

Checked on the full candidate snapshot, like the brace fit (MODEL-005 §5.2), so an opening command, a frame edit, or `SetWallAssembly` can each be rejected (D069). ε is 1e-6 m (D026). Coordinates are wall-local: `u` along the wall from its start post axis (0) to its end post axis (`W`), and `v` up from the lower datum (0) to the upper datum (`H`).

### 5.1 The framed opening

For an opening with rough opening `[o, o + w] × [s, s + h]`, the **framed opening** is a rectangle `[u0, u1] × [v0, v1]` that `ASM-001`'s rule reports (§7):

| Definition | `u0`, `u1` | `v1` | `v0` |
|---|---|---|---|
| Stud infill, width at most the jack threshold (+ε) | `o − t`, `o + w + t` (kings) | `s + h + d` (header) | `s − t` for a window (rough sill, [D076](../../product/decisions/D076-vs02b-framed-opening-geometry.md)); `s` for a door |
| Stud infill, width above the threshold | `o − 2t`, `o + w + 2t` (jacks and kings) | `s + h + d` | as above |
| Straw bale | `o − b`, `o + w + b` (buck jambs) | `s + h + b` (buck head) | `s − b` for a window (buck sill), `s` for a door |

`t` is the stud section's in-plane thickness, `d` the header section's in-plane depth, and `b` the buck section's in-plane thickness ([D076](../../product/decisions/D076-vs02b-framed-opening-geometry.md)). A door has `s = 0` and no rough or buck sill.

Reference House 001 v3: a 3'-0" window centered in a 12' bay spans `u` from 4'-4½" to 7'-7½" in either family, and `v` up to 7'-7¼" (stud infill) or 7'-1½" (straw bale). A 5'-0" stud infill window, with jacks, spans 3'-3" to 8'-9".

### 5.2 Checks

| Check | Fails when | Code (stage 4) | `path`; `related_paths` |
|---|---|---|---|
| Inside the wall | `u0 < −ε`, `u1 > W + ε`, `v0 < −ε`, or `v1 > H + ε` | **`OPENING_OUTSIDE_WALL`** | The opening's `offset_m` (start side), `width_m` (end side), `height_m` (top), or `sill_height_m` (bottom); the footprint dimension and grid axis that set `W`, or the level fields that set `H`; the framing sections used; `WallSystem.default_assembly_definition_id` |
| Clear of the braces | With the wall's brace plane on, the framed rectangle meets a knee-brace axis in its wall, or lies in the triangle above it ([D076](../../product/decisions/D076-vs02b-framed-opening-geometry.md): the rectangle rule) | **`OPENING_CROSSES_BRACE`** | The opening's `offset_m` (start brace) or `width_m` (end brace); `parameters.knee_brace_leg_m` and the plane's flag; as above for `W`, `H`, and the definition |
| No overlap | Two framed openings in one wall overlap by more than ε along the wall (`u`), whatever their heights ([D079](../../product/decisions/D079-vs02b-no-stacked-openings.md), amending the approved "in both `u` and `v`") | **`OPENINGS_OVERLAP`** | The later opening's `offset_m` (by ID order); the earlier opening's `offset_m` |
| Girts below the braces | With the wall's brace plane on and `girt_count = n > 0`, the top girt `H · n / (n + 1)` is not below the brace feet `H − L` by more than ε | **`GIRT_CROSSES_BRACE`** | The definition's `layers[k].framing.girt_count`; the level's story height, `parameters.knee_brace_leg_m`, the plane's flag, and `WallSystem.default_assembly_definition_id`. Reported once per definition and level, not per wall |

- **Which brace plane:** Level 0 walls lie under the `plane-L1` braces (`knee_braces_level_1`), and Level 1 walls under the `plane-eave` braces (`knee_braces_eave`). Each wall has one brace at each top corner, from `(0, H − L)` to `(L, H)` and from `(W, H − L)` to `(W − L, H)`.
- **Only walls as generated:** the checks use each wall's definition, so stud infill's girts are not checked while every wall is straw bale.
- **Argument links** follow interfaces.md §7.1: an `args.…` path is added when a failing field was set by the command. A width change that leaves no room for a window therefore names the opening's `offset_m` or `width_m`, the footprint's `width_m`, and `args.width_m`. That is D069's "naming the opening and the edited field".
- **Equality is accepted** where a check reads "beyond ε": a framed opening may touch a post axis, a datum, or another framed opening.
- **The girt edge case:** with one girt, the girt fit fails exactly when `L ≥ H/2` (−ε). The bounds allow `L = 4'-0"` with `H = 8'-0"`, so that pair is rejected while stud infill is used. A test pins it.
- **Not checked:** clearance to member faces (D069; an assumption line in `ART-003` says so).

## 6. Validation

The five stages and their top-level codes are unchanged (building-model.md §6). This section lists only what version 3 adds.

### 6.1 Stage 1 — syntactic

- `model_schema_version` must be 3; anything else is `UNSUPPORTED_SCHEMA_VERSION`. Record versions are checked per kind (§4.1).
- `WallSystem`, `AssemblyDefinition`, `Wall`, `WallFramingPiece`, and `Opening` are known kinds. New enums report `INVALID_ENUM`. `girt_count` is an integer (`INTEGER_OUT_OF_RANGE` for 1.5).
- `Layer`, `DeclaredValue`, and both framing shapes are strict objects: `MISSING_FIELD` and `UNKNOWN_FIELD`. The framing shape is chosen by `type`.
- `label` and `name` must match the slug pattern: **`INVALID_SLUG`** (new).
- `DeclaredValue.date` must be an RFC 3339 full date (`YYYY-MM-DD`): **`INVALID_DATE`** (new).

### 6.2 Stage 2 — referential

| Check | Code | Path, related paths |
|---|---|---|
| `Building.wall_system_id` resolves to a `WallSystem`; `default_assembly_definition_id` to an `AssemblyDefinition`; `Wall.level_id` to a `Level`; `Opening.wall_id` to a `Wall`; `WallFramingPiece.opening_id`, when set, to an `Opening`; every section and material ID to its kind | `DANGLING_REFERENCE`, `WRONG_REFERENCE_KIND` (existing) | the referencing field |
| A `WallSystem` not referenced by the building | `UNREFERENCED_ENTITY` (existing) | the record |
| `wall_ids` is exactly the set of `Wall` records | **`WALL_SET_MISMATCH`** (new) | `wall_ids`; related: unlisted records |
| `opening_ids` is exactly the set of `Opening` records | **`OPENING_SET_MISMATCH`** (new) | `opening_ids`; related: unlisted records |
| Every `WallFramingPiece` is listed by exactly one wall | **`FRAMING_SET_MISMATCH`** (new) | the wall's `framing_ids` (a piece listed twice: the later wall's, by ID); related: the piece |
| `wall_ids` and each `framing_ids` ascend by `generation_key`; `opening_ids` ascend by ID | `ORDER_VIOLATION` (existing) | the list |
| `generation_key` is unique across members, connections, walls, and wall framing | `DUPLICATE_GENERATION_KEY` (existing, widened) | the later record's key; related: the first's |
| `AssemblyDefinition.label` is unique | **`DUPLICATE_ASSEMBLY_LABEL`** (new) | the later definition's `label`, by ID; related: the first's |
| `Layer.name` is unique within its definition | **`DUPLICATE_LAYER_NAME`** (new) | `layers[k].name`; related: the first layer's |

Unlisted walls, openings, and pieces are reported once, by the set-mismatch code, as MODEL-005's implementation does for members (MODEL-005 §14).

### 6.3 Stage 3 — geometric

- `OUT_OF_RANGE` (existing) for: `thickness_m`, `stud_spacing_m`, `width_m`, and `height_m` not > 0; `girt_count`, `jack_threshold_width_m`, `sill_height_m`, and `offset_m` negative; a declared conductivity or resistance not > 0, or a permeance negative (0 is a perfect vapor barrier); `Wall.height_m` not > 0.
- **`ZERO_LENGTH_MEMBER`** is widened to wall framing pieces (axis length ≤ 1e-6 m), and `Wall` start and end closer than 1e-6 m. The code keeps its name (D035: renaming needs a decision); its meaning reads "member or piece".

### 6.4 Stage 4 — domain

- **Definitions:** exactly one layer is `FRAMING`, and only it has `framing`: **`FRAMING_LAYER_COUNT`** (new) at `layers`. `STUD_INFILL` needs `STUD` framing and `STRAW_BALE` needs `BUCK` framing; a `BUCK` `girt_count` other than 0, a `STUD` `girt_section_id` that is `null` while `girt_count > 0`, a layer declaring both a conductivity and a resistance, and a framing layer declaring a resistance are each `UNSUPPORTED_VALUE`.
- **Supported ranges** for definition values ([D077](../../product/decisions/D077-vs02b-definition-supported-ranges.md)): stud spacing 0.3048–1.2192 m and girt count 0–4, `OUT_OF_SUPPORTED_RANGE` at the `framing` field.
- **Openings:** a door with `sill_height_m` other than 0 is `UNSUPPORTED_VALUE`. The fit rules of §5.
- **Wall rule:** `WallSystem.generation_rule_version` must be registered (§7): `UNSUPPORTED_VALUE`, as for the frame rule.

### 6.5 Stage 5 — conformance

Walls and wall framing join members and connections in conformance (D046). Walls are compared only once members and connections conform, and framing only once walls conform, as connections wait for members (MODEL-005 §14).

| Code (new) | Meaning | Path |
|---|---|---|
| `MISSING_GENERATED_WALL` | The rule generates a wall key that no record has | `WallSystem.wall_ids`; `value` is the key |
| `UNEXPECTED_WALL` | A wall's key is not generated by the rule | its `generation_key` |
| `WALL_GEOMETRY_MISMATCH` | `start_m`, `end_m`, or `height_m` differs from the rule by more than 1e-6 m | that field |
| `WALL_ASSIGNMENT_MISMATCH` | `level_id` or `assembly_definition_id` differs from the rule | that field; for the definition, related: `default_assembly_definition_id` |
| `MISSING_GENERATED_FRAMING` | The rule generates a piece key that no record has | the wall's `framing_ids`; `value` is the key |
| `UNEXPECTED_FRAMING` | A piece's key is not generated by the rule | its `generation_key` |
| `FRAMING_GEOMETRY_MISMATCH` | `start_m` or `end_m` differs from the rule by more than 1e-6 m in any coordinate | that field |
| `FRAMING_ASSIGNMENT_MISMATCH` | `piece_kind`, `opening_id`, `section_id`, `material_id`, or the owning wall differs from the rule | that field; for section and material, related: the definition's framing field |

Openings are user-authored, so they have no conformance; their fit is stage 4.

## 7. The wall-rule interface (`assemblies`)

- **Registry:** `homedesign/assemblies/rules/__init__.py`, keyed by `WallSystem.generation_rule_version`, with `register`, `get_wall_rule`, and `registered_versions`, as the timber registry is. Model validation reaches the rule only through it, and the model module holds no rule logic (interfaces.md §1).
- **Interface** (illustrative):

```python
@dataclass(frozen=True)
class WallRule:
    version: str
    # Defined for snapshots passing stages 1-3; sorted by generation_key; no IDs.
    generate_walls: Callable[[Snapshot], tuple[GeneratedWall, ...]]
    # Pieces for every wall and opening, each naming its wall's key and its opening's ID.
    generate_framing: Callable[[Snapshot], tuple[GeneratedFramingPiece, ...]]
    # §5: each opening's framed rectangle in its wall's (u, v), and each wall's girt heights.
    framed_openings: Callable[[Snapshot], Mapping[str, Rect]]
    girt_heights: Callable[[Snapshot], Mapping[str, tuple[float, ...]]]

    def conformance(self, snapshot: Snapshot) -> list[ConformanceIssue]: ...
```

- **Shared comparison:** `assemblies/inventory.py` compares expected and actual walls and pieces and emits the §6.5 codes, as `timber/inventory.py` does for members and connections.
- **`ASM-001`** registers `vs02b-walls-1` and makes `framed_openings` agree with the pieces it generates: every piece that frames an opening lies within that opening's framed range along the wall, and the rectangle is the bounding box of the pieces that close it (an `ASM-001` test; restated by [ASM-001](ASM-001.md) §5.7, item 7, because kings run full height and cripples lie above and below the rectangle).

## 8. Commands and classification

### 8.1 `SetWallAssembly` (new)

| `args` | Effect |
|---|---|
| `{assembly_definition_id}` | Sets `WallSystem.default_assembly_definition_id` and regenerates walls and wall framing |

- A missing or wrong-kind ID is `DANGLING_REFERENCE` or `WRONG_REFERENCE_KIND` at `args.assembly_definition_id` (stage 2; D068).
- `args.assembly_definition_id` maps to `default_assembly_definition_id`, so a fit or girt error in the candidate carries the argument path (§5.2).
- The current value is a no-op (D045). Members and connections never change (AC2b-03).

### 8.2 `AddOpening`, `SetOpening`, `RemoveOpening` (new)

| `type` | `args` | Effect |
|---|---|---|
| `AddOpening` | `{wall_id, opening_kind, width_m, height_m, sill_height_m, offset_m}`, all required | Adds an `Opening`, ID minted with creation key `"opening"` (D041), lists it in `opening_ids`, and regenerates its wall's framing |
| `SetOpening` | `{opening_id, width_m, height_m, sill_height_m, offset_m}`, all required | Replaces one opening's dimensions and position. Its kind and wall do not change: to change them, remove it and add another |
| `RemoveOpening` | `{opening_id}` | Removes the opening and its framing |

- **Argument links:** each `args.<field>` maps to the opening's field; `args.wall_id` to its `wall_id`.
- **Errors:** an unknown wall or opening is `DANGLING_REFERENCE` (or `WRONG_REFERENCE_KIND`) at `args.wall_id` or `args.opening_id` (stage 2). A bad `opening_kind` is `INVALID_ENUM` (stage 1). Dimensions and fit are checked on the candidate (§5, §6.3–6.4).
- **No-ops:** `SetOpening` with the current values is a no-op. `AddOpening` and `RemoveOpening` never are.
- **"Position"** in D069 is read as the offset and sill height within the opening's own wall.

### 8.3 Existing commands under version 3

- **Every regenerating command** (footprint, story heights, roof, grid, frame parameters, member sections, connection types) also regenerates walls and wall framing, and is checked against §5. Their arguments and classes are unchanged.
- **`AddSection`** stays routine and regenerates nothing.
- **`CreateReferenceProject`** creates Reference House 001 v3 (§9.2).
- **`UndoToRevision`** restores walls, framing, and openings with their original IDs (D044).

### 8.4 Classification table `vs02b-change-classes-1`

Replaces `vs02-change-classes-1` in dependencies.md §4.1 (routine item 12 of vs-02b.md §6). Every preview and commit records the new version.

| Command | Class | Reason |
|---|---|---|
| `AddSection` | routine | As before |
| `AddOpening`, `SetOpening`, `RemoveOpening` | **routine** | Regenerate only their own wall's framing; no member, connection, or other wall changes (D069) |
| `SetWallAssembly` | **consequential** | Changes every wall and its framing, and the estimate, at once (D068) |
| `SetGableRoofParameters`, `SetFrameParameters`, `SetFootprintDimensions`, `SetStoryHeights`, `SetTimberGrid`, `SetMemberSection`, `SetConnectionType`, `UndoToRevision`, `CreateReferenceProject` | consequential | As in `vs02-change-classes-1` |

Routine commands may be committed without a preview, and a preview is still available (D069).

### 8.5 Regeneration pipeline

- **One regeneration** replaces members, connections, walls, and wall framing, in that order, each keeping IDs by key and minting new ones from `"generation/" + key` (D041).
- **Openings follow their wall's ID:** a wall whose key survives keeps its ID, so its openings keep their `wall_id`, offset, and size (D069). An opening whose wall is removed is removed, and dropped from `opening_ids`, before the candidate is validated. Nothing else moves or shrinks an opening.
- The pre-validation that tolerates stale conformance before regeneration (`_finish` in `propose.py`) extends to the new conformance codes.

### 8.6 Preview diff

- **`walls`** and **`wall_framing`** are added beside `members` and `connections`, with the same shape and ordering: `added` and `removed` are `{id, generation_key}` sorted by key, and `updated` lists the IDs of surviving records that changed, sorted by ID (CONN-001 §7.2). Neither kind appears in `changes`.
- **Openings appear in `changes`,** as authored records do. An opening removed with its wall is a `changes` entry with `after: null` and `field: ""`, together with the `opening_ids` change. That is D069's "the preview lists them".
- A no-op has empty lists.

## 9. Retiring version 2 (D055)

### 9.1 Code

- `MODEL_SCHEMA_VERSION = 3`, with `RECORD_SCHEMA_VERSIONS` per §4.1.
- `vs02-frame-1` stays the only frame rule. `vs02b-walls-1` (`ASM-001`) is the only wall rule.
- The D077 bounds go into `model/limits.py`, each citing its decision.

### 9.2 Template and fixture

- The fixture and packaged template become Reference House 001 v3, produced and drift-checked by `ASM-001`'s script.
- `CreateReferenceProject` copies the non-generated records (now including the wall system, the two definitions, their sections and materials, and the 20 openings) with creation keys `"template/" + fixture record ID`, then generates members, connections, walls, and framing with `"generation/" + key` (D041). Openings' `wall_id` values are rewritten to the generated walls' IDs, which are deterministic from their keys.

### 9.3 Stored data

- **Guard:** the migration runner already refuses any revision below `MODEL_SCHEMA_VERSION`, so it now refuses version 2 databases with no code change. A test pins it against a version 2 revision.
- **Reset:** `scripts/dev.sh --reset`, unchanged. The commit message tells developers to run it.

## 10. Keeping `main` green: the merge with `ASM-001`

Retiring version 2 breaks every existing test until walls are generated (vs-02b.md §16). MODEL-006 and ASM-001 are one branch and one merge, carrying the **smallest** changes elsewhere that keep CI passing:

| Area | Change in this merge | Later owner of the full change |
|---|---|---|
| Payloads | None. No artifact reads walls, framing, or openings; artifacts.md notes the gap | `ART-003` |
| `impacted_artifacts` | The four new commands impact no artifact, which is exact: no payload changes (AC2b-07) | `ART-003` adds selectors for walls |
| Golden record, UI fixture, OpenAPI, frontend `schema.d.ts` | Regenerated as reviewed diffs (D055) | `TEST-003` adds the new commands |
| Frame edits in existing tests | Some edits are now rejected by the fit rules (§5): the reference house's windows keep their offsets when a bay shrinks. Each changed outcome is listed in the merge's notes with its reason | `TEST-003` |
| Property-based sequences | Their frame edits draw more rejections. Reach is re-measured and reported; an assertion that no longer holds is reported to the product owner, not loosened silently | `TEST-003` |
| Browser | No new controls. A frame edit rejected for an opening shows its error in the editor that sent it, through the argument path; an `Opening` or `Wall` path falls back to the current tab | `UI-004` |
| Release note | `scripts/dev.sh --reset` | — |

**The golden scenario's grid step** (four 10' bays along X, after the width becomes 40') keeps the walls `x0-x1` and `x1-x2` on both long sides, with their windows still 4'-6" (3'-0" windows) or 3'-6" (5'-0" windows) from their start posts. It stays accepted under the rectangle rule ([D076](../../product/decisions/D076-vs02b-framed-opening-geometry.md)); the alternative would have rejected it.

## 11. Acceptance criteria and automated tests

Run on the merged branch, against the v3 fixture from `ASM-001`:

1. **Round trip (AC2b-01):** the v3 fixture validates, and its canonical bytes survive a parse and re-serialize.
2. **Version 2 rejected (AC2b-01):** `model_schema_version: 2` is `UNSUPPORTED_SCHEMA_VERSION`. A record with the wrong per-kind version (including `Building` at 1) is rejected at its `schema_version`. The guard refuses a database holding a version 2 revision and deletes nothing *(PostgreSQL only)*.
3. **Every new detail code** of §6 is produced by a minimal mutation of the fixture, with exact `path` and `related_paths`. So is widened `DUPLICATE_GENERATION_KEY` (a wall reusing a member's key) and widened `ZERO_LENGTH_MEMBER` (a zero-length piece).
4. **Definitions (AC2b-02):** both fixture definitions parse with every D067 field; a `DeclaredValue` with provenance validates, `null` validates, and 0 is rejected for a conductivity. Family and framing type must agree.
5. **Fit (AC2b-04):** for each §5.2 check, an opening command at the boundary is accepted (equality within ε) and just beyond it is rejected, on both families and on both sides of the jack threshold. The same failures are reached through `SetFootprintDimensions`, `SetTimberGrid`, `SetStoryHeights`, `SetFrameParameters`, and `SetWallAssembly`, with the argument in `related_paths`.
6. **Girt fit:** the `L = 4'-0"`, `H = 8'-0"` case is rejected with stud infill and accepted with straw bale; turning the brace plane off accepts it.
7. **`SetWallAssembly` (AC2b-03):** switching to stud infill and back changes only walls and wall framing; members (193) and connections (312) are unchanged; the current value is a no-op; committing without a preview is `PREVIEW_REQUIRED`.
8. **Opening commands (AC2b-04):** add, set, and remove each change exactly one opening and only its wall's framing; IDs are minted per D041; `SetOpening` with current values is a no-op; each argument's error carries its path; all three commit without a preview.
9. **Removed with the wall (AC2b-04):** a grid edit that removes a wall removes its openings, and the preview lists them in `changes` and in `wall_framing.removed`.
10. **Undo:** removing an opening and undoing restores it and its framing with their original IDs.
11. **Preview diff:** `walls` and `wall_framing` list exactly the added, removed, and updated records, in the stated orders; added IDs equal the commit's; neither kind appears in `changes`; the response validates against OpenAPI.
12. **Classification:** the table matches dependencies.md §4.1.
13. **Robustness:** never-raises property tests send random arguments to the four new commands; every accepted candidate re-validates.
14. **Schemas:** `snapshot.v3.schema.json`, the command schema, and OpenAPI are current (drift check), and this file's examples validate against them once the fixture's IDs are filled in.

## 12. Implementation guidance (not prescriptive)

- **Order on the shared branch:**
  1. schema, codes, and stages 1–4, tested against hand-built snapshots and a stub wall rule;
  2. `ASM-001`'s rule, fixture, and oracle;
  3. conformance, the pipeline, and the commands;
  4. the §10 changes;
  5. regenerated records last, so their diffs reflect the final code.
- **One pass per snapshot:** validation and regeneration each call both rules. If profiling shows it matters, compute the inventory once per snapshot.
- **Typed copies of enums:** export `PieceKind`, `OpeningKind`, and `AssemblyFamily` from the model, so `ART-003` and `UI-004` import one definition, as payloads import `MemberRole`.

## 13. Proposals for approval

**Your judgment** (one at a time, in this order):

1. ~~**Where walls and the wall default live** (§4.2): a new `WallSystem` record, referenced from `Building.wall_system_id`, holding the wall rule's version, D068's default, and the lists of walls and openings.~~ **Approved: [D073](../../product/decisions/D073-vs02b-wall-system-record.md)** (2026-11-21), as recommended. *Not adopted:* the same fields on `FrameSystem` or on `Building`.
2. ~~**Layers inside their definition** (§4.3): `layers` is a list of objects inside `AssemblyDefinition`, each with a `name` unique within the definition.~~ **Approved: [D074](../../product/decisions/D074-vs02b-embedded-layers.md)** (2026-11-21), as recommended. *Not adopted:* `Layer` as its own record kind.
3. ~~**Declared property values** (§4.3): three nullable fields per layer (`thermal_conductivity_w_m_k`, `thermal_resistance_m2_k_w`, `vapor_permeance_kg_pa_s_m2`), each a `DeclaredValue` `{value, source, date, note}`; at most one thermal field; conductivities only on the framing layer.~~ **Approved: [D075](../../product/decisions/D075-vs02b-declared-property-values.md)** (2026-11-21), as recommended. *Not adopted:* conductivity only; one provenance per layer.
4. **Framed-opening geometry** (§5.1–5.2). D069 checks the framed opening against the brace axes, but D066 makes kings full-height studs that stop at braces, so "clear of the brace axes" has two readings. Three parts, settled one at a time. **All three settled as recommended and recorded as [D076](../../product/decisions/D076-vs02b-framed-opening-geometry.md)** (2026-11-21):
   - **4a. Clearance to braces.** **Settled (2026-11-21): the rectangle rule, as recommended.** *Recommendation:* the framed opening is the rectangle from its bottom (`v0`) to the header top (`v1`), between the kings' outer faces, and must not meet either brace axis, including the triangle above it. Kings above the header may stop on a brace, like any stud (D066). This accepts windows under the braces when they are low enough. With the reference house's windows at their offsets, a bay can shrink to 8'-9" with the straw bale default (9'-4¼" with stud infill), so the golden scenario's 10' bays stay valid. *Alternative:* no part of a framed opening within a brace leg of either post, so every king is full height. Simpler to explain, but the same windows then need bays of at least 10'-7½" (the 3'-0" windows) and 11'-7½" (the 5'-0" windows), and the golden scenario's grid step (four 10' bays) is rejected.
   - **4b. The rough sill is part of a window's framed opening** in stud infill walls, as the buck sill is in straw bale walls. **Settled (2026-11-21): included, as recommended.** *Recommendation:* yes, so a window's sill must leave room for its rough sill (`s ≥ t`), and no rough sill is generated below the lower datum. D069 as written leaves it out. *Alternative:* D069 as written, with windows whose sill is under 1½" generating a rough sill below the floor datum.
   - **4c. Sections and in-plane dimensions.** D066 and D067 name only stud, girt, header, and buck sections. **Settled (2026-11-21), as recommended.** *Recommendation:* kings, jacks, cripples, and rough sills take the stud section. A piece's in-plane dimension is its section's `actual_width_m` (studs, kings, jacks, cripples, rough sills, girts, and bucks, all 1½" on the reference house), except a header's, which is its `actual_depth_m` (7¼", vertical, as D066's "the header's depth sets the cripples' lower end" requires). *Alternative:* separate sections in the framing layer for kings, jacks, and rough sills, which D067 does not list.
5. ~~**Supported ranges for definition values** (§6.4): stud spacing 12"–48" and girt count 0–4, borrowed from the joist-spacing and purlins-per-slope ranges; physical checks only for thicknesses, sections, and the jack threshold; no opening size bounds beyond > 0 and the fit.~~ **Approved: [D077](../../product/decisions/D077-vs02b-definition-supported-ranges.md)** (2026-11-21), as recommended. *Not adopted:* no supported ranges until definitions become editable.

**Routine** (they follow from D041, D042, D046, D055, D065–D070, routine items 10–15 of vs-02b.md §6, and the MODEL-005 and CONN-001 patterns). **All eight approved together (2026-11-21),** with the record shapes of D073–D075.

6. **Version 3 records** (§4): kind names `WallSystem`, `AssemblyDefinition`, `Wall`, `WallFramingPiece`, and `Opening`; `Building` at record version 2 and new kinds at 1; slugs for labels and names; `AssemblyInstance` left unused; `snapshot.v3.schema.json`.
7. **Walls and pieces as generated records** (§4.4–4.5): one record per piece, as AC2b-03's stable IDs require; geometry stored and checked in conformance, as for members; keys unique across all four generated kinds, with formats set by `ASM-001`.
8. **Openings** (§4.6): field names and meanings, `opening_ids` in ID order, no generation key.
9. **Validation** (§5.2, §6): the new codes (`INVALID_SLUG`, `INVALID_DATE`, `WALL_SET_MISMATCH`, `OPENING_SET_MISMATCH`, `FRAMING_SET_MISMATCH`, `DUPLICATE_ASSEMBLY_LABEL`, `DUPLICATE_LAYER_NAME`, `FRAMING_LAYER_COUNT`, `OPENING_OUTSIDE_WALL`, `OPENING_CROSSES_BRACE`, `OPENINGS_OVERLAP`, `GIRT_CROSSES_BRACE`, and the eight conformance codes), their paths and related paths, the ε rules, and the widened `DUPLICATE_GENERATION_KEY` and `ZERO_LENGTH_MEMBER`.
10. **The wall-rule interface** (§7, §3.1): a registry in `assemblies`, the fit computed from the rule's framed rectangles, and the seam with `ASM-001`.
11. **Commands and classification** (§8.1–8.4): the four commands' arguments, mappings, errors, and no-ops, the reading of "position", and table `vs02b-change-classes-1`.
12. **Pipeline and preview** (§8.5–8.6): one regeneration for all generated kinds, openings removed with their wall before validation, and the `walls` and `wall_framing` diffs.
13. **Retirement and merge scope** (§9–10): the version 3 constants, the unchanged guard pinned by a test, and the interim changes, with changed test outcomes reported rather than loosened.

The approved items are recorded in building-model.md (§3.4 "Version 3 records", §6, §6.1, §8), interfaces.md §2 and §3, and dependencies.md §4.1, each marked "not yet implemented"; the implementation removes the markers, moves the new codes into the §6.1 table, and adds the classification rows. The judgment items are [D073](../../product/decisions/D073-vs02b-wall-system-record.md)–[D077](../../product/decisions/D077-vs02b-definition-supported-ranges.md).

**Noted for later task files** (not MODEL-006 questions):

- **Framing-layer fill quantities (`ART-003`):** D070 quantifies the framing layer "by its pieces", and D071 makes the bales and the cellulose that layer's fill. Read together, the straw and cellulose would have no area or volume line and no `assembly.` estimate line. `ART-003` should propose a fill quantity (for example, the framing layer's net area and volume, priced per m² like other layers).
- **Template text (`ASM-001`):** D072 gives no installation notes or climate-detail lists for the two definitions. `ASM-001` should propose them; vs-02b.md §13 has examples (plaster and rain-screen detailing, bale moisture protection at the sill).

## 14. Definition of done

- All §11 tests pass on the merged MODEL-006 + ASM-001 branch, with the regenerated VS-01 and VS-02 suites, Vitest, and Playwright. `scripts/check.sh` and CI pass.
- building-model.md, interfaces.md, dependencies.md, and artifacts.md (the §10 note) are updated. The decisions for items 1–5 (D073–D077) are recorded, and the roadmap is updated.
- Changed files, tests, changed test outcomes, limitations, and next steps are summarized (AGENTS.md).

## 15. Implementation notes (2026-11-22)

Implemented on one branch with [ASM-001](ASM-001.md) (§10), in §12's order, except that the real rule replaced the stub from the start: ASM-001 specifies it fully, and its counts matched on the first run.

**Delivered:**
- `backend/src/homedesign/model/`:
  - `limits.py`: `MODEL_SCHEMA_VERSION = 3`; `Building` at record version 2 and the five new kinds at 1; the D077 bounds (`STUD_SPACING_MIN_M`, `STUD_SPACING_MAX_M`, `GIRT_COUNT_MAX`);
  - `schema.py`: `WallSystem`, `AssemblyDefinition` with embedded `Layer`, `DeclaredValue`, `StudFraming` and `BuckFraming` (discriminated by `type`), `Wall`, `WallFramingPiece`, `Opening`, and `Building.wall_system_id`. `AssemblyFamily`, `LayerFunction`, `PieceKind`, and `OpeningKind` are exported for `ART-003` and `UI-004` (§12);
  - `codes.py`: the twenty new codes, in the stage catalog;
  - `validation.py`: stages 1–5 for the new records (§6). Stage 4 checks each definition, then runs the fit (§5) from the wall rule's rectangles and girt heights, only when the default definition passed its own checks; stage 5 compares walls, then framing, once members and connections conform;
  - `commands/envelope.py`: `SetWallAssembly`, `AddOpening`, `SetOpening`, `RemoveOpening`;
  - `commands/propose.py`: table `vs02b-change-classes-1`; one regeneration for all four generated kinds, with openings removed with their wall (§8.5); the `walls` and `wall_framing` diffs (§8.6); `CreateReferenceProject` copying the openings and keeping the template's walls, with IDs minted from their keys and no framing, so that regeneration finds each opening's wall (§9.2);
  - `schema_export.py`: `snapshot.v3.schema.json` replaces `snapshot.v2.schema.json`.
- `backend/src/homedesign/assemblies/` (new): the wall-rule registry (`rules/__init__.py`), the shared comparison (`inventory.py`), and ASM-001's rule and template.
- `api/models.py`: `WallChanges` and `WallFramingChanges`, required on `PreviewResponse`.
- Regenerated, reviewed as diffs: the fixture and packaged template (651 records), the three committed schemas, `frontend/src/api/schema.d.ts`, the UI fixture, the golden record, and `vectors.json`.
- Documents: building-model.md §3, §3.4, §6, §6.1 (the new codes are rows of the table now), and §8; interfaces.md §1–3; dependencies.md §4.1 (the four rows; the heading anchor is `vs02b-change-classes-1`, and the links to it are updated); artifacts.md (the §10 interim note, before §11); D073–D077 (implemented); the backend README; the roadmap.

**Choices made during implementation** (each follows from the approved text; none changes a requirement):
- **`RemoveOpening` removes the opening's framing pieces with it** before validation, so that no piece names a removed opening. Without this the candidate fails stage 2 (`DANGLING_REFERENCE` at a piece's `opening_id`) before regeneration can run. §8.2's "removes the opening and its framing" covers it.
- **Pieces that no wall lists** are reported once, as §6.2 says, at `WallSystem.wall_ids` with the pieces in `related_paths`: §6.2 names "the wall's `framing_ids`" for a piece listed twice, but an unlisted piece has no wall. building-model.md §6.1 records the choice.
- **The owning-wall mismatch** of `FRAMING_ASSIGNMENT_MISMATCH` (a wall that lists another wall's piece) is reported at the listing wall's `framing_ids`, with the owner's `framing_ids` in `related_paths`.
- **An unknown framing `type`** is `INVALID_ENUM` at `framing.type` (it is a tag, not a record kind); a missing one is `MISSING_FIELD` there.
- **`layers` must be non-empty at stage 1** (`WRONG_TYPE`, as for other length constraints); a definition whose layers have no `FRAMING` layer is `FRAMING_LAYER_COUNT`.
- **Fit paths:** "the framing sections used" are, per side, the section that sets that edge: the stud section for `u0`, `u1`, and `v0` with stud infill, the header section for `v1`, and the buck section for every edge with straw bale. The brace check names the sections of `u` and `v1`. A start-side or brace failure also names the footprint dimension and grid axis that place the wall.
- **The brace test** is `(v1 − u0) − (H − L) > ε` at the start and `(v1 + u1) − (H − L + W) > ε` at the end: the rectangle's corner nearest each brace, which is where the rectangle first meets the brace or the triangle above it.
- **Totality:** stages 1–3 allow any positive stud spacing and any girt count, which stage 4 rejects (D077). The rule generates no layout studs beyond 1,000 positions and no girts beyond 1,000, so it stays fast on such snapshots; their output is unspecified (ASM-001 §5.6).

**Changed test outcomes (§10).** Each is listed with its reason. No assertion was loosened: where an edit is now rejected, the old assertion is kept on a house without openings (when it tests something openings do not affect) and the new outcome is asserted separately.

| Test | Before | Now | Reason |
|---|---|---|---|
| `test_mutations.py` case `29-width-inside-epsilon` (ASM-001 §10, known) | A 12'-0" − 5e-7 m footprint is accepted | Rejected on the v3 house: `OPENING_OUTSIDE_WALL` (new case `29b-…`). The D032 ε bound itself is still asserted accepted, on the house without openings | 4' bays fit no D072 window (D076) |
| `test_mutations.py` case `30-width-outside-epsilon` | Exactly one issue, `OUT_OF_SUPPORTED_RANGE` | Unchanged, now asserted on the house without openings | The same stage 4 also reports the windows that do not fit; `only=True` would fail |
| `test_mutations.py` cases `m005-braces-do-not-fit`, `m005-braces-off-need-no-fit` | Exactly the brace-fit issue; accepted with braces off | Unchanged, on the house without openings | The 5' bay fits no window |
| `test_mutations.py` case `36-unknown-kind` | `kind: "Wall"` is `UNKNOWN_KIND` | `kind: "AssemblyInstance"` is `UNKNOWN_KIND` | `Wall` is a version 3 kind; `AssemblyInstance` stays reserved and unused (§4.1) |
| `test_impact.py::test_measured_impact`, case `move y1 to 0.3` | Accepted, impacts all four | Rejected (`OPENING_OUTSIDE_WALL`, `OPENING_CROSSES_BRACE`, with `args.y_lines`); the case moved to `test_move_y1_to_0_3_is_rejected_by_the_fit`. The other four `move y1` cases keep their assertion | A 7'-2⅖" bay is below the straw bale minimum of 8'-9" (D076) |
| `test_commands.py::test_frame_parameters_no_op_and_errors` | The 2 m leg's issue is `issues[0]` | The same issue and argument link, found by path | A 2 m leg also crosses framed openings, and those issues sort first |
| `test_project.py` guard test | Version 1 database refused | Unchanged; a second test refuses a version 2 database | §9.3 |
| Counts: `test_fixture.py`, `test_connections.py` | 518 records | 651 | ASM-001 §8.1 |
| `test_commands.py`: created project equals the fixture; preview shape | — | Walls map by key, `opening_ids` compared in ID order; `walls` and `wall_framing` in the preview | §8.6, §9.2 |
| Golden record, UI fixture, vectors | — | Regenerated. The golden scenario's diff is only its 48 input fingerprints and 12 snapshot fingerprints (they include the model schema version): every step keeps its outcome, and the grid step to four 10' bays stays accepted (§10) | D055 |
| `test_sequences.py` (ASM-001 §10: story heights under 7'-1½") | — | No assertion changed. Those draws were already rejected by D034, and now also report fit issues in the same stage. The outcome gate still reaches every VS-02 outcome; reach is below | — |

**Property sequences' reach (re-measured, `ci` profile, 40 sequences each):** the outcome gate passes on v3, as on v2. Share of generated cases in which each outcome occurs, v2 → v3 (the derandomized draws diverge once an outcome differs, so these are indicative):

| Command | Accepted | Rejected |
|---|---|---|
| `SetFootprintDimensions` | 14.3% → 11.8% | 52.4% → 37.3% |
| `SetTimberGrid` | 11.1% → 17.6% | 31.7% → 35.3% |
| `SetStoryHeights` | 12.7% → 13.7% | 14.3% → 25.5% |
| `SetFrameParameters` | 22.2% → 29.4% | 9.5% → 13.7% |
| `SetGableRoofParameters` | 30.2% → 52.9% | 22.2% → 9.8% |

Every gated outcome (`impacts 0`–`4`, no-ops, both rejection codes) is still reached. The sequences do not send the four new commands yet (`TEST-003`).

Known in advance but not seen: no edit to a bay under 8'-9" occurs elsewhere in the existing suites. The e2e suite (23 tests) passes unchanged: its grid and width edits keep every bay at 8'-9" or more.

**Limitations:**
- No payload reads walls, framing, or openings, so the four commands impact no artifact (exact until `ART-003`). The browser has no wall controls (`UI-004`); a frame edit rejected for an opening shows its error in the editor that sent it, through the argument path, and an `Opening` or `WallSystem` path falls back to the current tab, with no browser change.
- The golden scenario, traceability, and sequences do not send the new commands yet (`TEST-003`).
