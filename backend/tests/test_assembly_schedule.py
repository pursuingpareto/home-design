"""ART-003 §4 and §13 tests 1–6: the `assembly_schedule` payload (D070, D071, D082, D084).

Reference figures are ART-003 §4.4 and §4.6 (measured with the drafting prototype); thermal arithmetic
and gating use test-only declared values, because every value in the template is null (D072).
"""

from __future__ import annotations

import copy
import json
from collections import Counter

import jsonschema
import pytest

from conftest import FIXTURE, REPO_ROOT, STUD_INFILL, entities_of
from homedesign.assemblies.schedule import ASSEMBLY_SCHEDULE, ASSUMPTIONS, build_assembly_schedule, select_assembly_schedule
from homedesign.assemblies.thermal import NOTES
from homedesign.assemblies.walls import VERTICAL_KINDS, framing_face, in_plane_m, overlap_area
from homedesign.model.jcs import canonical_json
from homedesign.model.schema import Snapshot
from homedesign.project import MemoryStore, ProjectService
from homedesign.timber.schedule import reference_length
from test_project import KEY, T0, create

SCHEMA = json.loads((REPO_ROOT / "docs/architecture/schemas/artifacts.v1.schema.json").read_text())
SF = 0.09290304  # m² per square foot


def schedule_of(doc):
    return build_assembly_schedule(select_assembly_schedule(Snapshot.model_validate(doc)))


STRAW = schedule_of(FIXTURE)
STUD = schedule_of(STUD_INFILL)


def by_key(items):
    return {i["generation_key"]: i for i in items}


def code_unit_sorted(keys):
    return keys == sorted(keys, key=lambda k: k.encode("utf-16-be"))


def validate(payload):
    jsonschema.Draft202012Validator({**SCHEMA, "$ref": "#/$defs/AssemblySchedulePayload"}).validate(payload)


# 1. Inventory and order (§13 test 1) -------------------------------------------------------------


@pytest.mark.parametrize("doc, payload, pieces", [(FIXTURE, STRAW, 79), (STUD_INFILL, STUD, 246)], ids=["straw-bale", "stud-infill"])
def test_rows_are_exactly_the_snapshots_records_in_order(doc, payload, pieces):
    walls, openings, framing = (entities_of(doc, k) for k in ("Wall", "Opening", "WallFramingPiece"))
    assert (len(payload["walls"]), len(payload["openings"]), len(payload["wall_framing"])) == (20, 20, pieces)
    assert {w["wall_id"] for w in payload["walls"]} == {w["id"] for w in walls}
    assert {o["opening_id"] for o in payload["openings"]} == {o["id"] for o in openings}
    assert {p["piece_id"] for p in payload["wall_framing"]} == {p["id"] for p in framing}
    assert code_unit_sorted([w["generation_key"] for w in payload["walls"]])
    assert code_unit_sorted([p["generation_key"] for p in payload["wall_framing"]])
    assert [(o["wall_key"], o["opening_id"]) for o in payload["openings"]] == sorted(
        ((o["wall_key"], o["opening_id"]) for o in payload["openings"]), key=lambda t: (t[0].encode("utf-16-be"), t[1]))
    owner = {pid: w["id"] for w in walls for pid in w["framing_ids"]}
    keys = {w["id"]: w["generation_key"] for w in walls}
    for row in payload["wall_framing"]:
        assert row["wall_id"] == owner[row["piece_id"]] and row["quantity"] == 1
    for row in payload["openings"]:
        assert row["wall_key"] == keys[row["wall_id"]]
        assert not {"offset_m", "sill_height_m"} & set(row)  # no position (§4.3)
    assert not any({"start_m", "end_m", "xy_m"} & set(row) for row in payload["wall_framing"])
    validate(payload)


def test_wall_rows_follow_the_records():
    records = {w["id"]: w for w in entities_of(FIXTURE, "Wall")}
    levels = {lv["id"]: lv["index"] for lv in entities_of(FIXTURE, "Level")}
    sides = Counter()
    for row in STRAW["walls"]:
        wall = records[row["wall_id"]]
        assert row["length_m"] == reference_length(wall["start_m"], wall["end_m"]) and row["height_m"] == wall["height_m"]
        assert row["level_index"] == levels[wall["level_id"]] and row["assembly_label"] == "straw-bale"
        assert row["gross_area_m2"] == row["length_m"] * row["height_m"]
        assert row["net_area_m2"] == row["gross_area_m2"] - row["opening_area_m2"]
        assert row["framing_fraction"] == row["framing_face_area_m2"] / row["net_area_m2"]
        sides[row["elevation_side"]] += 1
        axis, line = row["generation_key"].split("/")[1:3]
        assert row["elevation_side"] == {("axis-x", "y0"): "south", ("axis-x", "y2"): "north", ("axis-y", "x0"): "west", ("axis-y", "x3"): "east"}[axis, line]
    assert sides == {"south": 6, "north": 6, "west": 4, "east": 4}


