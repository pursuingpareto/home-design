"""MODEL-006 acceptance tests (§11): schema version 3, validation, the fit rules, the wall commands,
the pipeline, and the preview diff. Identity under each edit is ASM-001 §11 items 7–8."""

from __future__ import annotations

import copy
import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any

import jsonschema
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from conftest import FIXTURE, REPO_ROOT, SCHEMA_PATH, fresh_fixture
from homedesign.model import validate_value
from homedesign.model.commands import CLASSIFICATION, mint, propose, propose_create
from homedesign.model.schema import Snapshot

P = "17ac32e0-0b3b-518e-b568-adf98f41bcd0"
ACTOR = "00000000-0000-4000-8000-000000000001"
CID = "33333333-3333-4333-8333-333333333333"
AT = "2026-11-22T12:00:00Z"
FT, IN = 0.3048, 0.0254
EPS = 1e-6
T = 1.5 * IN  # the 2x6 in-plane thickness, and the buck's
D = 7.25 * IN  # the 2x8 header's vertical depth


def _create():
    result = propose_create({"command_id": "b8f9d645-5a10-4eb5-b2ca-38ce46e5d4aa", "type": "CreateReferenceProject", "args": {}}, project_id=P, actor_id=ACTOR, at=AT)
    assert result.accepted
    return result.change.candidate


BASE = _create()


def of_kind(snapshot, kind):
    return [e for e in snapshot.entities if e.kind == kind]


def one(snapshot, kind):
    return of_kind(snapshot, kind)[0]


def epath(entity_id, *steps):
    text = f"entities[{entity_id}]"
    for s in steps:
        text += f"[{s}]" if isinstance(s, int) else f".{s}"
    return text


def run(type_, args, base=BASE, cid=CID, target=None):
    envelope = {"command_id": cid, "project_id": base.project_id, "base_revision_id": base.revision_id, "type": type_, "args": args}
    return propose(base, envelope, actor_id=ACTOR, at=AT, target=target)


def accept(type_, args, base=BASE, cid=CID, target=None):
    result = run(type_, args, base, cid, target)
    assert result.accepted, result.rejection and result.rejection.to_dict()
    return result.change


def reject(type_, args, base=BASE, cid=CID):
    result = run(type_, args, base, cid)
    assert not result.accepted
    return result.rejection


def definition(snapshot, label):
    return next(d for d in of_kind(snapshot, "AssemblyDefinition") if d.label == label)


def wall(snapshot, key):
    return next(w for w in of_kind(snapshot, "Wall") if w.generation_key == key)


def opening_on(snapshot, key):
    w = wall(snapshot, key)
    return next(o for o in of_kind(snapshot, "Opening") if o.wall_id == w.id)


def set_opening(opening, base=BASE, **fields):
    args = {name: getattr(opening, name) for name in ("width_m", "height_m", "sill_height_m", "offset_m")} | fields
    return {"opening_id": opening.id, **args}


STUD = definition(BASE, "stud-infill")
STRAW = definition(BASE, "straw-bale")
SYSTEM = one(BASE, "WallSystem")
FP = one(BASE, "Footprint")
GRID = one(BASE, "TimberGrid")
FRAME = one(BASE, "FrameSystem")
L0, L1 = (next(e for e in BASE.entities if e.id == i) for i in BASE.building.level_ids)
L1_WALL = "wall/axis-y/x3/y1-y2/level-1"  # W 12'-0", H 9'-0", L 3'-0"; a 3'-0" window
STUD_BASE = accept("SetWallAssembly", {"assembly_definition_id": STUD.id}).candidate


def issues(result):
    return [(i.code, i.path, set(i.related_paths)) for i in result.issues]


def codes_of(result):
    return {i.code for i in result.issues}


# --- 1, 2: version 3 only ---------------------------------------------------------------------------


def test_version_2_is_rejected():
    doc = fresh_fixture()
    doc["model_schema_version"] = 2
    result = validate_value(doc)
    assert [(i.code, i.path) for i in result.issues] == [("UNSUPPORTED_SCHEMA_VERSION", "model_schema_version")]


@pytest.mark.parametrize("kind,version", [("Building", 1), ("Wall", 2), ("WallSystem", 2), ("Opening", 0), ("TimberMember", 1)])
def test_record_versions_are_per_kind(kind, version):
    doc = fresh_fixture()
    record = doc["building"] if kind == "Building" else next(e for e in doc["entities"] if e["kind"] == kind)
    record["schema_version"] = version
    path = "building.schema_version" if kind == "Building" else epath(record["id"], "schema_version")
    assert [(i.code, i.path) for i in validate_value(doc).issues] == [("UNSUPPORTED_SCHEMA_VERSION", path)]


# --- 3: every new detail code from a minimal fixture mutation -----------------------------------------


def _e(doc, kind, pick=0):
    records = [e for e in doc["entities"] if e["kind"] == kind]
    return records[pick] if isinstance(pick, int) else next(r for r in records if pick(r))


def _def(doc, label):
    return _e(doc, "AssemblyDefinition", lambda d: d["label"] == label)


def _wall_by_key(doc, key):
    return _e(doc, "Wall", lambda w: w["generation_key"] == key)


def _opening_of(doc, wall_record):
    return _e(doc, "Opening", lambda o: o["wall_id"] == wall_record["id"])


def _piece(doc, piece_id):
    return _e(doc, "WallFramingPiece", lambda p: p["id"] == piece_id)


def _later_by_id(*records):
    return sorted(records, key=lambda r: r["id"])


