# GEOM-001 — `plan2d` and `mesh3d` derivations

**Status:** Ready for implementation after `ART-001` — all §7 proposals approved (2026-11-19)  
**Owner module:** `geometry`  
**Slice:** VS-01  
**Depends on:** `ART-001` (derivation registry, envelope, storage)  
**Unblocks:** `UI-001` (synchronized 2D/3D views; AC-01, AC-02)  
**Closes:** C1 (`mesh3d` roof slope; D048)

## 1. Objective and user-visible behavior

Derive the two display views of a revision: a plan with explicit dimensions, and a list of 3D display primitives. Both follow the [artifacts.md](../../architecture/artifacts.md) §5–6 DTOs ([D027](../../product/decisions/D027-vs01-artifact-dtos.md)). These views are not the model, not a CAD kernel, and not drawings. With `UI-001` they satisfy AC-01: the same dimensions appear in 2D and 3D, both derived from one revision.

## 2. Scope

**In scope**

- Pydantic models for both payloads (D028), added to an exported `docs/architecture/schemas/artifacts.v1.schema.json`. `ART-001` provides the envelope and `EST-001` adds the other two payloads.
- `plan2d-vs01` and `mesh3d-vs01` derivations registered with `ART-001`. Each is a pure function of the revision's snapshot.
- Exact numeric formulas (§4), so payloads are byte-identical across implementations, as `TIMBER-001` does for members.

**Non-goals:** rendering, tessellation, Three.js, hit-testing, dimension styles, drawing sheets, DXF/glTF/IFC export (artifacts.md §11), and bay or grid dimension lines (not required by AC-01).

## 3. Payloads

As artifacts.md §5–6, with these rules made explicit:

**`plan2d`**
- **Planes:** `level-0` (at `L0.elevation_m`), `level-1` (at `L1.elevation_m`), and `eave` (at `z_eave`). Members are assigned to planes by the key segments listed in artifacts.md §5.
- **Ordering:** within a plane, posts and beams are each sorted by `generation_key`.
- **Member positions:**
  - post `xy_m` = `start_m[0:2]`;
  - beam `start_xy_m` and `end_xy_m` = the projections of `start_m` and `end_m`.
- **Footprint ring:** counterclockwise from the origin: `[o, o+(w,0), o+(w,d), o+(0,d)]`.
- **Roof plan:**
  - the ridge runs along X at `y = origin_y + depth_m / 2`, from `x = origin_x` to `origin_x + width_m`;
  - the eave ring extends `eave_overhang_m` north and south only, with no rake overhang, matching D025.
- **Dimensions:** exactly `footprint-width` and `footprint-depth`, with `value_m` copied from the footprint, never measured from geometry.

**`mesh3d`**
- **Members:** one `oriented_box` per stored `TimberMember`, in `generation_key` order.
  - `axis_start_m` and `axis_end_m` are the member's `start_m` and `end_m`.
  - `section_width_m` and `section_depth_m` come from the member's `Section`.
  - The box is oriented as artifacts.md §6 specifies: beam depth vertical; for posts, width along X.
  - Members are taken from the **stored snapshot**, never regenerated, so the view always shows exactly what was committed.
- **Envelope:** `footprint_ring_m`, `level_z_m` = `[L0.elevation_m, L1.elevation_m]`, `z_eave_m`, and a `roof` object holding `kind`, `ridge_axis`, `pitch_rad`, the ridge endpoints, and two surfaces (`south`, `north`) with the ring vertex order shown in artifacts.md §6, so each surface's normal points outward and upward.

## 4. Numeric evaluation (approved — §7 item 2)

All values are IEEE-754 doubles evaluated exactly as written, left to right, with no fused multiply-add and no rounding (as generation-rules.md "Numeric evaluation"):

```text
t        = tan(pitch_rad)
z_eave   = L1.elevation_m + L1.story_height_m
y_ridge  = origin_y + depth_m / 2
z_ridge  = z_eave + (depth_m / 2) * t
z_edge   = z_eave - eave_overhang_m * t        # C1: the roof plane extends below z_eave over the overhang
y_south  = origin_y - eave_overhang_m
y_north  = origin_y + depth_m + eave_overhang_m
```

**`tan`:** `tan` is the platform's correctly rounded or nearly correctly rounded library function. Implementations must agree with the shared vector within 1e-12 m. Coordinates are compared with the D026 epsilon; only `tan` may differ in the last bit.

**The south surface** ring is `[(x0, y_south, z_edge), (x1, y_south, z_edge), (x1, y_ridge, z_ridge), (x0, y_ridge, z_ridge)]`, and the north surface mirrors it. Here `x0` = `origin_x` and `x1` = `origin_x + width_m`.

**For Reference House 001:** `z_ridge` = 8.5344 m (unchanged from D025), and `z_edge` = **5.334 m**. The artifacts.md §6 example has been corrected from 5.7912 m, which gave a 7.71/12 slope (C1, D048).

## 5. Acceptance criteria and automated tests

1. **Reference House 001 `plan2d`:** posts and beams per plane are 12 and 0 (`level-0`), 12 and 17 (`level-1`), and 0 and 17 (`eave`). Width and depth `value_m` equal the footprint's (artifacts.md §10, test 2). The rings and the ridge match §3.
2. **Reference House 001 `mesh3d`:** 58 boxes whose IDs are the snapshot's 58 member IDs, the same set as the plan's members (test 3). Section dimensions come from the referenced sections. The envelope footprint equals the plan footprint within 1e-6 m.
3. **Roof slope (C1):** for each surface, `(z_ridge − z_edge) / (depth/2 + overhang)` equals `tan(pitch_rad)` within 1e-9. The ridge is at 8.5344 m and the edge at 5.334 m within 1e-6 m.
4. **Width change:** after a width change, both payloads reflect the new footprint, both fingerprints differ, and the old views are never served as `CURRENT` for the new head (test 5).
5. **Section change:** after `SetMemberSection` to a new section, the mesh box dimensions change for that role only.
6. **Determinism:** identical revisions give byte-identical canonical payloads. A cross-language vector (`generate.mjs`) reproduces the Reference House 001 payloads within the §4 `tan` tolerance.
7. **Contract:** both payloads validate against the exported JSON Schema, and the schema drift check passes.

## 6. Implementation guidance (not prescriptive)

`backend/src/homedesign/geometry/`: `plan2d.py`, `mesh3d.py`, and `payloads.py` (Pydantic models), each registered with the `ART-001` registry.

## 7. Proposals approved by the product owner

1. ~~**C1 roof correction:** each roof plane passes through the wall line at `z_eave` at the confirmed pitch, so the overhang edge is at `z_eave − overhang × tan(pitch)` (5.334 m for Reference House 001), and the ridge stays at 8.5344 m.~~ **Approved: [D048](../../product/decisions/D048-roof-plane-through-wall-line.md)**; artifacts.md §6 corrected, with a note on D027.
2. ~~**Numeric evaluation** (§4): exact formulas, with a 1e-12 m tolerance only where `tan` enters.~~ **Approved**; recorded in geometry.md.
3. ~~**Members come from the stored snapshot**, not from regeneration (§3).~~ **Approved**; recorded in geometry.md.
4. ~~**Ordering and plane rules** as stated in §3, including no rake overhang and exactly two dimensions.~~ **Approved**; artifacts.md §5 updated.