# 2. Areas (§13 test 2, AC2b-05) ------------------------------------------------------------------


def test_reference_house_areas():
    totals = STRAW["totals"]
    assert (totals["wall_count"], totals["opening_count"]) == (20, 20)
    for name, value, sf in (("gross_area_m2", 211.8189312, 2280), ("opening_area_m2", 24.52640256, 264), ("net_area_m2", 187.29252864, 2016)):
        assert totals[name] == pytest.approx(value, abs=1e-9) and totals[name] / SF == pytest.approx(sf, abs=1e-6)
    assert STRAW["definition_aggregates"] == [{"assembly_label": "straw-bale", "wall_count": 20, "opening_count": 20, "gross_area_m2": totals["gross_area_m2"],
                                               "opening_area_m2": totals["opening_area_m2"], "net_area_m2": totals["net_area_m2"]}]
    assert STRAW["opening_aggregates"] == [{"opening_kind": "DOOR", "count": 1, "area_m2": 0.9144 * 2.032},
                                           {"opening_kind": "WINDOW", "count": 19, "area_m2": pytest.approx(24.52640256 - 0.9144 * 2.032, abs=1e-9)}]


@pytest.mark.parametrize("payload", [STRAW, STUD], ids=["straw-bale", "stud-infill"])
def test_aggregates_reconcile_with_the_rows(payload):
    walls, openings = payload["walls"], payload["openings"]
    per_wall = {w["wall_id"]: 0.0 for w in walls}
    for o in openings:  # row order
        assert o["area_m2"] == o["width_m"] * o["height_m"]
        per_wall[o["wall_id"]] += o["area_m2"]
    assert all(w["opening_area_m2"] == per_wall[w["wall_id"]] for w in walls)
    net = sum(w["net_area_m2"] for w in walls)
    fill = sum(w["net_area_m2"] - w["framing_face_area_m2"] for w in walls)
    for layer in payload["layer_aggregates"]:
        expected = fill if layer["function"] == "FRAMING" else net
        assert layer["area_m2"] == pytest.approx(expected, rel=1e-12)
        assert layer["volume_m3"] == layer["area_m2"] * layer["thickness_m"]
    assert sum(a["count"] for a in payload["opening_aggregates"]) == len(openings)
    assert payload["totals"]["framing_face_area_m2"] == pytest.approx(sum(w["framing_face_area_m2"] for w in walls), rel=1e-12)


def test_layer_aggregates_and_the_fill_net_of_framing():
    """§4.6, D082: non-framing layers at net area; the bales and the cellulose net of framing."""
    straw = [(a["layer"], a["function"], a["material_name"], a["thickness_m"]) for a in STRAW["layer_aggregates"]]
    assert straw == [("lime-plaster", "FINISH", "Lime plaster", 0.0381), ("bales", "FRAMING", "Straw", 0.4572), ("clay-plaster", "FINISH", "Clay plaster", 0.0254)]
    bales = STRAW["layer_aggregates"][1]
    assert bales["area_m2"] == pytest.approx(183.807697, abs=1e-6) and bales["volume_m3"] == pytest.approx(84.0369, abs=1e-4)
    stud = [(a["layer"], a["function"], a["material_name"]) for a in STUD["layer_aggregates"]]
    assert stud == [("siding", "FINISH", "Wood siding"), ("sheathing", "SHEATHING", "Sheathing"), ("framing", "FRAMING", "Dense-pack cellulose"),
                    ("gypsum-board", "FINISH", "Gypsum board")]
    cellulose = STUD["layer_aggregates"][2]
    assert cellulose["area_m2"] == pytest.approx(167.135956, abs=1e-6) and cellulose["volume_m3"] == pytest.approx(23.3489, abs=1e-4)


# 3. Framing (§13 test 3) -------------------------------------------------------------------------

