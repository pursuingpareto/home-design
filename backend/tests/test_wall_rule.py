"""Rule vs02b-walls-1, the template definitions, and Reference House 001 v3 (ASM-001 §11)."""

from __future__ import annotations

import json
import random
import re
from collections import Counter
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from conftest import FIXTURE, REPO_ROOT, VECTORS_PATH, entities_of, fresh_fixture, grid_doc, regenerate
from homedesign.assemblies import get_wall_rule, registered_versions
from homedesign.assemblies import template as wall_template
from homedesign.model import validate_value
from homedesign.model.schema import Snapshot

RULE = get_wall_rule("vs02b-walls-1")
FT, IN = 0.3048, 0.0254
EPS = 1e-6
VERTICAL = {"STUD", "KING", "JACK", "CRIPPLE", "BUCK_JAMB"}


def _snapshot(doc: dict[str, Any]) -> Snapshot:
    return Snapshot.model_validate(doc)


def _by_kind(doc: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    return entities_of(doc, kind)


def _definition(doc: dict[str, Any], label: str) -> dict[str, Any]:
    return next(d for d in _by_kind(doc, "AssemblyDefinition") if d["label"] == label)


def _framing(doc: dict[str, Any], label: str) -> dict[str, Any]:
    return next(layer["framing"] for layer in _definition(doc, label)["layers"] if layer["framing"] is not None)


def _system(doc: dict[str, Any]) -> dict[str, Any]:
    return _by_kind(doc, "WallSystem")[0]


def with_default(doc: dict[str, Any], label: str) -> dict[str, Any]:
    _system(doc)["default_assembly_definition_id"] = _definition(doc, label)["id"]
    return regenerate(doc)


def stud_doc() -> dict[str, Any]:
    return with_default(fresh_fixture(), "stud-infill")


def _valid(doc: dict[str, Any]) -> Snapshot:
    result = validate_value(doc)
    assert result.valid, result.to_dict()
    return result.snapshot


def _local(doc: dict[str, Any]):
    """Wall-local (u, v) for every piece of the doc's rule output: {key: (piece, wall, (u_start, v_start), (u_end, v_end))}."""
    inventory = RULE.build(_snapshot(doc))
    walls = {w.generation_key: w for w in inventory.walls}
    out = {}
    for piece in inventory.framing:
        wall = walls[piece.wall_key]
        ax = 0 if wall.axis == "x" else 1

        def uv(point, wall=wall, ax=ax):
            return (point[ax] - wall.start_m[ax], point[2] - wall.start_m[2])

        out[piece.generation_key] = (piece, wall, uv(piece.start_m), uv(piece.end_m))
    return inventory, out


def _sections(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {s["id"]: s for s in _by_kind(doc, "Section")}


def _in_plane(piece, sections) -> float:
    section = sections[piece.section_id]
    return section["actual_depth_m"] if piece.piece_kind == "HEADER" else section["actual_width_m"]


# --- 1, 2: inventories ----------------------------------------------------------------------


def test_fixture_inventory_is_exactly_the_rule_output():
    """AC2b-03: the fixture's 20 walls and 79 pieces are the rule's, bit for bit."""
    inventory = RULE.build(_snapshot(FIXTURE))
    walls = {w["generation_key"]: w for w in _by_kind(FIXTURE, "Wall")}
    pieces = {p["generation_key"]: p for p in _by_kind(FIXTURE, "WallFramingPiece")}
    assert len(inventory.walls) == len(walls) == 20
    assert len(inventory.framing) == len(pieces) == 79
    for w in inventory.walls:
        stored = walls[w.generation_key]
        assert stored["level_id"] == w.level_id
        assert stored["assembly_definition_id"] == w.assembly_definition_id == _definition(FIXTURE, "straw-bale")["id"]
        assert stored["start_m"] == list(w.start_m) and stored["end_m"] == list(w.end_m) and stored["height_m"] == w.height_m
        assert [pieces_id for pieces_id in stored["framing_ids"]] == [
            next(p["id"] for p in pieces.values() if p["generation_key"] == g.generation_key)
            for g in inventory.framing if g.wall_key == w.generation_key
        ]
    for g in inventory.framing:
        assert pieces[g.generation_key] | {"id": None} == {"id": None, "kind": "WallFramingPiece", "schema_version": 1, **g.to_json()}
    assert Counter(g.piece_kind for g in inventory.framing) == {"BUCK_JAMB": 40, "BUCK_HEAD": 20, "BUCK_SILL": 19}


def test_stud_infill_inventory():
    """ASM-001 §8.2: 246 pieces; 12, 16, and 10 per wall; the candidate passes every fit."""
    doc = stud_doc()
    _valid(doc)
    inventory = RULE.build(_snapshot(doc))
    assert len(inventory.framing) == 246
    assert Counter(p.piece_kind for p in inventory.framing) == {
        "STUD": 76, "GIRT": 40, "KING": 40, "JACK": 4, "HEADER": 20, "ROUGH_SILL": 19, "CRIPPLE": 47,
    }
    per_wall = Counter(p.wall_key for p in inventory.framing)
    assert sorted(Counter(per_wall.values()).items()) == [(10, 1), (12, 17), (16, 2)]
    assert per_wall["wall/axis-x/y0/x1-x2/level-0"] == 10  # the door
    assert per_wall["wall/axis-x/y0/x0-x1/level-0"] == per_wall["wall/axis-x/y0/x2-x3/level-0"] == 16


# --- 3: worked example (ASM-001 §5.8) ---------------------------------------------------------


def _wall_pieces(doc, wall_key):
    _, local = _local(doc)
    return {k[len(wall_key) + 1:]: v for k, v in local.items() if k.startswith(wall_key + "/")}


def test_worked_example_stud_infill():
    """A 3'-0" × 4'-0" window centered in a 12' Level 0 bay, with stud infill: twelve pieces."""
    key = "wall/axis-y/x0/y0-y1/level-0"
    doc = stud_doc()
    opening = next(o for o in _by_kind(doc, "Opening") if next(w for w in _by_kind(doc, "Wall") if w["id"] == o["wall_id"])["generation_key"] == key)
    oid = opening["id"]
    pieces = _wall_pieces(doc, key)
    expected = {  # u and v in inches: (u_start, v_start), (u_end, v_end)
        "stud/s1": ((24, 0), (24, 108)),
        "stud/s5": ((120, 0), (120, 108)),
        "stud/s2": ((48, 0), (48, 120)),
        "stud/s4": ((96, 0), (96, 120)),
        f"opening/{oid}/king/start": ((53.25, 0), (53.25, 120)),
        f"opening/{oid}/king/end": ((90.75, 0), (90.75, 120)),
        f"opening/{oid}/header": ((54, 87.625), (90, 87.625)),
        f"opening/{oid}/rough-sill": ((54, 35.25), (90, 35.25)),
        f"opening/{oid}/cripple/s3/above": ((72, 91.25), (72, 120)),
        f"opening/{oid}/cripple/s3/below": ((72, 0), (72, 34.5)),
        "girt/g1/start": ((0, 60), (52.5, 60)),
        f"girt/g1/after/{oid}": ((91.5, 60), (144, 60)),
    }
    assert set(pieces) == set(expected)
    for name, (start, end) in expected.items():
        _, _, got_start, got_end = pieces[name]
        for got, want in zip((*got_start, *got_end), (*start, *end)):
            assert got == pytest.approx(want * IN, abs=1e-9), name
    rect = RULE.framed_openings(_snapshot(doc))[oid]
    assert (rect.u0, rect.u1, rect.v0, rect.v1) == pytest.approx((52.5 * IN, 91.5 * IN, 34.5 * IN, 91.25 * IN), abs=1e-9)


def test_worked_example_straw_bale():
    key = "wall/axis-y/x0/y0-y1/level-0"
    pieces = _wall_pieces(FIXTURE, key)
    oid = next(o["id"] for o in _by_kind(FIXTURE, "Opening") if o["id"] in "".join(pieces))
    expected = {
        f"opening/{oid}/buck-jamb/start": ((53.25, 34.5), (53.25, 85.5)),
        f"opening/{oid}/buck-jamb/end": ((90.75, 34.5), (90.75, 85.5)),
        f"opening/{oid}/buck-head": ((54, 84.75), (90, 84.75)),
        f"opening/{oid}/buck-sill": ((54, 35.25), (90, 35.25)),
    }
    assert set(pieces) == set(expected)
    for name, (start, end) in expected.items():
        _, _, got_start, got_end = pieces[name]
        assert (*got_start, *got_end) == pytest.approx(tuple(x * IN for x in (*start, *end)), abs=1e-9), name


def test_five_foot_window_and_door():
    """ASM-001 §8.2: the 5'-0" window's cripples, kings, and jacks; the door's one cripple."""
    doc = stud_doc()
    five = _wall_pieces(doc, "wall/axis-x/y0/x0-x1/level-0")
    kinds = Counter(p.piece_kind for p, *_ in five.values())
    assert kinds == {"STUD": 2, "KING": 2, "JACK": 2, "HEADER": 1, "ROUGH_SILL": 1, "CRIPPLE": 6, "GIRT": 2}
    u = sorted(round(start[0] / IN, 6) for p, _, start, _ in five.values() if p.piece_kind in ("KING", "JACK"))
    assert u == [39.75, 41.25, 102.75, 104.25]  # kings 3'-3¾" and 8'-8¼", jacks 3'-5¼" and 8'-6¾"
    assert sorted(round(start[0] / IN, 6) for p, _, start, _ in five.values() if p.piece_kind == "STUD") == [24, 120]
    door = _wall_pieces(doc, "wall/axis-x/y0/x1-x2/level-0")
    cripples = [(start, end) for p, _, start, end in door.values() if p.piece_kind == "CRIPPLE"]
    assert len(cripples) == 1
    (start, end), = cripples
    assert (start[1] / IN, end[1] / IN) == pytest.approx((87.25, 120))  # 7'-3¼" to 10'-0"
    assert not any(p.piece_kind == "ROUGH_SILL" for p, *_ in door.values())


def test_every_opening_cuts_its_mid_height_girt():
    doc = stud_doc()
    inventory = RULE.build(_snapshot(doc))
    for wall in inventory.walls:
        assert inventory.girt_heights[wall.generation_key] == (wall.height_m * (1 / 2),)
        girt_keys = [p.generation_key for p in inventory.framing if p.wall_key == wall.generation_key and p.piece_kind == "GIRT"]
        assert len(girt_keys) == 2 and girt_keys[1].endswith("/girt/g1/start") and "/girt/g1/after/" in girt_keys[0]
    assert {round(v / FT, 9) for h in inventory.girt_heights.values() for v in h} == {5.0, 4.5}


# --- 4: agreement (ASM-001 §5.7) ---------------------------------------------------------------


def _check_agreement(doc: dict[str, Any]) -> None:
    inventory, local = _local(doc)
    sections = _sections(doc)
    openings = {o["id"]: o for o in _by_kind(doc, "Opening")}
    for oid, rect in inventory.framed_openings.items():
        mine = [(p, s, e) for p, _, s, e in local.values() if p.opening_id == oid]
        assert mine, oid
        u_lo = u_hi = None
        v0 = 0.0 if openings[oid]["opening_kind"] == "DOOR" else None
        v1 = None
        for piece, start, end in mine:
            half = _in_plane(piece, sections) / 2
            lo, hi = (start[0] - half, start[0] + half) if piece.piece_kind in VERTICAL else (start[0], end[0])
            assert rect.u0 - 1e-9 <= lo and hi <= rect.u1 + 1e-9, piece.generation_key
            if piece.piece_kind in ("KING", "BUCK_JAMB"):
                u_lo = lo if u_lo is None else min(u_lo, lo)
                u_hi = hi if u_hi is None else max(u_hi, hi)
            if piece.piece_kind in ("HEADER", "BUCK_HEAD"):
                v1 = start[1] + half
            if piece.piece_kind in ("ROUGH_SILL", "BUCK_SILL"):
                v0 = start[1] - half
        assert (u_lo, u_hi, v0, v1) == pytest.approx((rect.u0, rect.u1, rect.v0, rect.v1), abs=1e-9)
    for piece, wall, start, end in local.values():
        if piece.piece_kind == "GIRT":
            assert any(abs(start[1] - v) <= 1e-9 and abs(end[1] - v) <= 1e-9 for v in inventory.girt_heights[wall.generation_key])


def test_rectangles_agree_with_pieces_on_the_fixture_and_stud_infill():
    _check_agreement(FIXTURE)
    _check_agreement(stud_doc())


def _place(doc: dict[str, Any], wall_key: str, **fields: float | str) -> dict[str, Any]:
    wall = next(w for w in _by_kind(doc, "Wall") if w["generation_key"] == wall_key)
    opening = next(o for o in _by_kind(doc, "Opening") if o["wall_id"] == wall["id"])
    opening.update(fields)
    return regenerate(doc)


openings_strategy = st.fixed_dictionaries({
    "opening_kind": st.sampled_from(["WINDOW", "DOOR"]),
    "width_m": st.floats(0.3, 2.6),
    "height_m": st.floats(0.3, 2.4),
    "sill_height_m": st.floats(0.0, 1.5),
    "offset_m": st.floats(0.0, 2.4),
})


@settings(max_examples=40)
@given(fields=openings_strategy, family=st.sampled_from(["straw-bale", "stud-infill"]), wall=st.sampled_from(["wall/axis-y/x3/y1-y2/level-1", "wall/axis-x/y2/x1-x2/level-0"]))
def test_random_openings_never_raise_and_fitting_ones_agree(fields, family, wall):
    """ASM-001 §11 items 4 and 9: random openings never make the rule raise, including ones that fail
    the fit; on fitting snapshots the rectangles agree with the pieces."""
    if fields["opening_kind"] == "DOOR":
        fields = {**fields, "sill_height_m": 0.0}
    doc = with_default(fresh_fixture(), family)
    doc = _place(doc, wall, **fields)
    RULE.build(_snapshot(doc))
    if validate_value(doc).valid:
        _check_agreement(doc)
        _check_properties(doc)


# --- 5: D066 and D076 properties -----------------------------------------------------------------


def _check_properties(doc: dict[str, Any]) -> None:
    inventory, local = _local(doc)
    sections = _sections(doc)
    frame = _by_kind(doc, "FrameSystem")[0]["parameters"]
    L = frame["knee_brace_leg_m"]
    by_wall: dict[str, list] = {}
    for piece, wall, start, end in local.values():
        W, H = wall.length_m, wall.height_m
        braced = frame["knee_braces_level_1"] if wall.level_index == 0 else frame["knee_braces_eave"]
        for _, v in (start, end):
            assert -1e-9 <= v <= H + 1e-9, piece.generation_key
        if piece.piece_kind == "STUD":
            assert start[0] > EPS and start[0] < W - EPS  # no stud on a post axis
        if piece.piece_kind in VERTICAL and braced:
            u = start[0]
            top = (H - L) + u if u < L - EPS else (H - L) + (W - u) if u > W - L + EPS else H
            if piece.piece_kind in ("STUD", "KING") or piece.generation_key.endswith("/above"):
                assert end[1] == pytest.approx(top, abs=1e-9), piece.generation_key  # ends on the brace axis
            else:
                assert end[1] <= top + 1e-9, piece.generation_key  # never crosses a brace
        assert end[0] - start[0] >= -1e-12 and end[1] - start[1] >= -1e-12  # upward, toward the end
        half = _in_plane(piece, sections) / 2
        if piece.piece_kind in VERTICAL:
            face = (start[0] - half, start[0] + half, start[1], end[1])
        else:
            face = (start[0], end[0], start[1] - half, start[1] + half)
        by_wall.setdefault(wall.generation_key, []).append((piece, face))
    # Faces overlap only where a girt crosses a vertical piece (ASM-001 §5.6).
    for entries in by_wall.values():
        for a in range(len(entries)):
            for b in range(a + 1, len(entries)):
                (pa, fa), (pb, fb) = entries[a], entries[b]
                du = min(fa[1], fb[1]) - max(fa[0], fb[0])
                dv = min(fa[3], fb[3]) - max(fa[2], fb[2])
                if du > 1e-9 and dv > 1e-9:
                    kinds = {pa.piece_kind, pb.piece_kind}
                    assert "GIRT" in kinds and kinds - {"GIRT"} <= VERTICAL, (pa.generation_key, pb.generation_key)


def test_properties_on_the_fixture_and_stud_infill():
    _check_properties(FIXTURE)
    _check_properties(stud_doc())


@pytest.mark.parametrize("width_over", [0.0, 2 * EPS])
def test_jacks_appear_exactly_above_the_threshold(width_over):
    doc = stud_doc()
    threshold = _framing(doc, "stud-infill")["jack_threshold_width_m"]
    doc = _place(doc, "wall/axis-y/x3/y1-y2/level-1", width_m=threshold + width_over, offset_m=1.0)
    _valid(doc)
    pieces = _wall_pieces(doc, "wall/axis-y/x3/y1-y2/level-1")
    jacks = [p for p, *_ in pieces.values() if p.piece_kind == "JACK"]
    assert len(jacks) == (2 if width_over else 0)


def test_zero_length_cases_generate_nothing():
    """ASM-001 §5.6: a lower cripple when s = t, an upper cripple when the header's top is on the
    upper datum, and a girt piece when a framed opening touches a post axis."""
    t = 1.5 * IN
    doc = stud_doc()
    key = "wall/axis-y/x0/y0-y1/level-0"  # H 10'-0", W 12'-0", the layout stud s3 at 6'-0" is claimed
    doc = _place(doc, key, sill_height_m=t)
    _valid(doc)
    pieces = _wall_pieces(doc, key)
    assert not any(k.endswith("/below") for k in pieces) and any(k.endswith("/s3/above") for k in pieces)

    doc = stud_doc()
    doc = _place(doc, key, sill_height_m=0.9144, height_m=10 * FT - 0.9144 - 7.25 * IN)  # header top on the upper datum
    _valid(doc)
    pieces = _wall_pieces(doc, key)
    assert not any(k.endswith("/above") for k in pieces) and any(k.endswith("/s3/below") for k in pieces)

    doc = stud_doc()
    doc = _place(doc, key, offset_m=t, sill_height_m=0.9144, height_m=3 * FT)  # u0 = 0; v1 = 6'-7¼" < H - L
    _valid(doc)
    pieces = _wall_pieces(doc, key)
    girts = sorted(k for k, (p, *_) in pieces.items() if p.piece_kind == "GIRT")
    assert len(girts) == 1 and "/after/" in girts[0]


# --- 6: keys ----------------------------------------------------------------------------------------


def test_keys():
    for doc in (FIXTURE, stud_doc()):
        inventory = RULE.build(_snapshot(doc))
        wall_keys = {w.generation_key for w in inventory.walls}
        assert all(re.fullmatch(r"wall/axis-(x/y\d+/x\d+-x\d+|y/x\d+/y\d+-y\d+)/level-[01]", k) for k in wall_keys)
        for p in inventory.framing:
            assert p.generation_key.startswith(p.wall_key + "/") and p.wall_key in wall_keys
            if p.opening_id is not None:
                assert f"/opening/{p.opening_id}/" in p.generation_key
        member_keys = {e["generation_key"] for e in doc["entities"] if e["kind"] in ("TimberMember", "Connection")}
        all_keys = [*wall_keys, *(p.generation_key for p in inventory.framing), *member_keys]
        assert len(all_keys) == len(set(all_keys))
        assert max(len(k) for k in all_keys if k.startswith("wall/")) <= 95  # about 90 (ASM-001 §6.1)


# --- 9: counts and robustness ---------------------------------------------------------------------


@pytest.mark.parametrize("nx,ny", [(2, 2), (2, 7), (7, 2), (4, 3), (5, 5), (7, 7)])
def test_wall_counts_per_grid(nx, ny):
    doc = grid_doc(nx, ny, bay_ft=12)
    _valid(doc)
    walls = RULE.generate_walls(_snapshot(doc))
    assert len(walls) == 2 * 2 * ((nx - 1) + (ny - 1))
    keys = [w.generation_key for w in walls] + [p.generation_key for p in RULE.generate_framing(_snapshot(doc))]
    assert len(keys) == len(set(keys))


@pytest.mark.parametrize("spacing,girts", [(0.3048, 0), (0.3048, 4), (1.2192, 0), (1.2192, 4)])
def test_definition_bounds(spacing, girts):
    """D077 bounds: the inventory is generated and its keys are unique. Four girts need a brace
    plane off on Level 1 (H 9'-0", L 3'-0": the top girt at 7'-2⅖" crosses the brace feet)."""
    doc = fresh_fixture()
    framing = _framing(doc, "stud-infill")
    framing.update(stud_spacing_m=spacing, girt_count=girts)
    doc = with_default(doc, "stud-infill")
    result = validate_value(doc)
    if girts == 4:
        assert {i.code for i in result.issues} == {"GIRT_CROSSES_BRACE"}
        entities_of(doc, "FrameSystem")[0]["parameters"].update(knee_braces_level_1=False, knee_braces_eave=False)
        doc = regenerate(doc)
    _valid(doc)
    inventory = RULE.build(_snapshot(doc))
    keys = [p.generation_key for p in inventory.framing]
    assert len(keys) == len(set(keys))
    assert Counter(p.piece_kind for p in inventory.framing)["GIRT"] >= 20 * girts


def test_largest_case_is_reported(capsys):
    """ASM-001 §11 item 9: the largest supported case's piece count and propose time (TEST-003 sets budgets)."""
    import time

    from homedesign.model.commands import propose

    doc = grid_doc(7, 7, bay_ft=80 / 6)
    framing = _framing(doc, "stud-infill")
    framing.update(stud_spacing_m=0.3048, girt_count=1)
    doc = with_default(doc, "stud-infill")
    base = _valid(doc)
    started = time.perf_counter()
    result = propose(base, {
        "command_id": "00000000-0000-4000-8000-0000000000a1", "project_id": base.project_id, "base_revision_id": base.revision_id,
        "type": "SetWallAssembly", "args": {"assembly_definition_id": _definition(doc, "straw-bale")["id"]},
    }, actor_id="00000000-0000-4000-8000-000000000001", at="2026-11-22T00:00:00Z")
    elapsed = time.perf_counter() - started
    assert result.accepted
    with capsys.disabled():
        print(f"\n[ASM-001] largest case (7×7, 80'×80', 12\" studs): {len(RULE.generate_framing(base))} stud infill pieces, "
              f"{len(RULE.generate_walls(base))} walls; SetWallAssembly propose {elapsed:.2f} s")


# --- 10: template ------------------------------------------------------------------------------------


def test_template_definitions():
    """AC2b-02, ASM-001 §7: layers, thicknesses, materials, framing values; every property null."""
    materials = {m["id"]: m for m in _by_kind(FIXTURE, "Material")}
    sections = {s["id"]: s for s in _by_kind(FIXTURE, "Section")}
    expected = {
        "straw-bale": ("STRAW_BALE", [("lime-plaster", "FINISH", 0.0381, "Lime plaster"), ("bales", "FRAMING", 0.4572, "Straw"), ("clay-plaster", "FINISH", 0.0254, "Clay plaster")]),
        "stud-infill": ("STUD_INFILL", [("siding", "FINISH", 0.01905, "Wood siding"), ("sheathing", "SHEATHING", 0.0127, "Sheathing"), ("framing", "FRAMING", 0.1397, "Dense-pack cellulose"), ("gypsum-board", "FINISH", 0.0127, "Gypsum board")]),
    }
    definitions = _by_kind(FIXTURE, "AssemblyDefinition")
    assert sorted(d["label"] for d in definitions) == ["straw-bale", "stud-infill"]
    for d in definitions:
        family, layers = expected[d["label"]]
        assert d["family"] == family
        assert [(l["name"], l["function"], l["thickness_m"], materials[l["material_id"]]["name"]) for l in d["layers"]] == layers
        for layer in d["layers"]:
            assert layer["thermal_conductivity_w_m_k"] is None and layer["thermal_resistance_m2_k_w"] is None and layer["vapor_permeance_kg_pa_s_m2"] is None
    buck = _framing(FIXTURE, "straw-bale")
    assert buck == {"type": "BUCK", "framing_material_id": buck["framing_material_id"], "framing_thermal_conductivity_w_m_k": None, "buck_section_id": buck["buck_section_id"], "girt_count": 0}
    assert materials[buck["framing_material_id"]]["species"] == "spruce-pine-fir" and sections[buck["buck_section_id"]]["nominal_label"] == "1.5x18"
    stud = _framing(FIXTURE, "stud-infill")
    assert (stud["stud_spacing_m"], stud["girt_count"], stud["jack_threshold_width_m"], stud["framing_thermal_conductivity_w_m_k"]) == (0.6096, 1, 1.2192, None)
    assert [sections[stud[f]]["nominal_label"] for f in ("stud_section_id", "girt_section_id", "header_section_id")] == ["2x6", "2x6", "2x8"]
    assert materials[stud["framing_material_id"]]["name"] == "Spruce-pine-fir"
    wall_sections = {s["nominal_label"]: (s["actual_width_m"], s["actual_depth_m"]) for s in sections.values() if s["nominal_label"] in ("2x6", "2x8", "1.5x18")}
    assert wall_sections == {"2x6": (0.0381, 0.1397), "2x8": (0.0381, 0.18415), "1.5x18": (0.0381, 0.4572)}
    new_materials = [m for m in materials.values() if m["name"] != "Eastern white pine"]
    assert sorted(m["name"] for m in new_materials) == sorted(name for _, name, _ in wall_template.MATERIALS)
    assert all(m["grade"] is None and m["density_kg_m3"] is None and m["provenance"] is None for m in new_materials)
    labels = [s["nominal_label"] for s in sections.values()]
    assert len(labels) == len(set(labels))


def test_template_text_is_d081_exactly():
    """D081: the strings are stored exactly as written in the decision."""
    text = (REPO_ROOT / "docs/product/decisions/D081-reference-house-001-v3-template-text.md").read_text(encoding="utf-8")
    notes = re.findall(r'^\*\*`installation_note`:\*\* "(.*)"$', text, flags=re.MULTILINE)
    details = re.findall(r'^\d\. "(.*)"$', text, flags=re.MULTILINE)
    assert notes == [_definition(FIXTURE, "straw-bale")["installation_note"], _definition(FIXTURE, "stud-infill")["installation_note"]]
    assert details == _definition(FIXTURE, "straw-bale")["unverified_climate_details"] + _definition(FIXTURE, "stud-infill")["unverified_climate_details"]


def test_fixture_openings_follow_d072():
    openings = _by_kind(FIXTURE, "Opening")
    walls = {w["id"]: w["generation_key"] for w in _by_kind(FIXTURE, "Wall")}
    kinds = Counter((o["opening_kind"], o["width_m"], o["height_m"], o["sill_height_m"], o["offset_m"]) for o in openings)
    assert kinds == {("DOOR", 0.9144, 2.032, 0.0, 1.3716): 1, ("WINDOW", 1.524, 1.2192, 0.9144, 1.0668): 2, ("WINDOW", 0.9144, 1.2192, 0.9144, 1.3716): 17}
    assert sorted(walls[o["wall_id"]] for o in openings) == sorted(walls.values())  # one per wall
    door = next(o for o in openings if o["opening_kind"] == "DOOR")
    assert walls[door["wall_id"]] == "wall/axis-x/y0/x1-x2/level-0"
    assert _system(FIXTURE)["generation_rule_version"] == "vs02b-walls-1" == registered_versions()[0]
    assert Counter(e["kind"] for e in FIXTURE["entities"])["Opening"] == 20
    authored = [e for e in FIXTURE["entities"] if e["kind"] not in ("TimberMember", "Connection", "Wall", "WallFramingPiece")]
    assert len(authored) == 47 and len(FIXTURE["entities"]) == 651  # ASM-001 §8.1


# --- 11: oracle ----------------------------------------------------------------------------------------


def _oracle_rows(doc: dict[str, Any]):
    sections = _sections(doc)
    materials = {m["id"]: m["name"] for m in _by_kind(doc, "Material")}
    inventory = RULE.build(_snapshot(doc))
    walls = [{"generation_key": w.generation_key, "level_index": w.level_index, "start_m": list(w.start_m), "end_m": list(w.end_m), "height_m": w.height_m} for w in inventory.walls]
    pieces = [
        {"generation_key": p.generation_key, "wall_key": p.wall_key, "piece_kind": p.piece_kind, "opening_id": p.opening_id,
         "start_m": list(p.start_m), "end_m": list(p.end_m), "section_label": sections[p.section_id]["nominal_label"], "material_name": materials[p.material_id]}
        for p in inventory.framing
    ]
    return walls, pieces


def test_oracle_walls_are_bit_identical():
    """ASM-001 §9: the ECMAScript walls and framing equal Python's in every field, bit for bit."""
    vectors = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))["inventories"]
    straw = next(v for v in vectors if v["name"] == "reference-house-001-vs02-frame-1")
    stud = next(v for v in vectors if v["name"] == "reference-house-001-stud-infill-vs02b-walls-1")
    walls, pieces = _oracle_rows(FIXTURE)
    assert straw["walls"] == walls and straw["wall_framing"] == pieces
    doc = fresh_fixture()
    _system(doc)["default_assembly_definition_id"] = _definition(doc, "stud-infill")["id"]  # unregenerated, as the oracle reads it
    walls, pieces = _oracle_rows(doc)
    assert stud["walls"] == walls and stud["wall_framing"] == pieces and len(pieces) == 246