def _mutation_cases():
    """(name, mutate(doc) -> (code, path, related)) for MODEL-006 §6's new codes."""

    def slug_label(d):
        r = _def(d, "straw-bale"); r["label"] = "Straw Bale"
        return "INVALID_SLUG", epath(r["id"], "label"), set()

    def slug_layer(d):
        r = _def(d, "straw-bale"); r["layers"][0]["name"] = "lime_plaster"
        return "INVALID_SLUG", epath(r["id"], "layers", 0, "name"), set()

    def bad_date(d):
        r = _def(d, "straw-bale")
        r["layers"][0]["thermal_conductivity_w_m_k"] = {"value": 0.8, "source": "test", "date": "2026-02-30", "note": None}
        return "INVALID_DATE", epath(r["id"], "layers", 0, "thermal_conductivity_w_m_k", "date"), set()

    def bad_date_pattern(d):
        r = _def(d, "straw-bale")
        r["layers"][0]["thermal_conductivity_w_m_k"] = {"value": 0.8, "source": "test", "date": "2026-2-3", "note": None}
        return "INVALID_DATE", epath(r["id"], "layers", 0, "thermal_conductivity_w_m_k", "date"), set()

    def framing_type(d):
        r = _def(d, "straw-bale"); r["layers"][1]["framing"]["type"] = "LOG"
        return "INVALID_ENUM", epath(r["id"], "layers", 1, "framing", "type"), set()

    def girt_fraction(d):
        r = _def(d, "stud-infill"); r["layers"][2]["framing"]["girt_count"] = 1.5
        return "INTEGER_OUT_OF_RANGE", epath(r["id"], "layers", 2, "framing", "girt_count"), set()

    def framing_unknown(d):
        r = _def(d, "straw-bale"); r["layers"][1]["framing"]["stud_spacing_m"] = 0.6
        return "UNKNOWN_FIELD", epath(r["id"], "layers", 1, "framing", "stud_spacing_m"), set()

    def layer_missing(d):
        r = _def(d, "straw-bale"); del r["layers"][0]["vapor_permeance_kg_pa_s_m2"]
        return "MISSING_FIELD", epath(r["id"], "layers", 0, "vapor_permeance_kg_pa_s_m2"), set()

    def piece_kind(d):
        p = _e(d, "WallFramingPiece"); p["piece_kind"] = "PLATE"
        return "INVALID_ENUM", epath(p["id"], "piece_kind"), set()

    def wall_set(d):
        s = _e(d, "WallSystem"); removed = s["wall_ids"].pop(3)
        return "WALL_SET_MISMATCH", epath(s["id"], "wall_ids"), {epath(removed)}

    def opening_set(d):
        s = _e(d, "WallSystem"); removed = s["opening_ids"].pop(5)
        return "OPENING_SET_MISMATCH", epath(s["id"], "opening_ids"), {epath(removed)}

    def framing_unlisted(d):
        w = _e(d, "Wall"); removed = w["framing_ids"].pop(0)
        return "FRAMING_SET_MISMATCH", epath(_e(d, "WallSystem")["id"], "wall_ids"), {epath(removed)}

    def framing_twice(d):
        a, b = _later_by_id(*[w for w in d["entities"] if w["kind"] == "Wall"][:2])
        piece_id = a["framing_ids"][0]
        b["framing_ids"] = sorted([*b["framing_ids"], piece_id], key=lambda i: _piece(d, i)["generation_key"])
        return "FRAMING_SET_MISMATCH", epath(b["id"], "framing_ids"), {epath(piece_id)}

    def wall_order(d):
        s = _e(d, "WallSystem"); s["wall_ids"].reverse()
        return "ORDER_VIOLATION", epath(s["id"], "wall_ids"), set()

    def opening_order(d):
        s = _e(d, "WallSystem"); s["opening_ids"].reverse()
        return "ORDER_VIOLATION", epath(s["id"], "opening_ids"), set()

    def framing_order(d):
        w = _e(d, "Wall"); w["framing_ids"].reverse()
        return "ORDER_VIOLATION", epath(w["id"], "framing_ids"), set()

    def key_collision(d):
        w = _e(d, "Wall"); m = _e(d, "TimberMember")
        w["generation_key"] = m["generation_key"]
        first, later = _later_by_id(w, m)
        # the wall list stays ordered: wall_ids is re-sorted by key as the rule would
        s = _e(d, "WallSystem")
        s["wall_ids"] = sorted(s["wall_ids"], key=lambda i: _e(d, "Wall", lambda x: x["id"] == i)["generation_key"])
        return "DUPLICATE_GENERATION_KEY", epath(later["id"], "generation_key"), {epath(first["id"], "generation_key")}

    def duplicate_label(d):
        a, b = _def(d, "straw-bale"), _def(d, "stud-infill")
        b["label"] = "straw-bale"
        first, later = _later_by_id(a, b)
        return "DUPLICATE_ASSEMBLY_LABEL", epath(later["id"], "label"), {epath(first["id"], "label")}

    def duplicate_layer(d):
        r = _def(d, "stud-infill"); r["layers"][3]["name"] = "siding"
        return "DUPLICATE_LAYER_NAME", epath(r["id"], "layers", 3, "name"), {epath(r["id"], "layers", 0, "name")}

    def unreferenced_system(d):
        extra = copy.deepcopy(_e(d, "WallSystem")); extra["id"] = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaab"; d["entities"].append(extra)
        return "UNREFERENCED_ENTITY", epath(extra["id"]), set()

    def wrong_kind_default(d):
        s = _e(d, "WallSystem"); s["default_assembly_definition_id"] = _e(d, "Section")["id"]
        return "WRONG_REFERENCE_KIND", epath(s["id"], "default_assembly_definition_id"), set()

    def dangling_opening_wall(d):
        o = _e(d, "Opening"); o["wall_id"] = str(uuid.uuid4())
        return "DANGLING_REFERENCE", epath(o["id"], "wall_id"), set()

    def thickness(d):
        r = _def(d, "straw-bale"); r["layers"][0]["thickness_m"] = 0.0
        return "OUT_OF_RANGE", epath(r["id"], "layers", 0, "thickness_m"), set()

    def spacing_zero(d):
        r = _def(d, "stud-infill"); r["layers"][2]["framing"]["stud_spacing_m"] = 0.0
        return "OUT_OF_RANGE", epath(r["id"], "layers", 2, "framing", "stud_spacing_m"), set()

    def conductivity_zero(d):
        r = _def(d, "straw-bale")
        r["layers"][0]["thermal_conductivity_w_m_k"] = {"value": 0.0, "source": "test", "date": "2026-01-01", "note": None}
        return "OUT_OF_RANGE", epath(r["id"], "layers", 0, "thermal_conductivity_w_m_k", "value"), set()

    def permeance_negative(d):
        r = _def(d, "straw-bale")
        r["layers"][0]["vapor_permeance_kg_pa_s_m2"] = {"value": -1e-12, "source": "test", "date": "2026-01-01", "note": None}
        return "OUT_OF_RANGE", epath(r["id"], "layers", 0, "vapor_permeance_kg_pa_s_m2", "value"), set()

    def opening_width(d):
        o = _e(d, "Opening"); o["width_m"] = 0.0
        return "OUT_OF_RANGE", epath(o["id"], "width_m"), set()

    def opening_offset(d):
        o = _e(d, "Opening"); o["offset_m"] = -0.01
        return "OUT_OF_RANGE", epath(o["id"], "offset_m"), set()

    def threshold_negative(d):
        r = _def(d, "stud-infill"); r["layers"][2]["framing"]["jack_threshold_width_m"] = -0.1
        return "OUT_OF_RANGE", epath(r["id"], "layers", 2, "framing", "jack_threshold_width_m"), set()

    def wall_height(d):
        w = _e(d, "Wall"); w["height_m"] = 0.0
        return "OUT_OF_RANGE", epath(w["id"], "height_m"), set()

    def zero_piece(d):
        p = _e(d, "WallFramingPiece"); p["end_m"] = list(p["start_m"])
        return "ZERO_LENGTH_MEMBER", epath(p["id"]), set()

    def zero_wall(d):
        w = _e(d, "Wall"); w["end_m"] = list(w["start_m"])
        return "ZERO_LENGTH_MEMBER", epath(w["id"]), set()

    def two_framing_layers(d):
        r = _def(d, "straw-bale"); r["layers"][0]["function"] = "FRAMING"
        return "FRAMING_LAYER_COUNT", epath(r["id"], "layers"), set()

    def family_mismatch(d):
        r = _def(d, "straw-bale"); r["family"] = "STUD_INFILL"
        return "UNSUPPORTED_VALUE", epath(r["id"], "layers", 1, "framing", "type"), {epath(r["id"], "family")}

    def buck_girts(d):
        r = _def(d, "straw-bale"); r["layers"][1]["framing"]["girt_count"] = 1
        return "UNSUPPORTED_VALUE", epath(r["id"], "layers", 1, "framing", "girt_count"), set()

    def girts_without_section(d):
        r = _def(d, "stud-infill"); r["layers"][2]["framing"]["girt_section_id"] = None
        return "UNSUPPORTED_VALUE", epath(r["id"], "layers", 2, "framing", "girt_section_id"), {epath(r["id"], "layers", 2, "framing", "girt_count")}

    def both_thermal(d):
        r = _def(d, "straw-bale")
        r["layers"][0]["thermal_conductivity_w_m_k"] = {"value": 0.8, "source": "s", "date": "2026-01-01", "note": None}
        r["layers"][0]["thermal_resistance_m2_k_w"] = {"value": 0.05, "source": "s", "date": "2026-01-01", "note": "n"}
        return "UNSUPPORTED_VALUE", epath(r["id"], "layers", 0, "thermal_resistance_m2_k_w"), {epath(r["id"], "layers", 0, "thermal_conductivity_w_m_k")}

    def framing_resistance(d):
        r = _def(d, "straw-bale")
        r["layers"][1]["thermal_resistance_m2_k_w"] = {"value": 5.0, "source": "s", "date": "2026-01-01", "note": None}
        return "UNSUPPORTED_VALUE", epath(r["id"], "layers", 1, "thermal_resistance_m2_k_w"), set()

    def spacing_range(d):
        r = _def(d, "stud-infill"); r["layers"][2]["framing"]["stud_spacing_m"] = 0.3
        return "OUT_OF_SUPPORTED_RANGE", epath(r["id"], "layers", 2, "framing", "stud_spacing_m"), set()

    def girt_range(d):
        r = _def(d, "stud-infill"); r["layers"][2]["framing"]["girt_count"] = 5
        return "OUT_OF_SUPPORTED_RANGE", epath(r["id"], "layers", 2, "framing", "girt_count"), set()

    def door_sill(d):
        o = _e(d, "Opening", lambda o: o["opening_kind"] == "DOOR"); o["sill_height_m"] = 0.1
        return "UNSUPPORTED_VALUE", epath(o["id"], "sill_height_m"), {epath(o["id"], "opening_kind")}

    def wall_rule(d):
        s = _e(d, "WallSystem"); s["generation_rule_version"] = "vs02b-walls-0"
        return "UNSUPPORTED_VALUE", epath(s["id"], "generation_rule_version"), set()

    def missing_wall(d):
        s = _e(d, "WallSystem")
        w = _e(d, "Wall", lambda w: w["id"] == s["wall_ids"][0])
        o = _opening_of(d, w)
        drop = {w["id"], o["id"], *w["framing_ids"]}
        d["entities"] = [e for e in d["entities"] if e["id"] not in drop]
        s["wall_ids"].remove(w["id"]); s["opening_ids"].remove(o["id"])
        return "MISSING_GENERATED_WALL", epath(s["id"], "wall_ids"), set()

    def unexpected_framing(d):
        w = _e(d, "Wall"); p = _piece(d, w["framing_ids"][-1]); p["generation_key"] += "x"
        return "UNEXPECTED_FRAMING", epath(p["id"], "generation_key"), set()

    def missing_framing(d):
        w = _e(d, "Wall"); piece_id = w["framing_ids"].pop(0)
        d["entities"] = [e for e in d["entities"] if e["id"] != piece_id]
        return "MISSING_GENERATED_FRAMING", epath(w["id"], "framing_ids"), set()

    def wall_level(d):
        w = _e(d, "Wall", lambda w: w["generation_key"].endswith("level-0")); w["level_id"] = d["building"]["level_ids"][1]
        return "WALL_ASSIGNMENT_MISMATCH", epath(w["id"], "level_id"), set()

    def wall_definition(d):
        w = _e(d, "Wall"); w["assembly_definition_id"] = _def(d, "stud-infill")["id"]
        return "WALL_ASSIGNMENT_MISMATCH", epath(w["id"], "assembly_definition_id"), {epath(_e(d, "WallSystem")["id"], "default_assembly_definition_id")}

    def wall_height_mismatch(d):
        w = _e(d, "Wall"); w["height_m"] += 0.01
        return "WALL_GEOMETRY_MISMATCH", epath(w["id"], "height_m"), set()

    def piece_geometry(d):
        p = _e(d, "WallFramingPiece"); p["end_m"] = [p["end_m"][0], p["end_m"][1], p["end_m"][2] + 2e-6]
        return "FRAMING_GEOMETRY_MISMATCH", epath(p["id"], "end_m"), set()

    def piece_section(d):
        p = _e(d, "WallFramingPiece"); p["section_id"] = _e(d, "Section", lambda s: s["nominal_label"] == "2x6")["id"]
        return "FRAMING_ASSIGNMENT_MISMATCH", epath(p["id"], "section_id"), {epath(_def(d, "straw-bale")["id"], "layers", 1, "framing", "buck_section_id")}

    def piece_material(d):
        p = _e(d, "WallFramingPiece"); p["material_id"] = _e(d, "Material", lambda m: m["name"] == "Straw")["id"]
        return "FRAMING_ASSIGNMENT_MISMATCH", epath(p["id"], "material_id"), {epath(_def(d, "straw-bale")["id"], "layers", 1, "framing", "framing_material_id")}

    def piece_opening(d):
        p = _e(d, "WallFramingPiece"); p["opening_id"] = next(o["id"] for o in d["entities"] if o["kind"] == "Opening" and o["id"] != p["opening_id"])
        return "FRAMING_ASSIGNMENT_MISMATCH", epath(p["id"], "opening_id"), set()

    def piece_owner(d):
        walls = sorted((w for w in d["entities"] if w["kind"] == "Wall"), key=lambda w: w["generation_key"])
        a, b = walls[0], walls[1]
        piece_id = a["framing_ids"].pop(0)
        b["framing_ids"] = sorted([*b["framing_ids"], piece_id], key=lambda i: _piece(d, i)["generation_key"])
        return "FRAMING_ASSIGNMENT_MISMATCH", epath(b["id"], "framing_ids"), {epath(a["id"], "framing_ids")}

    return {name: fn for name, fn in locals().items() if callable(fn) and not name.startswith("_")}