STRAW_FRAMING = [("BUCK_HEAD", "1.5x18", 20, 19.5072), ("BUCK_JAMB", "1.5x18", 40, 53.3654), ("BUCK_SILL", "1.5x18", 19, 18.5928)]
STUD_FRAMING = [("CRIPPLE", "2x6", 47, 34.7345), ("GIRT", "2x6", 40, 51.9684), ("HEADER", "2x8", 20, 19.6596), ("JACK", "2x6", 4, 8.5344),
                ("KING", "2x6", 40, 115.824), ("ROUGH_SILL", "2x6", 19, 18.5928), ("STUD", "2x6", 76, 207.264)]


@pytest.mark.parametrize("payload, table", [(STRAW, STRAW_FRAMING), (STUD, STUD_FRAMING)], ids=["straw-bale", "stud-infill"])
def test_framing_aggregates(payload, table):
    got = payload["framing_aggregates"]
    assert [(a["piece_kind"], a["nominal_section"], a["count"]) for a in got] == [t[:3] for t in table]
    for a, (_, _, n, total) in zip(got, table, strict=True):
        assert a["total_length_m"] == pytest.approx(total, abs=1e-4)
        rows = [r["length_m"] for r in payload["wall_framing"] if (r["piece_kind"], r["nominal_section"]) == (a["piece_kind"], a["nominal_section"])]
        assert len(rows) == n and abs(a["total_length_m"] - sum(rows)) <= 1e-6 * n
    assert sum(a["count"] for a in got) == len(payload["wall_framing"])


def test_has_jacks_follows_the_pieces():
    for payload, expected in ((STRAW, 0), (STUD, 2)):
        jacked = {r["opening_id"] for r in payload["wall_framing"] if r["piece_kind"] == "JACK"}
        assert all(o["has_jacks"] == (o["opening_id"] in jacked) for o in payload["openings"])
        assert sum(o["has_jacks"] for o in payload["openings"]) == expected
    assert {o["width_m"] for o in STUD["openings"] if o["has_jacks"]} == {1.524}  # the 5'-0" windows, above the 4'-0" threshold


# 4. Framing fraction (§13 test 4, AC2b-06) -------------------------------------------------------


def faces(doc):
    """Per wall key: every piece's face (from the records), for an all-pairs check."""
    snapshot = Snapshot.model_validate(doc)
    by_id = {e.id: e for e in snapshot.entities}
    out = {}
    for wall in (e for e in snapshot.entities if e.kind == "Wall"):
        along = 0 if wall.generation_key.split("/")[1] == "axis-x" else 1
        pieces = sorted((by_id[i] for i in wall.framing_ids), key=lambda p: p.generation_key.encode("utf-16-be"))
        out[wall.generation_key] = [
            (p, framing_face(p.piece_kind, p.start_m, p.end_m, in_plane_m(p.piece_kind, by_id[p.section_id].actual_width_m, by_id[p.section_id].actual_depth_m), along))
            for p in pieces
        ]
    return out


@pytest.mark.parametrize("doc, payload", [(FIXTURE, STRAW), (STUD_INFILL, STUD)], ids=["straw-bale", "stud-infill"])
def test_faces_overlap_only_at_girt_crossings_and_count_once(doc, payload):
    rows = by_key(payload["walls"])
    crossings_total = 0.0
    for key, items in faces(doc).items():
        crossings = 0.0
        for i, (p, a) in enumerate(items):
            for q, b in items[i + 1:]:
                area = overlap_area(a, b)
                if area is None:
                    continue
                kinds = {p.piece_kind, q.piece_kind}
                assert "GIRT" in kinds and kinds - {"GIRT"} <= VERTICAL_KINDS and len(kinds) == 2, (key, p.generation_key, q.generation_key)
                crossings += area
        naive = sum((f.u_hi - f.u_lo) * (f.v_hi - f.v_lo) for _, f in items)
        assert rows[key]["framing_face_area_m2"] == pytest.approx(naive - crossings, rel=1e-12, abs=1e-15)
        crossings_total += crossings
    assert crossings_total == (0.0 if payload is STRAW else pytest.approx(0.110322, abs=1e-6))