# --- 12: determinism ---------------------------------------------------------------------------------


@pytest.mark.parametrize("seed", [3, 17])
def test_determinism_across_orderings(seed):
    doc = stud_doc()
    first = RULE.build(_snapshot(doc))
    random.Random(seed).shuffle(doc["entities"])
    second = RULE.build(_snapshot(doc))
    assert first.walls == second.walls and first.framing == second.framing
    assert dict(first.framed_openings) == dict(second.framed_openings) and dict(first.girt_heights) == dict(second.girt_heights)


# --- 13: conformance -----------------------------------------------------------------------------------


def _codes(doc):
    result = validate_value(doc)
    return {(i.code, i.path) for i in result.issues}


@pytest.mark.parametrize("family", ["straw-bale", "stud-infill"])
def test_conformance_codes_for_each_piece_kind(family):
    """ASM-001 §11 item 13: mutating one wall and one piece of each kind is caught at stage 5."""
    base = with_default(fresh_fixture(), family)
    wall = _by_kind(base, "Wall")[0]
    doc = json.loads(json.dumps(base))
    next(w for w in _by_kind(doc, "Wall") if w["id"] == wall["id"])["end_m"][2] += 0.01
    assert ("WALL_GEOMETRY_MISMATCH", f"entities[{wall['id']}].end_m") in _codes(doc)
    kinds = {}
    for piece in _by_kind(base, "WallFramingPiece"):
        kinds.setdefault(piece["piece_kind"], piece)
    for kind, piece in kinds.items():
        doc = json.loads(json.dumps(base))
        next(p for p in _by_kind(doc, "WallFramingPiece") if p["id"] == piece["id"])["start_m"][2] -= 0.001
        assert _codes(doc) == {("FRAMING_GEOMETRY_MISMATCH", f"entities[{piece['id']}].start_m")}, kind
        doc = json.loads(json.dumps(base))
        other = next(k for k in ("STUD", "BUCK_HEAD") if k != kind)
        next(p for p in _by_kind(doc, "WallFramingPiece") if p["id"] == piece["id"])["piece_kind"] = other
        assert _codes(doc) == {("FRAMING_ASSIGNMENT_MISMATCH", f"entities[{piece['id']}].piece_kind")}, kind