CASES = _mutation_cases()


@pytest.mark.parametrize("name", sorted(CASES))
def test_new_detail_codes(name):
    doc = fresh_fixture()
    code, path, related = CASES[name](doc)
    result = validate_value(doc)
    found = [(i.code, i.path, set(i.related_paths)) for i in result.issues if i.code == code and i.path == path]
    assert found, (name, result.to_dict())
    assert found[0][2] == related, (name, found)


def test_unexpected_wall():
    doc = fresh_fixture()
    last = _e(doc, "WallSystem")["wall_ids"][-1]
    w = _e(doc, "Wall", lambda w: w["id"] == last)
    w["generation_key"] += "x"  # still last in key order
    result = validate_value(doc)
    assert ("UNEXPECTED_WALL", epath(w["id"], "generation_key")) in {(i.code, i.path) for i in result.issues}
    assert "MISSING_GENERATED_WALL" in codes_of(result)


def test_every_new_code_is_reached():
    """MODEL-006 §11 item 3: each new detail code of §6 is produced by some mutation (fit codes below)."""
    reached = set()
    for fn in CASES.values():
        doc = fresh_fixture()
        reached.add(fn(doc)[0])
    new = {"INVALID_SLUG", "INVALID_DATE", "WALL_SET_MISMATCH", "OPENING_SET_MISMATCH", "FRAMING_SET_MISMATCH", "DUPLICATE_ASSEMBLY_LABEL",
           "DUPLICATE_LAYER_NAME", "FRAMING_LAYER_COUNT", "MISSING_GENERATED_WALL", "WALL_GEOMETRY_MISMATCH", "WALL_ASSIGNMENT_MISMATCH",
           "MISSING_GENERATED_FRAMING", "UNEXPECTED_FRAMING", "FRAMING_ASSIGNMENT_MISMATCH", "DUPLICATE_GENERATION_KEY", "ZERO_LENGTH_MEMBER"}
    assert new <= reached