def test_reference_house_framing_fractions():
    """§4.4's table: whole-house 1.86% and 10.76%; per wall by opening."""
    for payload, face, whole in ((STRAW, 3.484832, 0.0186), (STUD, 20.156573, 0.1076)):
        totals = payload["totals"]
        assert totals["framing_face_area_m2"] == pytest.approx(face, abs=1e-6)
        assert totals["framing_face_area_m2"] / totals["net_area_m2"] == pytest.approx(whole, abs=5e-5)
    widths = {o["wall_id"]: (o["opening_kind"], o["width_m"]) for o in STRAW["openings"]}

    def table(payload):
        groups: dict = {}
        for w in payload["walls"]:
            kind, width = widths[w["wall_id"]]
            group = "door" if kind == "DOOR" else "5'-0\"" if width == 1.524 else f"3'-0\", level {w['level_index']}"
            groups.setdefault(group, set()).add(round(w["framing_fraction"], 4))
        return groups

    assert table(STRAW) == {"5'-0\"": {0.0231}, "door": {0.0207}, "3'-0\", level 0": {0.0168}, "3'-0\", level 1": {0.0189}}
    assert table(STUD) == {"5'-0\"": {0.1305}, "door": {0.1043}, "3'-0\", level 0": {0.1030}, "3'-0\", level 1": {0.1068}}


# 5. Definitions and thermal figures (§13 test 5, AC2b-06) ----------------------------------------


def test_only_definitions_in_use_are_listed_with_their_values_as_stored():
    for payload, label in ((STRAW, "straw-bale"), (STUD, "stud-infill")):
        (definition,) = payload["definitions"]
        record = next(e for e in entities_of(FIXTURE, "AssemblyDefinition") if e["label"] == label)
        assert (definition["assembly_definition_id"], definition["family"], definition["installation_note"]) == (record["id"], record["family"], record["installation_note"])
        assert definition["unverified_climate_details"] == record["unverified_climate_details"]
        assert [layer["name"] for layer in definition["layers"]] == [layer["name"] for layer in record["layers"]]
        assert definition["total_thickness_m"] == pytest.approx(sum(layer["thickness_m"] for layer in record["layers"]), abs=1e-12)
        for ours, stored in zip(definition["layers"], record["layers"], strict=True):
            for name in ("thermal_conductivity_w_m_k", "thermal_resistance_m2_k_w", "vapor_permeance_kg_pa_s_m2"):
                assert ours[name] == stored[name] is None
    buck = STRAW["definitions"][0]["layers"][1]["framing"]
    assert buck == {"type": "BUCK", "framing_material_id": buck["framing_material_id"], "framing_material_name": "Spruce-pine-fir",
                    "framing_thermal_conductivity_w_m_k": None, "buck_section": "1.5x18", "girt_count": 0}
    stud = STUD["definitions"][0]["layers"][2]["framing"]
    assert {k: stud[k] for k in ("stud_section", "stud_spacing_m", "girt_count", "girt_section", "header_section", "jack_threshold_width_m")} == {
        "stud_section": "2x6", "stud_spacing_m": 0.6096, "girt_count": 1, "girt_section": "2x6", "header_section": "2x8", "jack_threshold_width_m": 1.2192}


def test_reference_house_has_no_thermal_figures_and_names_the_missing_inputs():
    thermal = STRAW["thermal"]
    assert thermal["method"] == {"id": "parallel-path-1", "notes": list(NOTES)} and len(NOTES) == 5
    assert NOTES[2] == "Surface air films are not included."  # D084
    assert all(w["u_value_w_m2_k"] is w["r_value_m2_k_w"] is w["ua_w_k"] is None for w in STRAW["walls"])
    assert all(w["framing_fraction"] > 0 for w in STRAW["walls"])
    (entry,) = thermal["definitions"]
    either = ["thermal_conductivity_w_m_k", "thermal_resistance_m2_k_w"]
    plaster = [{"assembly_label": "straw-bale", "layer": "lime-plaster", "fields": either}, {"assembly_label": "straw-bale", "layer": "clay-plaster", "fields": either}]
    fill = {"assembly_label": "straw-bale", "layer": "bales", "fields": ["thermal_conductivity_w_m_k"]}
    framing = {"assembly_label": "straw-bale", "layer": "bales", "fields": ["framing.framing_thermal_conductivity_w_m_k"]}
    assert entry["center_of_cavity"] == {"r_value_m2_k_w": None, "u_value_w_m2_k": None, "missing_inputs": [plaster[0], fill, plaster[1]]}
    assert entry["framing_path"] == {"r_value_m2_k_w": None, "u_value_w_m2_k": None, "missing_inputs": [plaster[0], framing, plaster[1]]}
    union = [plaster[0], fill, framing, plaster[1]]
    for figure in (entry["parallel_path"], thermal["all_walls"]):
        assert figure == {"net_area_m2": STRAW["totals"]["net_area_m2"], "ua_w_k": None, "u_value_w_m2_k": None, "r_value_m2_k_w": None, "missing_inputs": union}