# --- 14: fixture check and created projects ----------------------------------------------------------


def test_fixture_check_passes():
    from homedesign.timber.fixture import main

    assert main(["--check"]) == 0


def test_created_project_equals_fixture_apart_from_ids():
    """ASM-001 §8.3, §11 item 14: apart from IDs, opening-ID tokens in keys, and revision metadata."""
    from homedesign.model.commands import propose_create

    result = propose_create({"command_id": "00000000-0000-4000-8000-00000000c0de", "type": "CreateReferenceProject", "args": {}},
                            project_id="00000000-0000-4000-8000-00000000beef", actor_id="00000000-0000-4000-8000-000000000001", at="2026-11-22T00:00:00Z")
    assert result.accepted
    created = result.change.candidate.model_dump(mode="json")
    template = json.loads(json.dumps(FIXTURE))

    # Map fixture IDs to created IDs: authored records by position of kind and content, generated by key.
    def key_map(doc):
        return {e["generation_key"]: e["id"] for e in doc["entities"] if "generation_key" in e}

    opening_pairs = {}
    walls_f = {w["id"]: w["generation_key"] for w in _by_kind(template, "Wall")}
    walls_c = {w["generation_key"]: w["id"] for w in _by_kind(created, "Wall")}
    for o in _by_kind(template, "Opening"):
        match = next(c for c in _by_kind(created, "Opening") if c["wall_id"] == walls_c[walls_f[o["wall_id"]]])
        opening_pairs[o["id"]] = match["id"]

    def normalize(doc, pairs):
        text = json.dumps(doc)
        for old, new in pairs.items():
            text = text.replace(old, new)
        return json.loads(text)

    template = normalize(template, opening_pairs)  # opening-ID tokens inside keys, and opening IDs
    ids = {}
    for kind in ("Footprint", "Level", "GableRoof", "TimberGrid", "FrameSystem", "Section", "Material", "WallSystem", "AssemblyDefinition"):
        fixture_records, created_records = _by_kind(template, kind), _by_kind(created, kind)
        assert len(fixture_records) == len(created_records)
        for f in fixture_records:
            strip = lambda r: {k: v for k, v in r.items() if k != "id" and not k.endswith("_id") and not k.endswith("_ids") and k != "layers" and k != "member_defaults"}  # noqa: E731
            c = next(c for c in created_records if strip(c) == strip(f) and c["id"] not in ids.values())
            ids[f["id"]] = c["id"]
    ids[template["building"]["id"]] = created["building"]["id"]
    fk, ck = key_map(template), key_map(created)
    assert fk.keys() == ck.keys()
    ids.update({fk[k]: ck[k] for k in fk})
    mapped = normalize(template, ids)
    _system(mapped)["opening_ids"].sort()  # ID order, and the IDs differ
    by_id = lambda doc: sorted(doc["entities"], key=lambda e: e["id"])  # noqa: E731
    assert mapped["building"] == created["building"]
    assert by_id(mapped) == by_id(created)