# --- 4: definitions (AC2b-02) ---------------------------------------------------------------------------


def test_declared_values():
    doc = fresh_fixture()
    layer = _def(doc, "straw-bale")["layers"][0]
    layer["thermal_conductivity_w_m_k"] = {"value": 0.8, "source": "Manufacturer data sheet", "date": "2026-01-15", "note": "illustrative"}
    layer["vapor_permeance_kg_pa_s_m2"] = {"value": 0.0, "source": "s", "date": "2026-01-15", "note": None}  # a perfect barrier is 0
    assert validate_value(doc).valid
    assert validate_value(fresh_fixture()).valid  # null everywhere


# --- 5: the fit (AC2b-04) -------------------------------------------------------------------------------


def framed(family: str, kind: str, o: float, w: float, s: float, h: float) -> tuple[float, float, float, float]:
    """MODEL-006 §5.1, written independently of the rule."""
    if family == "straw":
        return o - T, o + w + T, (s - T if kind == "WINDOW" else 0.0), s + h + T
    k = 2 * T if w > 4 * FT + EPS else T
    return o - k, o + w + k, (s - T if kind == "WINDOW" else 0.0), s + h + D


FAMILIES = [("straw", BASE), ("stud", STUD_BASE)]
WIDTHS = [3 * FT, 4 * FT, 5 * FT]  # below, at, and above the 4'-0" jack threshold


@pytest.mark.parametrize("family,base", FAMILIES)
@pytest.mark.parametrize("width", WIDTHS)
def test_fit_boundaries(family, base, width):
    W, H, L = 12 * FT, 9 * FT, 3 * FT
    o = opening_on(base, L1_WALL)
    k = framed(family, "WINDOW", 0, width, 0, 0)[1] - width  # the end-side allowance
    cases = []
    # Inside the wall, start side: u0 = 0, with a low window clear of the braces.
    s, h = 1 * FT, 2 * FT
    cases.append(("OPENING_OUTSIDE_WALL", "offset_m", dict(offset_m=k, width_m=width, sill_height_m=s, height_m=h), dict(offset_m=k - 2 * EPS)))
    # End side: u1 = W.
    cases.append(("OPENING_OUTSIDE_WALL", "width_m", dict(offset_m=W - width - k, sill_height_m=s, height_m=h, width_m=width), dict(offset_m=W - width - k + 2 * EPS, width_m=width)))
    # Top: v1 = H, centered (clear of both braces).
    top_allowance = framed(family, "WINDOW", 0, 0, 0, 0)[3]
    center = (W - width) / 2
    hh = H - 3 * FT - top_allowance
    cases.append(("OPENING_OUTSIDE_WALL", "height_m", dict(offset_m=center, width_m=width, sill_height_m=3 * FT, height_m=hh), dict(offset_m=center, width_m=width, sill_height_m=3 * FT, height_m=hh + 2 * EPS)))
    # Bottom: v0 = 0 (the sill leaves room for its rough sill or buck sill, D076).
    cases.append(("OPENING_OUTSIDE_WALL", "sill_height_m", dict(offset_m=center, width_m=width, sill_height_m=T, height_m=h), dict(offset_m=center, width_m=width, sill_height_m=T - 2 * EPS, height_m=h)))
    # Start brace: v1 - u0 = H - L.
    s, h = 3 * FT, 4 * FT
    v1 = framed(family, "WINDOW", 0, width, s, h)[3]
    u0 = v1 - (H - L)
    cases.append(("OPENING_CROSSES_BRACE", "offset_m", dict(offset_m=u0 + k, width_m=width, sill_height_m=s, height_m=h), dict(offset_m=u0 + k - 2 * EPS, width_m=width, sill_height_m=s, height_m=h)))
    # End brace: v1 + u1 = H - L + W.
    u1 = (H - L + W) - v1
    cases.append(("OPENING_CROSSES_BRACE", "width_m", dict(offset_m=u1 - width - k, width_m=width, sill_height_m=s, height_m=h), dict(offset_m=u1 - width - k + 2 * EPS, width_m=width, sill_height_m=s, height_m=h)))
    for code, field, at, beyond in cases:
        accept("SetOpening", set_opening(o, **at), base)
        rejection = reject("SetOpening", set_opening(o, **{**at, **beyond}), base)
        found = [i for i in rejection.issues if i.code == code]
        assert found and found[0].path == epath(o.id, field), (code, field, rejection.to_dict())
        assert f"args.{field}" in found[0].related_paths
        assert epath(SYSTEM.id, "default_assembly_definition_id") in found[0].related_paths
        assert rejection.code == "UNSUPPORTED_CONFIGURATION"


@pytest.mark.parametrize("family,base", FAMILIES)
def test_openings_overlap_boundary(family, base):
    """D079: framed ranges along the wall may touch, not overlap, whatever their heights."""
    o = opening_on(base, L1_WALL)
    u1 = framed(family, "WINDOW", o.offset_m, o.width_m, o.sill_height_m, o.height_m)[1]
    k = T  # a 1'-0" opening has no jacks
    args = {"wall_id": wall(base, L1_WALL).id, "opening_kind": "WINDOW", "width_m": 1 * FT, "height_m": 1 * FT, "sill_height_m": 6 * FT}
    added = accept("AddOpening", {**args, "offset_m": u1 + k}, base)
    new_id = mint("entity", P, ACTOR, CID, "opening")
    assert [c["entity_id"] for c in added.changes if c["entity_kind"] == "Opening"] == [new_id]
    rejection = reject("AddOpening", {**args, "offset_m": u1 + k - 2 * EPS}, base)
    later, earlier = (new_id, o.id) if new_id > o.id else (o.id, new_id)
    assert issues(rejection) == [("OPENINGS_OVERLAP", epath(later, "offset_m"), {epath(earlier, "offset_m"), "args.offset_m"})]
    # Stacked: a window above the first, clear of it in height, still overlaps along the wall (D079).
    rejection = reject("AddOpening", {**args, "offset_m": o.offset_m + 1 * FT, "sill_height_m": 7.25 * FT}, base)
    assert codes_of(rejection) == {"OPENINGS_OVERLAP"}


def _related_args(rejection, code, arg):
    found = [i for i in rejection.issues if i.code == code]
    assert found, rejection.to_dict()
    assert all(arg in i.related_paths for i in found), [(i.path, i.related_paths) for i in found]
    return found