def declared(value):
    return {"value": value, "source": "Test-only value", "date": "2026-11-22", "note": None}


def with_values(doc, label, layers, framing=None):
    """A test-only copy of ``doc`` whose ``label`` definition declares these values (layer name -> fields)."""
    doc = copy.deepcopy(doc)
    record = next(e for e in entities_of(doc, "AssemblyDefinition") if e["label"] == label)
    for layer in record["layers"]:
        for name, value in layers.get(layer["name"], {}).items():
            layer[name] = declared(value)
        if layer["framing"] is not None and framing is not None:
            layer["framing"]["framing_thermal_conductivity_w_m_k"] = declared(framing)
    return doc


STUD_VALUES = {"siding": {"thermal_resistance_m2_k_w": 0.14}, "sheathing": {"thermal_conductivity_w_m_k": 0.12},
               "framing": {"thermal_conductivity_w_m_k": 0.039}, "gypsum-board": {"thermal_conductivity_w_m_k": 0.16}}


def test_parallel_path_arithmetic():
    """§4.8 with declared values: each formula, a resistance and a conductivity both accepted."""
    payload = schedule_of(with_values(STUD_INFILL, "stud-infill", STUD_VALUES, framing=0.12))
    validate(payload)
    r_fill = 0.14 + 0.0127 / 0.12 + 0.1397 / 0.039 + 0.0127 / 0.16
    r_framing = 0.14 + 0.0127 / 0.12 + 0.1397 / 0.12 + 0.0127 / 0.16
    (entry,) = payload["thermal"]["definitions"]
    assert entry["center_of_cavity"]["r_value_m2_k_w"] == pytest.approx(r_fill, rel=1e-12)
    assert entry["center_of_cavity"]["u_value_w_m2_k"] == pytest.approx(1 / r_fill, rel=1e-12)
    assert entry["framing_path"]["r_value_m2_k_w"] == pytest.approx(r_framing, rel=1e-12)
    assert entry["center_of_cavity"]["missing_inputs"] == entry["framing_path"]["missing_inputs"] == []
    ua = 0.0
    for w in payload["walls"]:
        f = w["framing_fraction"]
        u = f / r_framing + (1 - f) / r_fill
        assert w["u_value_w_m2_k"] == pytest.approx(u, rel=1e-12)
        assert w["r_value_m2_k_w"] == pytest.approx(1 / u, rel=1e-12)
        assert w["ua_w_k"] == pytest.approx(u * w["net_area_m2"], rel=1e-12)
        assert 1 / r_fill < w["u_value_w_m2_k"] < 1 / r_framing  # the framing penalty
        ua += w["ua_w_k"]
    net = payload["totals"]["net_area_m2"]
    for figure in (entry["parallel_path"], payload["thermal"]["all_walls"]):
        assert figure["ua_w_k"] == pytest.approx(ua, rel=1e-12) and figure["net_area_m2"] == net
        assert figure["u_value_w_m2_k"] == pytest.approx(ua / net, rel=1e-12)
        assert figure["r_value_m2_k_w"] == pytest.approx(net / ua, rel=1e-12) and figure["missing_inputs"] == []


def test_missing_framing_conductivity_leaves_only_the_center_of_cavity():
    payload = schedule_of(with_values(STUD_INFILL, "stud-infill", STUD_VALUES))
    (entry,) = payload["thermal"]["definitions"]
    assert entry["center_of_cavity"]["r_value_m2_k_w"] is not None and entry["center_of_cavity"]["missing_inputs"] == []
    missing = [{"assembly_label": "stud-infill", "layer": "framing", "fields": ["framing.framing_thermal_conductivity_w_m_k"]}]
    assert entry["framing_path"] == {"r_value_m2_k_w": None, "u_value_w_m2_k": None, "missing_inputs": missing}
    assert entry["parallel_path"]["ua_w_k"] is None and entry["parallel_path"]["missing_inputs"] == missing
    assert payload["thermal"]["all_walls"]["missing_inputs"] == missing
    assert all(w["u_value_w_m2_k"] is None for w in payload["walls"])


