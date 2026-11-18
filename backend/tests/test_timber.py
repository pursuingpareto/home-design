"""TIMBER-001: vs01-post-beam-1 generator, registry, and cross-language inventory vector."""

from __future__ import annotations

import json
import math
import random
import re

import pytest

from conftest import FIXTURE, VECTORS_PATH, entities_of, fresh_fixture, regenerate
from homedesign.model import canonical_json, fingerprint, validate_value
from homedesign.model.schema import Snapshot
from homedesign.timber import get_rule, registered_versions

RULE = get_rule("vs01-post-beam-1")
VECTORS = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))


def _snapshot(doc) -> Snapshot:
    return Snapshot.model_validate(doc)


def _keys(doc) -> set[str]:
    return {m.generation_key for m in RULE.generate(_snapshot(doc))}


def test_registry():
    assert registered_versions() == ("vs01-post-beam-1",)
    assert get_rule("vs01-post-beam-2") is None
    assert RULE.generated_roles == {"POST", "BEAM"}


def test_unregistered_rule_is_unsupported():
    doc = fresh_fixture()
    entities_of(doc, "TimberGrid")[0]["generation_rule_version"] = "vs01-post-beam-9"
    result = validate_value(doc)
    assert result.code == "UNSUPPORTED_CONFIGURATION"
    assert {i.code for i in result.issues} == {"UNSUPPORTED_VALUE"}


def test_fixture_inventory_matches_fixture():
    generated = RULE.generate(_snapshot(FIXTURE))
    stored = {m["generation_key"]: m for m in entities_of(FIXTURE, "TimberMember")}
    assert len(generated) == 58
    assert sum(m.member_role == "POST" for m in generated) == 24
    assert [m.generation_key for m in generated] == sorted(stored)
    bitwise_different = set()
    for m in generated:
        s = stored[m.generation_key]
        assert (m.member_role, m.section_id, m.material_id) == (s["member_role"], s["section_id"], s["material_id"])
        for got, want in ((m.start_m, s["start_m"]), (m.end_m, s["end_m"])):
            assert all(abs(a - b) <= 1e-6 for a, b in zip(got, want))
            if list(got) != want:
                bitwise_different.add(m.generation_key)
    # generation-rules.md "Numeric evaluation": exactly the members touching lines x1 or x2
    # differ in the last bits (10.9728 × ⅓ = 3.6575999999999995, × ⅔ = 7.315199999999999).
    touching = {k for k in stored if re.search(r"(^|[/-])x[12]([/-]|$)", k)}
    assert bitwise_different == touching and len(touching) == 38


def test_inventory_matches_independent_ecmascript_implementation():
    vector = next(v for v in VECTORS["inventories"] if v["name"] == "reference-house-001-vs01-post-beam-1")
    inventory = [m.to_json() for m in RULE.generate(_snapshot(FIXTURE))]
    assert len(inventory) == vector["members"]
    assert len(canonical_json(inventory)) == vector["canonical_bytes"]
    assert fingerprint(inventory) == vector["fingerprint"]


@pytest.mark.parametrize("seed", [3, 11])
def test_generation_is_deterministic_and_order_independent(seed):
    baseline = canonical_json([m.to_json() for m in RULE.generate(_snapshot(FIXTURE))])
    doc = fresh_fixture()
    random.Random(seed).shuffle(doc["entities"])
    assert canonical_json([m.to_json() for m in RULE.generate(_snapshot(doc))]) == baseline


def _grid_doc(nx: int, ny: int) -> dict:
    doc = fresh_fixture()
    footprint = entities_of(doc, "Footprint")[0]
    footprint["width_m"] = (nx - 1) * 3.6576  # 12'-0" bays stay inside D032 bounds
    footprint["depth_m"] = (ny - 1) * 3.6576
    grid = entities_of(doc, "TimberGrid")[0]
    grid["x_lines"] = [{"id": f"x{i}", "fraction": i / (nx - 1)} for i in range(nx)]
    grid["y_lines"] = [{"id": f"y{j}", "fraction": j / (ny - 1)} for j in range(ny)]
    return regenerate(doc)


@pytest.mark.parametrize("nx", range(2, 8))
@pytest.mark.parametrize("ny", range(2, 8))
def test_member_counts_for_every_supported_grid(nx, ny):
    doc = _grid_doc(nx, ny)
    result = validate_value(doc)
    assert result.valid, result.to_dict()
    members = RULE.generate(result.snapshot)
    posts = sum(m.member_role == "POST" for m in members)
    beams = len(members) - posts
    assert posts == 2 * nx * ny
    assert beams == 2 * (ny * (nx - 1) + nx * (ny - 1))
    assert len({m.generation_key for m in members}) == len(members)


def _with_x_lines(lines):
    doc = fresh_fixture()
    entities_of(doc, "TimberGrid")[0]["x_lines"] = lines
    return doc


X = {line["id"]: line for line in entities_of(FIXTURE, "TimberGrid")[0]["x_lines"]}


def test_inserting_a_line_keeps_other_keys():
    before = _keys(FIXTURE)
    after = _keys(_with_x_lines([X["x0"], X["x1"], {"id": "x4", "fraction": 0.5}, X["x2"], X["x3"]]))
    removed, added = before - after, after - before
    assert removed == {k for k in before if "/x1-x2/" in k}
    assert len(removed) == 6  # 3 y lines × 2 planes
    assert all("x4" in k for k in added) and len(added) == 6 + 12 + 4
    assert not {k for k in before & after if "x4" in k}


def test_removing_an_interior_line_retires_exactly_its_members():
    before = _keys(FIXTURE)
    after = _keys(_with_x_lines([X["x0"], X["x1"], X["x3"]]))
    removed, added = before - after, after - before
    expected_removed = {k for k in before if re.search(r"(^|[/-])x2([/-]|$)", k)}
    assert removed == expected_removed and len(removed) == 6 + 12 + 4
    assert added == {k for k in after if "/x1-x3/" in k} and len(added) == 6


def test_member_defaults_change_only_sections():
    doc = fresh_fixture()
    frame = entities_of(doc, "FrameSystem")[0]
    beam_section = frame["member_defaults"]["BEAM"]["section_id"]
    frame["member_defaults"]["POST"]["section_id"] = beam_section
    before = {m.generation_key: m for m in RULE.generate(_snapshot(FIXTURE))}
    for m in RULE.generate(_snapshot(doc)):
        b = before[m.generation_key]
        assert (m.start_m, m.end_m, m.member_role, m.material_id) == (b.start_m, b.end_m, b.member_role, b.material_id)
        assert m.section_id == (beam_section if m.member_role == "POST" else b.section_id)


def test_regenerated_snapshot_is_valid_and_exact():
    doc = regenerate(fresh_fixture())
    result = validate_value(doc)
    assert result.valid
    # Regenerated members store generator output bit for bit.
    stored = {m["generation_key"]: m for m in entities_of(doc, "TimberMember")}
    for m in RULE.generate(result.snapshot):
        assert stored[m.generation_key]["start_m"] == list(m.start_m)
        assert stored[m.generation_key]["end_m"] == list(m.end_m)
    assert not math.isnan(sum(c for m in stored.values() for c in m["end_m"]))