def test_fit_through_frame_edits():
    """MODEL-006 §11 item 5: the same failures through frame commands, with the argument in related_paths."""
    # SetFootprintDimensions: 8'-6" bays leave no room (8'-9" is the straw bale minimum, D076).
    rejection = reject("SetFootprintDimensions", {"width_m": 3 * 8.5 * FT, "depth_m": FP.depth_m})
    found = [i for i in rejection.issues if i.code in ("OPENING_OUTSIDE_WALL", "OPENING_CROSSES_BRACE")]
    assert found and all("args.width_m" in i.related_paths and epath(FP.id, "width_m") in i.related_paths for i in found)
    assert {i.path.rsplit(".", 1)[1] for i in found} == {"width_m"}
    # ...and 8'-9" bays are accepted.
    accept("SetFootprintDimensions", {"width_m": 3 * (8 * FT + 9 * IN), "depth_m": FP.depth_m})
    # SetTimberGrid: a shorter first bay.
    x_lines = [{"id": "x0", "fraction": 0.0}, {"id": "x1", "fraction": 0.2}, {"id": "x2", "fraction": 2 / 3}, {"id": "x3", "fraction": 1.0}]
    y_lines = [{"id": line.id, "fraction": line.fraction} for line in GRID.y_lines]
    _related_args(reject("SetTimberGrid", {"x_lines": x_lines, "y_lines": y_lines}), "OPENING_OUTSIDE_WALL", "args.x_lines")
    # SetStoryHeights: a tall window, then a lower story.
    o = opening_on(BASE, L1_WALL)
    tall = accept("SetOpening", set_opening(o, height_m=9 * FT - 0.9144 - T)).candidate  # v1 = H
    _related_args(reject("SetStoryHeights", {"story_heights_m": [L0.story_height_m, 8.5 * FT]}, tall), "OPENING_OUTSIDE_WALL", "args.story_heights_m[1]")
    # SetFrameParameters: a window near the start post clears a 3'-0" brace, not a 4'-0" one.
    near = accept("SetOpening", set_opening(o, offset_m=1.5 * FT + T)).candidate  # u0 = 1'-6"
    params = FRAME.parameters.model_dump() | {"knee_brace_leg_m": 4 * FT}
    _related_args(reject("SetFrameParameters", params, near), "OPENING_CROSSES_BRACE", "args.knee_brace_leg_m")
    # SetWallAssembly: a window that fits with bucks but not under a 2x8 header.
    snug = accept("SetOpening", set_opening(o, height_m=9 * FT - 0.9144 - 2 * IN)).candidate
    found = _related_args(reject("SetWallAssembly", {"assembly_definition_id": STUD.id}, snug), "OPENING_OUTSIDE_WALL", "args.assembly_definition_id")
    assert found[0].path == epath(o.id, "height_m")


def test_girt_fit_edge_case():
    """MODEL-006 §5.2: with one girt, L = 4'-0" and H = 8'-0" is rejected while stud infill is used."""
    low = accept("SetStoryHeights", {"story_heights_m": [8 * FT, 8 * FT]}).candidate
    params = FRAME.parameters.model_dump() | {"knee_brace_leg_m": 4 * FT}
    braced = accept("SetFrameParameters", params, low).candidate  # accepted with straw bale
    rejection = reject("SetWallAssembly", {"assembly_definition_id": STUD.id}, braced)
    girt = [i for i in rejection.issues if i.code == "GIRT_CROSSES_BRACE"]
    assert [i.path for i in girt] == [epath(STUD.id, "layers", 2, "framing", "girt_count")] * 2  # once per level
    assert all({"args.assembly_definition_id", epath(FRAME.id, "parameters", "knee_brace_leg_m")} <= set(i.related_paths) for i in girt)
    unbraced = accept("SetFrameParameters", params | {"knee_braces_level_1": False, "knee_braces_eave": False}, braced).candidate
    accept("SetWallAssembly", {"assembly_definition_id": STUD.id}, unbraced)
    # Through the frame edit itself, with stud infill already in use.
    stud_low = accept("SetStoryHeights", {"story_heights_m": [8 * FT, 8 * FT]}, STUD_BASE).candidate
    rejection = reject("SetFrameParameters", params, stud_low)
    assert all("args.knee_brace_leg_m" in i.related_paths for i in rejection.issues if i.code == "GIRT_CROSSES_BRACE")
    assert "GIRT_CROSSES_BRACE" in codes_of(rejection)


# --- 7: SetWallAssembly (AC2b-03) --------------------------------------------------------------------------


def test_set_wall_assembly():
    change = accept("SetWallAssembly", {"assembly_definition_id": STUD.id})
    assert change.classification == "consequential" and change.confirmation_required
    assert change.members.to_dict() == change.connections.to_dict() == {"added": [], "removed": [], "updated": []}
    assert len(of_kind(change.candidate, "TimberMember")) == 193 and len(of_kind(change.candidate, "Connection")) == 312
    assert len(change.wall_framing.added) == 246 and len(change.wall_framing.removed) == 79
    assert sorted(change.walls.updated) == sorted(w.id for w in of_kind(BASE, "Wall"))
    assert {c["entity_kind"] for c in change.changes} == {"WallSystem"}
    back = accept("SetWallAssembly", {"assembly_definition_id": STRAW.id}, change.candidate)
    assert {r["generation_key"] for r in back.wall_framing.added} == {p.generation_key for p in of_kind(BASE, "WallFramingPiece")}
    noop = accept("SetWallAssembly", {"assembly_definition_id": STRAW.id})
    assert noop.is_noop and not noop.confirmation_required and noop.wall_framing.to_dict() == {"added": [], "removed": [], "updated": []}
    assert issues(reject("SetWallAssembly", {"assembly_definition_id": FP.id})) == [("WRONG_REFERENCE_KIND", "args.assembly_definition_id", set())]
    assert issues(reject("SetWallAssembly", {"assembly_definition_id": str(uuid.uuid4())})) == [("DANGLING_REFERENCE", "args.assembly_definition_id", set())]


def test_set_wall_assembly_needs_a_preview():
    from homedesign.project import MemoryStore, ProjectService
    from homedesign.project.errors import PreviewRequired

    svc = ProjectService(MemoryStore(), token_key=b"test-preview-signing-key-0123456")
    now = datetime(2026, 11, 22, 12, 0, tzinfo=UTC)
    pid = svc.create_project({"command_id": str(uuid.uuid4()), "type": "CreateReferenceProject", "args": {}}, actor_id=ACTOR, now=now).project_id
    head = svc.get_project(pid)["head_revision_id"]
    stud = next(e for e in svc.get_revision(pid, head).entities if e.kind == "AssemblyDefinition" and e.label == "stud-infill")
    command = {"command_id": str(uuid.uuid4()), "project_id": pid, "base_revision_id": head, "type": "SetWallAssembly", "args": {"assembly_definition_id": stud.id}}
    with pytest.raises(PreviewRequired):
        svc.commit(pid, command, actor_id=ACTOR, now=now)
    preview = svc.preview(pid, command, actor_id=ACTOR, now=now)
    committed = svc.commit(pid, command, preview.preview_token, actor_id=ACTOR, now=now)
    assert committed.http_status == 201
    stored = svc.get_revision(pid, committed.revision_id)
    added = {r["id"] for r in preview.body["wall_framing"]["added"]}
    assert added == {e.id for e in stored.entities if e.kind == "WallFramingPiece"}  # added IDs equal the commit's

    from api_support import conforms

    conforms("PreviewResponse", json.loads(json.dumps(preview.body)))
    # Opening commands are routine: committed without a preview.
    o = next(e for e in stored.entities if e.kind == "Opening")
    routine = {"command_id": str(uuid.uuid4()), "project_id": pid, "base_revision_id": committed.revision_id, "type": "SetOpening",
               "args": {"opening_id": o.id, "width_m": o.width_m, "height_m": o.height_m, "sill_height_m": o.sill_height_m, "offset_m": o.offset_m + 0.01}}
    assert svc.commit(pid, routine, actor_id=ACTOR, now=now).http_status == 201