def test_a_wall_without_framing_still_needs_the_framing_path():
    """f = 0: a straw bale wall without an opening has no pieces, and gating is by input, not by wall."""
    from conftest import regenerate

    doc = copy.deepcopy(FIXTURE)
    key = "wall/axis-y/x3/y1-y2/level-1"
    wall = next(w for w in entities_of(doc, "Wall") if w["generation_key"] == key)
    gone = {o["id"] for o in entities_of(doc, "Opening") if o["wall_id"] == wall["id"]}
    doc["entities"] = [e for e in doc["entities"] if e["id"] not in gone]
    entities_of(doc, "WallSystem")[0]["opening_ids"] = [i for i in entities_of(doc, "WallSystem")[0]["opening_ids"] if i not in gone]
    doc = regenerate(doc)
    values = {"lime-plaster": {"thermal_conductivity_w_m_k": 0.8}, "bales": {"thermal_conductivity_w_m_k": 0.06}, "clay-plaster": {"thermal_resistance_m2_k_w": 0.03}}
    unknown = schedule_of(with_values(doc, "straw-bale", values))
    row = by_key(unknown["walls"])[key]
    assert (row["framing_face_area_m2"], row["framing_fraction"], row["u_value_w_m2_k"]) == (0.0, 0.0, None)
    known = schedule_of(with_values(doc, "straw-bale", values, framing=0.12))
    r_fill = 0.0381 / 0.8 + 0.4572 / 0.06 + 0.03
    assert by_key(known["walls"])[key]["u_value_w_m2_k"] == pytest.approx(1 / r_fill, rel=1e-12)


def test_assumptions_in_order():
    codes = ["WALLS_ONLY", "REFERENCE_AREA", "REFERENCE_AXIS_LENGTH", "FILL_NET_OF_FRAMING", "NO_PLATES_OR_NOTCHES", "FASTENINGS_NOT_COUNTED",
             "JACK_THRESHOLD_DECLARED", "OPENINGS_ARE_VOIDS", "FIT_TO_AXES_ONLY"]
    for payload in (STRAW, STUD):
        assert [a["code"] for a in payload["assumptions"]] == codes
    assert STRAW["assumptions"] == [dict(a) for a in ASSUMPTIONS]
    assert not any("air film" in a["message"] or "parallel" in a["message"].lower() for a in STRAW["assumptions"])  # §4.7


# 6. The envelope (§13 test 6, AC2b-09) -----------------------------------------------------------


def test_envelope_is_preliminary_and_flags_climate_details():
    svc = ProjectService(MemoryStore(), token_key=KEY)
    pid = create(svc).project_id
    env = svc.artifacts.get_artifact(pid, "assembly_schedule", now=T0)
    assert (env["status"], env["generator_id"], env["generator_version"]) == ("CURRENT", "assembly-schedule-vs02b", "1")
    assert env["suitability"] == "preliminary" and not any(env["claims"].values())
    assert [w["code"] for w in env["warnings"]] == ["PRELIMINARY_UNVERIFIED", "CLIMATE_DETAILS_UNVERIFIED"]
    for name in ("assumptions", "totals", "layer_aggregates", "framing_aggregates", "opening_aggregates", "definition_aggregates"):
        assert env["payload"][name] == STRAW[name], name  # the created house has minted IDs (D041), the same quantities
    assert env["payload"]["definitions"][0]["unverified_climate_details"]
    assert (ASSEMBLY_SCHEDULE.generator_id, ASSEMBLY_SCHEDULE.generator_version, ASSEMBLY_SCHEDULE.depends_on) == ("assembly-schedule-vs02b", "1", ())


def test_climate_warning_is_on_every_envelope_whatever_its_status():
    from homedesign.dependencies import ArtifactService, registry_of
    from homedesign.dependencies.registry import Derivation

    def broken(context):
        raise RuntimeError("boom")

    svc = ProjectService(MemoryStore(), token_key=KEY)
    pid = create(svc).project_id
    failing = ArtifactService(svc.store, registry_of([Derivation("assembly_schedule", "assembly-schedule-vs02b", "broken", select_assembly_schedule, broken)]))
    env = failing.get_artifact(pid, "assembly_schedule", now=T0)
    assert env["status"] == "FAILED" and [w["code"] for w in env["warnings"]] == ["PRELIMINARY_UNVERIFIED", "CLIMATE_DETAILS_UNVERIFIED"]
    missing = ArtifactService(svc.store, registry_of([])).get_artifact(pid, "assembly_schedule", now=T0)
    assert missing["status"] == "MISSING" and [w["code"] for w in missing["warnings"]] == ["PRELIMINARY_UNVERIFIED", "CLIMATE_DETAILS_UNVERIFIED"]


def test_deterministic_bytes():
    assert canonical_json(schedule_of(FIXTURE)) == canonical_json(STRAW)
    assert canonical_json(schedule_of(STUD_INFILL)) == canonical_json(STUD)