# --- 8: opening commands (AC2b-04) ----------------------------------------------------------------------------


def _only_one_wall(change, key):
    for entry in (*change.wall_framing.added, *change.wall_framing.removed):
        assert entry["generation_key"].startswith(key + "/")
    wall_id = wall(change.candidate, key).id
    assert set(change.walls.updated) <= {wall_id} and not change.walls.added and not change.walls.removed
    assert change.members.to_dict() == change.connections.to_dict() == {"added": [], "removed": [], "updated": []}
    assert change.classification == "routine" and not change.confirmation_required


@pytest.mark.parametrize("family,base", FAMILIES)
def test_opening_commands(family, base):
    key = L1_WALL
    w = wall(base, key)
    added = accept("AddOpening", {"wall_id": w.id, "opening_kind": "WINDOW", "width_m": 1 * FT, "height_m": 1 * FT, "sill_height_m": 6 * FT, "offset_m": 9 * FT}, base)
    new_id = mint("entity", P, ACTOR, CID, "opening")
    assert [(c["entity_id"], c["field"]) for c in added.changes if c["entity_kind"] == "Opening"] == [(new_id, "")]
    assert new_id in one(added.candidate, "WallSystem").opening_ids
    _only_one_wall(added, key)
    assert added.wall_framing.added
    moved = accept("SetOpening", {"opening_id": new_id, "width_m": 1 * FT, "height_m": 1 * FT, "sill_height_m": 6 * FT, "offset_m": 9 * FT - 0.05}, added.candidate)
    _only_one_wall(moved, key)
    assert moved.wall_framing.updated and [c["field"] for c in moved.changes] == ["offset_m"]
    same = accept("SetOpening", {"opening_id": new_id, "width_m": 1 * FT, "height_m": 1 * FT, "sill_height_m": 6 * FT, "offset_m": 9 * FT}, added.candidate)
    assert same.is_noop
    removed = accept("RemoveOpening", {"opening_id": new_id}, added.candidate)
    _only_one_wall(removed, key)
    assert {r["generation_key"] for r in removed.wall_framing.removed} == {r["generation_key"] for r in added.wall_framing.added}


def test_opening_command_errors_carry_their_paths():
    o = opening_on(BASE, L1_WALL)
    w = wall(BASE, L1_WALL)
    good = {"wall_id": w.id, "opening_kind": "WINDOW", "width_m": 1 * FT, "height_m": 1 * FT, "sill_height_m": 6 * FT, "offset_m": 9 * FT}
    assert issues(reject("AddOpening", {**good, "wall_id": str(uuid.uuid4())})) == [("DANGLING_REFERENCE", "args.wall_id", set())]
    assert issues(reject("AddOpening", {**good, "wall_id": o.id})) == [("WRONG_REFERENCE_KIND", "args.wall_id", set())]
    assert issues(reject("AddOpening", {**good, "opening_kind": "SKYLIGHT"})) == [("INVALID_ENUM", "args.opening_kind", set())]
    new_id = mint("entity", P, ACTOR, CID, "opening")
    for name, value, code in (("width_m", 0.0, "OUT_OF_RANGE"), ("height_m", -1.0, "OUT_OF_RANGE"), ("sill_height_m", -0.1, "OUT_OF_RANGE"), ("offset_m", -0.1, "OUT_OF_RANGE")):
        assert issues(reject("AddOpening", {**good, name: value})) == [(code, epath(new_id, name), {f"args.{name}"})]
    assert issues(reject("AddOpening", {**good, "opening_kind": "DOOR"})) == [("UNSUPPORTED_VALUE", epath(new_id, "sill_height_m"), {epath(new_id, "opening_kind"), "args.sill_height_m", "args.opening_kind"})]
    assert issues(reject("SetOpening", {"opening_id": w.id, "width_m": 1.0, "height_m": 1.0, "sill_height_m": 1.0, "offset_m": 1.0})) == [("WRONG_REFERENCE_KIND", "args.opening_id", set())]
    assert issues(reject("RemoveOpening", {"opening_id": str(uuid.uuid4())})) == [("DANGLING_REFERENCE", "args.opening_id", set())]
    rejection = reject("SetOpening", set_opening(o, width_m=20 * FT))
    assert ("OPENING_OUTSIDE_WALL", epath(o.id, "width_m")) in {(i.code, i.path) for i in rejection.issues}
    assert all("args.width_m" in i.related_paths for i in rejection.issues if i.path == epath(o.id, "width_m"))
    assert issues(reject("SetOpening", {"opening_id": o.id, "width_m": 1.0, "height_m": 1.0, "sill_height_m": 1.0})) == [("MISSING_FIELD", "args.offset_m", set())]


# --- 9, 10: removed with the wall; undo -------------------------------------------------------------------------


def test_openings_are_removed_with_their_wall():
    """A perimeter line insertion retires the split walls; their openings are listed in the preview."""
    x_lines = [{"id": "x0", "fraction": 0.0}, {"fraction": 1 / 6}, {"id": "x1", "fraction": 1 / 3}, {"id": "x2", "fraction": 2 / 3}, {"id": "x3", "fraction": 1.0}]
    y_lines = [{"id": line.id, "fraction": line.fraction} for line in GRID.y_lines]
    change = accept("SetTimberGrid", {"x_lines": x_lines, "y_lines": y_lines})
    split = {k for k in (w.generation_key for w in of_kind(BASE, "Wall")) if "/x0-x1/" in k}
    assert len(split) == 4
    assert {r["generation_key"] for r in change.walls.removed} == split
    gone = {opening_on(BASE, k).id for k in split}
    removals = [c for c in change.changes if c["entity_kind"] == "Opening"]
    assert {c["entity_id"] for c in removals} == gone and all(c["after"] is None and c["field"] == "" for c in removals)
    assert any(c["entity_kind"] == "WallSystem" and c["field"] == "opening_ids" for c in change.changes)
    assert {r["generation_key"].split("/opening/")[1].split("/")[0] for r in change.wall_framing.removed} == gone
    assert len(of_kind(change.candidate, "Opening")) == 16 and len(of_kind(change.candidate, "Wall")) == 24
    # Every other opening keeps its ID, wall, offset, and size.
    kept = {o.id: o for o in of_kind(change.candidate, "Opening")}
    for o in of_kind(BASE, "Opening"):
        if o.id not in gone:
            assert kept[o.id] == o


def test_remove_and_undo_restore_original_ids():
    o = opening_on(BASE, L1_WALL)
    removed = accept("RemoveOpening", {"opening_id": o.id})
    restored_studs = {r["id"] for r in removed.wall_framing.added}
    assert not restored_studs  # straw bale: removing an opening only removes its bucks
    undo = accept("UndoToRevision", {"target_revision_id": BASE.revision_id}, removed.candidate, target=BASE)
    assert {(e.id, e.kind) for e in undo.candidate.entities} == {(e.id, e.kind) for e in BASE.entities}
    stud = accept("RemoveOpening", {"opening_id": opening_on(STUD_BASE, L1_WALL).id}, STUD_BASE, cid="66666666-6666-4666-8666-666666666666")
    assert {r["generation_key"].rsplit("/", 1)[1] for r in stud.wall_framing.added} == {"s3"}  # the layout stud comes back
    assert stud.wall_framing.added[0]["id"] not in {e.id for e in STUD_BASE.entities}  # with a new ID (D041)
    undo = accept("UndoToRevision", {"target_revision_id": STUD_BASE.revision_id}, stud.candidate, target=STUD_BASE)
    assert {e.id for e in undo.candidate.entities} == {e.id for e in STUD_BASE.entities}


# --- 11: preview diff ---------------------------------------------------------------------------------------------


def test_preview_diff_shape():
    change = accept("SetFootprintDimensions", {"width_m": 12.192, "depth_m": FP.depth_m}, STUD_BASE)
    preview = change.to_preview_dict()
    for kind in ("walls", "wall_framing"):
        diff = preview[kind]
        for side in ("added", "removed"):
            keys = [r["generation_key"] for r in diff[side]]
            assert keys == sorted(keys, key=lambda k: k.encode("utf-16-be"))
        assert diff["updated"] == sorted(diff["updated"])
    assert {c["entity_kind"] for c in preview["changes"]} <= {"Footprint", "FrameSystem", "WallSystem", "Opening"}
    assert not any(c["entity_kind"] in ("Wall", "WallFramingPiece") for c in preview["changes"])
    before = {e.id for e in STUD_BASE.entities if e.kind == "WallFramingPiece"}
    after = {e.id for e in change.candidate.entities if e.kind == "WallFramingPiece"}
    assert {r["id"] for r in preview["wall_framing"]["added"]} == after - before
    assert {r["id"] for r in preview["wall_framing"]["removed"]} == before - after
    assert not preview["walls"]["added"] and not preview["walls"]["removed"]  # every key survives (ASM-001 §6.2)
    assert len(preview["walls"]["updated"]) == 16  # all but the four on x0, which do not move


# --- 12: classification -----------------------------------------------------------------------------------------


def test_classification_of_the_new_commands():
    assert {k: CLASSIFICATION[k] for k in ("SetWallAssembly", "AddOpening", "SetOpening", "RemoveOpening")} == {
        "SetWallAssembly": "consequential", "AddOpening": "routine", "SetOpening": "routine", "RemoveOpening": "routine",
    }


# --- 13: robustness ----------------------------------------------------------------------------------------------

_any = st.one_of(st.none(), st.booleans(), st.integers(-3, 3), st.floats(allow_nan=False, allow_infinity=False, min_value=-50, max_value=50), st.text(max_size=8))
_ids = st.sampled_from([e.id for e in BASE.entities if e.kind in ("Wall", "Opening", "AssemblyDefinition", "Section")] + [str(uuid.uuid4())])
_len = st.floats(-1.0, 6.0, allow_nan=False)


@settings(max_examples=60, suppress_health_check=[HealthCheck.too_slow])
@given(
    type_=st.sampled_from(["SetWallAssembly", "AddOpening", "SetOpening", "RemoveOpening"]),
    args=st.one_of(
        st.fixed_dictionaries({"assembly_definition_id": _ids}),
        st.fixed_dictionaries({"wall_id": _ids, "opening_kind": st.sampled_from(["WINDOW", "DOOR", "X"]), "width_m": _len, "height_m": _len, "sill_height_m": _len, "offset_m": _len}),
        st.fixed_dictionaries({"opening_id": _ids, "width_m": _len, "height_m": _len, "sill_height_m": _len, "offset_m": _len}),
        st.fixed_dictionaries({"opening_id": _ids}),
        st.dictionaries(st.text(max_size=12), _any, max_size=4),
    ),
)
def test_new_commands_never_raise(type_, args):
    result = run(type_, args)
    if result.accepted:
        assert validate_value(result.change.candidate.model_dump(mode="json")).valid


# --- 14: schemas --------------------------------------------------------------------------------------------------


def test_model_006_examples_validate_against_the_committed_schema():
    """MODEL-006 §4's examples, with placeholder IDs filled in, validate against snapshot.v3.schema.json."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    text = (REPO_ROOT / "docs/implementation/tasks/MODEL-006.md").read_text(encoding="utf-8")
    section = text[text.index("## 4. Version 3 records"):text.index("## 5. Fit rules")]
    blocks = re.findall(r"```json\n(.*?)```", section, flags=re.DOTALL)
    assert len(blocks) == 5
    filler = "00000000-0000-4000-8000-00000000f111"

    def fill(value, key=""):
        if isinstance(value, dict):
            return {k: fill(v, k) for k, v in value.items()}
        if isinstance(value, list):
            return [fill(v, key) for v in value]
        if isinstance(value, str) and (key == "id" or key.endswith("_id") or key.endswith("_ids")) and not re.fullmatch(r"[0-9a-f-]{36}", value):
            return filler
        return value

    seen = set()
    for block in blocks:
        record = fill(json.loads(block))
        seen.add(record["kind"])
        validator = jsonschema.Draft202012Validator({"$schema": schema["$schema"], "$defs": schema["$defs"], "$ref": f"#/$defs/{record['kind']}"})
        validator.validate(record)
    assert seen == {"WallSystem", "AssemblyDefinition", "Wall", "WallFramingPiece", "Opening"}


# --- ASM-001 §11 items 7–8: identity under each edit (§6.2), and openings survive -------------------------


def _keys(snapshot, kind):
    return {e.generation_key: e.id for e in of_kind(snapshot, kind)}


def _diff_keys(change, kind):
    diff = change.walls if kind == "Wall" else change.wall_framing
    return {r["generation_key"] for r in diff.added}, {r["generation_key"] for r in diff.removed}


def _openings_kept(before, after):
    assert {o.id: o for o in of_kind(after, "Opening")} == {o.id: o for o in of_kind(before, "Opening")}


def test_identity_footprint():
    """Every key survives; pieces move; the bay's far end gains studs; openings keep their offsets."""
    change = accept("SetFootprintDimensions", {"width_m": 12.192, "depth_m": FP.depth_m}, STUD_BASE)
    added, removed = _diff_keys(change, "WallFramingPiece")
    assert not removed and not _diff_keys(change, "Wall")[0] and not _diff_keys(change, "Wall")[1]
    assert added and all(re.search(r"/stud/s\d+$", k) for k in added)  # 13'-4" bays: one more stud each
    assert {k.rsplit("/", 1)[1] for k in added} == {"s6"}
    _openings_kept(STUD_BASE, change.candidate)
    for key, piece_id in _keys(STUD_BASE, "WallFramingPiece").items():
        assert _keys(change.candidate, "WallFramingPiece")[key] == piece_id


def test_identity_story_heights():
    """Girts move with H; every key survives while each girt still crosses its opening."""
    change = accept("SetStoryHeights", {"story_heights_m": [11 * FT, 9 * FT]}, STUD_BASE)
    assert _diff_keys(change, "WallFramingPiece") == (set(), set()) and _diff_keys(change, "Wall") == (set(), set())
    moved = {next(e.generation_key for e in of_kind(STUD_BASE, "WallFramingPiece") if e.id == i) for i in change.wall_framing.updated}
    assert any("/girt/" in k for k in moved)
    # A raised window crosses the 5'-0" girt of a 10'-0" story, and not the 4'-6" girt of a 9'-0" one.
    key = "wall/axis-y/x0/y0-y1/level-0"
    o = opening_on(STUD_BASE, key)
    raised = accept("SetOpening", set_opening(o, sill_height_m=5 * FT, height_m=2 * FT), STUD_BASE).candidate
    lower = accept("SetStoryHeights", {"story_heights_m": [9 * FT, 9 * FT]}, raised)
    added, removed = _diff_keys(lower, "WallFramingPiece")
    assert not added and removed == {f"{key}/girt/g1/after/{o.id}"}
    _openings_kept(raised, lower.candidate)


@pytest.mark.parametrize("params", [{"knee_brace_leg_m": 2.5 * FT}, {"knee_braces_eave": False}])
def test_identity_brace_parameters(params):
    """Vertical pieces near the posts change length; every key survives; walls do not change."""
    change = accept("SetFrameParameters", FRAME.parameters.model_dump() | params, STUD_BASE)
    assert _diff_keys(change, "WallFramingPiece") == (set(), set())
    assert change.wall_framing.updated and set(change.walls.updated) == set()
    assert not change.walls.added and not change.walls.removed


@pytest.mark.parametrize("type_,args", [
    ("SetFrameParameters", FRAME.parameters.model_dump() | {"joist_spacing_m": 0.4064, "purlins_per_slope": 3}),
    ("SetGableRoofParameters", {"pitch_rad": 0.5, "eave_overhang_m": 0.3}),
    ("SetMemberSection", {"role": "BEAM", "section_id": next(s.id for s in of_kind(BASE, "Section") if s.nominal_label == "8x10")}),
    ("SetConnectionType", {"junction_class": "post-beam", "connection_type": "STEEL_KNIFE_PLATE"}),
])
def test_identity_frame_only_edits(type_, args):
    """The wall rule reads no roof value, joist, purlin, or member section (D058): no wall change."""
    change = accept(type_, args, STUD_BASE)
    assert change.walls.to_dict() == change.wall_framing.to_dict() == {"added": [], "removed": [], "updated": []}


def test_identity_set_wall_assembly():
    change = accept("SetWallAssembly", {"assembly_definition_id": STRAW.id}, STUD_BASE)
    assert {r["generation_key"] for r in change.wall_framing.removed} == set(_keys(STUD_BASE, "WallFramingPiece"))
    assert {r["generation_key"] for r in change.wall_framing.added} == set(_keys(BASE, "WallFramingPiece"))
    assert set(_keys(change.candidate, "Wall").items()) == set(_keys(STUD_BASE, "Wall").items())  # every wall keeps its ID


def test_identity_opening_commands():
    """AddOpening retires the studs it claims, shortens the girt before it, and adds `after/{id}`;
    SetOpening keeps its keys (jacks come and go across the threshold); RemoveOpening reverses it."""
    w = wall(STUD_BASE, L1_WALL)
    o = opening_on(STUD_BASE, L1_WALL)
    added = accept("AddOpening", {"wall_id": w.id, "opening_kind": "WINDOW", "width_m": 1.5 * FT, "height_m": 1 * FT, "sill_height_m": 4 * FT, "offset_m": 8.5 * FT}, STUD_BASE)
    new_id = mint("entity", P, ACTOR, CID, "opening")
    plus, minus = _diff_keys(added, "WallFramingPiece")
    assert minus == {f"{L1_WALL}/stud/s5"}  # the layout stud at 10'-0" overlaps the end king: dropped
    assert f"{L1_WALL}/girt/g1/after/{new_id}" in plus and all(k.startswith(f"{L1_WALL}/") for k in plus)
    after_old = _keys(STUD_BASE, "WallFramingPiece")[f"{L1_WALL}/girt/g1/after/{o.id}"]
    assert after_old in added.wall_framing.updated  # survives, shortened
    wider = accept("SetOpening", {"opening_id": new_id, "width_m": 1.5 * FT, "height_m": 1 * FT, "sill_height_m": 4 * FT, "offset_m": 8.52 * FT}, added.candidate)
    assert _diff_keys(wider, "WallFramingPiece") == (set(), set())  # its keys survive and move
    jacked = accept("SetOpening", set_opening(o, width_m=4 * FT + 2 * EPS, offset_m=4 * FT), STUD_BASE)
    plus, minus = _diff_keys(jacked, "WallFramingPiece")
    assert {k.rsplit(f"/{o.id}/", 1)[1] for k in plus if f"/{o.id}/" in k} >= {"jack/start", "jack/end"}
    removed = accept("RemoveOpening", {"opening_id": new_id}, added.candidate, cid="55555555-5555-4555-8555-555555555555")
    plus, minus = _diff_keys(removed, "WallFramingPiece")
    assert plus == {f"{L1_WALL}/stud/s5"} and _keys(removed.candidate, "WallFramingPiece")[f"{L1_WALL}/stud/s5"] != _keys(STUD_BASE, "WallFramingPiece")[f"{L1_WALL}/stud/s5"]
    undo = accept("UndoToRevision", {"target_revision_id": STUD_BASE.revision_id}, removed.candidate, target=STUD_BASE)
    assert _keys(undo.candidate, "WallFramingPiece") == _keys(STUD_BASE, "WallFramingPiece")  # original IDs (D044)


def test_golden_grid_step_keeps_the_x0_x2_walls():
    """MODEL-006 §10: four 10' bays along X after a 40' width; the x2-x3 walls and their windows are retired."""
    wide = accept("SetFootprintDimensions", {"width_m": 12.192, "depth_m": FP.depth_m}).candidate
    x_lines = [{"id": "x0", "fraction": 0.0}, {"id": "x1", "fraction": 0.25}, {"id": "x2", "fraction": 0.5}, {"fraction": 0.75}, {"id": "x3", "fraction": 1.0}]
    y_lines = [{"id": line.id, "fraction": line.fraction} for line in GRID.y_lines]
    change = accept("SetTimberGrid", {"x_lines": x_lines, "y_lines": y_lines}, wide, cid="44444444-4444-4444-8444-444444444444")
    removed = {r["generation_key"] for r in change.walls.removed}
    assert removed == {f"wall/axis-x/{y}/x2-x3/level-{i}" for y in ("y0", "y2") for i in (0, 1)}
    assert len(change.walls.added) == 8 and len(of_kind(change.candidate, "Wall")) == 24 and len(of_kind(change.candidate, "Opening")) == 16
    gone = [c for c in change.changes if c["entity_kind"] == "Opening"]
    assert len(gone) == 4 and sorted(c["before"]["width_m"] for c in gone) == [0.9144, 0.9144, 0.9144, 1.524]
    for key, offset in (("wall/axis-x/y0/x0-x1/level-0", 3.5 * FT), ("wall/axis-x/y2/x1-x2/level-1", 4.5 * FT)):
        assert opening_on(change.candidate, key).offset_m == pytest.approx(offset)
