"""TIMBER-002: vs02-frame-1 generator, registry, fixture, and cross-language inventory vector."""

from __future__ import annotations

import json
import math
import random
import re
from collections import Counter

import pytest
from hypothesis import given
from hypothesis import strategies as st

from conftest import FIXTURE, VECTORS_PATH, entities_of, fresh_fixture, grid_doc, largest_doc, regenerate, with_frame_parameters
from homedesign.model import canonical_json, validate_value
from homedesign.model.connections import JUNCTION_CLASSES
from homedesign.model.schema import Snapshot
from homedesign.timber import get_rule, registered_versions
from homedesign.timber import fixture as fixture_builder

RULE = get_rule("vs02-frame-1")
VECTORS = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))
FT = 0.3048
ROLES = ("POST", "BEAM", "SILL", "FLOOR_JOIST", "PRINCIPAL_RAFTER", "PURLIN", "KNEE_BRACE")


def _snapshot(doc) -> Snapshot:
    return Snapshot.model_validate(doc)


def _generate(doc):
    return RULE.generate(_snapshot(doc))


def _keys(doc) -> set[str]:
    return {m.generation_key for m in _generate(doc)}


def _frame(doc):
    return entities_of(doc, "FrameSystem")[0]




# --- registry and fixture --------------------------------------------------------------


def test_registry():
    assert registered_versions() == ("vs02-frame-1",)
    assert get_rule("vs01-post-beam-1") is None  # retired (D055)
    assert RULE.generated_roles == set(ROLES)
    assert RULE.generated_junction_classes == set(JUNCTION_CLASSES)
    assert len(RULE.generate_connections(_snapshot(FIXTURE))) == 312  # CONN-001 §6; test_connections.py


def test_retired_rule_is_unsupported():
    doc = fresh_fixture()
    entities_of(doc, "TimberGrid")[0]["generation_rule_version"] = "vs01-post-beam-1"
    result = validate_value(doc)
    assert result.code == "UNSUPPORTED_CONFIGURATION"
    assert {i.code for i in result.issues} == {"UNSUPPORTED_VALUE"}


def test_fixture_inventory_is_exact_generator_output():
    """AC2-02, AC2-06; TIMBER-002 §7: 193 members, bit-identical to the rule."""
    generated = _generate(FIXTURE)
    stored = {m["generation_key"]: m for m in entities_of(FIXTURE, "TimberMember")}
    assert [m.generation_key for m in generated] == sorted(stored, key=lambda k: k.encode("utf-16-be"))
    for m in generated:
        assert {k: v for k, v in stored[m.generation_key].items() if k not in ("id", "kind", "schema_version")} == m.to_json()
    assert Counter(m.member_role for m in generated) == {
        "POST": 24, "BEAM": 34, "SILL": 17, "FLOOR_JOIST": 30, "PRINCIPAL_RAFTER": 8, "PURLIN": 12, "KNEE_BRACE": 68,
    }
    assert len(generated) == 193


def test_fixture_and_template_are_current():
    assert fixture_builder.main(["--check"]) == 0


def test_reference_values():
    """TIMBER-002 §10 test 3: ridge, rafter length, purlin and joist positions, braces."""
    by_key = {m.generation_key: m for m in _generate(FIXTURE)}
    rafter = by_key["frame/roof/x0/south/principal-rafter"]
    assert abs(rafter.end_m[2] - 8.5344) <= 1e-12  # D048
    assert abs(math.dist(rafter.start_m, rafter.end_m) - 15 * FT) <= 1e-9  # D053
    for i, along in ((1, 5 * FT), (2, 10 * FT)):
        purlin = by_key[f"frame/roof/x0-x1/south/p{i}/purlin"]
        assert abs(math.dist(rafter.start_m, (rafter.start_m[0], *purlin.start_m[1:])) - along) <= 1e-9
    joists = sorted(m.start_m[0] for k, m in by_key.items() if "/x0-x1/j" in k and "/y0-y1/" in k)
    assert [round(x / FT, 9) for x in joists] == [2, 4, 6, 8, 10]
    for k, m in by_key.items():
        if m.member_role == "KNEE_BRACE":
            dx, dy, dz = (abs(e - s) for s, e in zip(m.start_m, m.end_m))
            assert abs(max(dx, dy) - 3 * FT) <= 1e-9 and abs(dz - 3 * FT) <= 1e-9 and min(dx, dy) == 0, k


def test_inventory_matches_independent_ecmascript_implementation():
    """TIMBER-002 §8: bit-identical, except rafter and purlin z values (tan), within 1e-12 m."""
    vector = next(v for v in VECTORS["inventories"] if v["name"] == "reference-house-001-vs02-frame-1")
    assert vector["rule"] == "vs02-frame-1"
    ours = [m.to_json() for m in _generate(FIXTURE)]
    theirs = vector["inventory"]
    assert len(ours) == len(theirs) == vector["members"] == 193
    for a, b in zip(ours, theirs):
        tan_derived = a["member_role"] in ("PRINCIPAL_RAFTER", "PURLIN")
        for field in a:
            if field in ("start_m", "end_m") and tan_derived:
                assert a[field][:2] == b[field][:2], (a["generation_key"], field)
                assert abs(a[field][2] - b[field][2]) <= 1e-12, (a["generation_key"], field)
            else:
                assert a[field] == b[field], (a["generation_key"], field)


@pytest.mark.parametrize("seed", [3, 11])
def test_generation_is_deterministic_and_order_independent(seed):
    baseline = canonical_json([m.to_json() for m in _generate(FIXTURE)])
    doc = fresh_fixture()
    random.Random(seed).shuffle(doc["entities"])
    assert canonical_json([m.to_json() for m in _generate(doc)]) == baseline


# --- counts (TIMBER-002 §5.3) --------------------------------------------------------------


def _expected_counts(doc) -> Counter:
    """An independent restatement of the §5.3 formulas."""
    fp = entities_of(doc, "Footprint")[0]
    grid = entities_of(doc, "TimberGrid")[0]
    p = _frame(doc)["parameters"]
    nx, ny = len(grid["x_lines"]), len(grid["y_lines"])
    bay_lines = ny * (nx - 1) + nx * (ny - 1)
    xs = [fp["width_m"] * line["fraction"] for line in grid["x_lines"]]
    joists_per_span = 0
    for xa, xb in zip(xs, xs[1:]):
        joists_per_span += sum(1 for k in range(1, 200) if xa + k * p["joist_spacing_m"] < xb - 1e-6)
    planes = int(p["knee_braces_level_1"]) + int(p["knee_braces_eave"])
    counts = Counter({
        "POST": 2 * nx * ny,
        "BEAM": 2 * bay_lines,
        "SILL": bay_lines,
        "FLOOR_JOIST": (ny - 1) * joists_per_span,
        "PRINCIPAL_RAFTER": 2 * nx,
        "PURLIN": 2 * p["purlins_per_slope"] * (nx - 1),
        "KNEE_BRACE": 2 * bay_lines * planes,
    })
    return +counts  # drop zero counts




def _check_counts(doc):
    result = validate_value(doc)
    assert result.valid, result.to_dict()
    members = RULE.generate(result.snapshot)
    assert Counter(m.member_role for m in members) == _expected_counts(doc)
    assert len({m.generation_key for m in members}) == len(members)
    xs = {line["fraction"] * entities_of(doc, "Footprint")[0]["width_m"] for line in entities_of(doc, "TimberGrid")[0]["x_lines"]}
    for m in members:
        if m.member_role == "FLOOR_JOIST":
            assert all(abs(m.start_m[0] - x) > 1e-6 for x in xs), m.generation_key  # never on a beam line


@pytest.mark.parametrize("nx", range(2, 8))
@pytest.mark.parametrize("ny", range(2, 8))
def test_member_counts_for_every_supported_grid(nx, ny):
    _check_counts(grid_doc(nx, ny))


@pytest.mark.parametrize(
    "parameters",
    [
        {"joist_spacing_m": 0.3048},
        {"joist_spacing_m": 1.2192},
        {"purlins_per_slope": 0},
        {"purlins_per_slope": 4},
        {"knee_brace_leg_m": 0.4572},
        {"knee_brace_leg_m": 1.2192},
        {"knee_braces_level_1": False},
        {"knee_braces_level_1": False, "knee_braces_eave": False},
    ],
)
def test_member_counts_at_parameter_bounds(parameters):
    _check_counts(with_frame_parameters(**parameters))


def test_largest_supported_inventory():
    """TIMBER-002 §5.3: 7 × 7 stations over 80' × 80', 12" joists, 4 purlins, both brace planes."""
    doc = largest_doc()
    _check_counts(doc)
    members = _generate(doc)
    assert len(members) == 1216 and sum(m.member_role == "FLOOR_JOIST" for m in members) == 468


# --- identity (TIMBER-002 §5.4) ----------------------------------------------------------


def _with_x_lines(lines):
    doc = fresh_fixture()
    entities_of(doc, "TimberGrid")[0]["x_lines"] = lines
    return doc


X = {line["id"]: line for line in entities_of(FIXTURE, "TimberGrid")[0]["x_lines"]}
X_LINE = re.compile(r"(^|[/-])x2([/-]|$)")


def test_inserting_a_line_retires_only_the_split_bay():
    before = _keys(FIXTURE)
    after = _keys(_with_x_lines([X["x0"], X["x1"], {"id": "x4", "fraction": 0.5}, X["x2"], X["x3"]]))
    removed, added = before - after, after - before
    assert removed == {k for k in before if "/x1-x2/" in k or k.endswith("/x1-x2")}
    assert all("x4" in k for k in added)
    assert not {k for k in before & after if "x4" in k}


def test_removing_an_interior_line_retires_exactly_its_members():
    before = _keys(FIXTURE)
    after = _keys(_with_x_lines([X["x0"], X["x1"], X["x3"]]))
    removed, added = before - after, after - before
    assert removed == {k for k in before if X_LINE.search(k)}
    assert added == {k for k in after if "x1-x3" in k}
    # The merged 24' bay holds 11 joists per span (2' to 22').
    assert sum("/x1-x3/j" in k for k in added) == 2 * 11


def test_spacing_change_keeps_lower_ordinals():
    base = _keys(FIXTURE)
    tighter = _keys(with_frame_parameters(joist_spacing_m=16 * FT / 12))  # 16": 8 joists per 12' bay
    assert {k for k in base if "/joist" in k} < {k for k in tighter if "/joist" in k}
    assert sum("/x0-x1/j" in k and "/y0-y1/" in k for k in tighter) == 8
    wider = _keys(with_frame_parameters(joist_spacing_m=0.9144))  # 36": 3 joists per bay
    assert {k for k in wider if "/joist" in k} == {k for k in base if re.search(r"/j[123]/", k)}


def test_purlin_count_change_keeps_lower_ordinals():
    base = _generate(FIXTURE)
    three = {m.generation_key: m for m in _generate(with_frame_parameters(purlins_per_slope=3))}
    base_purlins = {m.generation_key: m for m in base if m.member_role == "PURLIN"}
    assert set(base_purlins) < set(three)
    moved = three["frame/roof/x0-x1/south/p1/purlin"].start_m[2] != base_purlins["frame/roof/x0-x1/south/p1/purlin"].start_m[2]
    assert moved  # 1/3 → 1/4 of the slope


def test_member_defaults_change_only_sections():
    doc = fresh_fixture()
    frame = _frame(doc)
    joist_section = frame["member_defaults"]["FLOOR_JOIST"]["section_id"]
    frame["member_defaults"]["KNEE_BRACE"]["section_id"] = joist_section
    before = {m.generation_key: m for m in _generate(FIXTURE)}
    for m in _generate(doc):
        b = before[m.generation_key]
        assert (m.start_m, m.end_m, m.member_role, m.material_id) == (b.start_m, b.end_m, b.member_role, b.material_id)  # D058
        assert m.section_id == (joist_section if m.member_role == "KNEE_BRACE" else b.section_id)


# --- datum axes (D058) ----------------------------------------------------------------------


def _on_segment(point, start, end, eps=1e-9) -> bool:
    ab = [e - s for s, e in zip(start, end)]
    ap = [p - s for s, p in zip(start, point)]
    length2 = sum(c * c for c in ab)
    t = sum(a * b for a, b in zip(ap, ab)) / length2
    closest = [s + t * c for s, c in zip(start, ab)]
    return -eps <= t <= 1 + eps and math.dist(point, closest) <= eps


def test_axes_meet_on_datums():
    members = _generate(FIXTURE)
    beams = [m for m in members if m.member_role == "BEAM"]
    posts = [m for m in members if m.member_role == "POST"]
    rafters = [m for m in members if m.member_role == "PRINCIPAL_RAFTER"]
    for m in members:
        if m.member_role == "FLOOR_JOIST":
            for end in (m.start_m, m.end_m):
                assert any(_on_segment(end, b.start_m, b.end_m) for b in beams if "plane-L1" in b.generation_key), m.generation_key
        elif m.member_role == "PURLIN":
            for end in (m.start_m, m.end_m):
                assert any(_on_segment(end, r.start_m, r.end_m) for r in rafters), m.generation_key
        elif m.member_role == "KNEE_BRACE":
            assert any(_on_segment(m.start_m, p.start_m, p.end_m) for p in posts), m.generation_key
            assert any(_on_segment(m.end_m, b.start_m, b.end_m) for b in beams), m.generation_key
        elif m.member_role == "PRINCIPAL_RAFTER":
            assert any(_on_segment(m.start_m, b.start_m, b.end_m) for b in beams if "plane-eave" in b.generation_key)


# --- zero cases, conformance, regeneration -------------------------------------------------


def test_zero_cases_generate_nothing_of_that_kind_and_validate():
    doc = with_frame_parameters(purlins_per_slope=0, knee_braces_level_1=False, knee_braces_eave=False, joist_spacing_m=1.2192)
    # A 4'-0" bay with 48" spacing has no joists.
    grid = entities_of(doc, "TimberGrid")[0]
    width = entities_of(doc, "Footprint")[0]["width_m"]
    grid["x_lines"] = [X["x0"], X["x1"], {"id": "x4", "fraction": X["x1"]["fraction"] + 4 * FT / width}, X["x2"], X["x3"]]
    doc = regenerate(doc)
    result = validate_value(doc)
    assert result.valid, result.to_dict()
    roles = Counter(m.member_role for m in _generate(doc))
    assert roles["PURLIN"] == 0 and roles["KNEE_BRACE"] == 0
    assert not any("/x1-x4/j" in m.generation_key for m in _generate(doc))


@pytest.mark.parametrize("role", ROLES)
def test_conformance_mutations_for_every_role(role):
    """TIMBER-001 test 8, applied to one member of each role (TIMBER-002 §10 test 10)."""
    member = next(m for m in entities_of(FIXTURE, "TimberMember") if m["member_role"] == role)

    def mutated(change):
        doc = fresh_fixture()
        target = next(m for m in entities_of(doc, "TimberMember") if m["id"] == member["id"])
        change(doc, target)
        return validate_value(doc)

    def codes_of(result):
        return {i.code for i in result.issues}

    inside = mutated(lambda d, m: m["end_m"].__setitem__(2, m["end_m"][2] + 5e-7))
    assert inside.valid
    assert codes_of(mutated(lambda d, m: m["end_m"].__setitem__(2, m["end_m"][2] + 2e-6))) == {"MEMBER_GEOMETRY_MISMATCH"}
    assert codes_of(mutated(lambda d, m: m.update(start_m=m["end_m"], end_m=m["start_m"]))) == {"MEMBER_GEOMETRY_MISMATCH"}
    other = "BEAM" if role != "BEAM" else "POST"
    wrong = mutated(lambda d, m: m.update(section_id=_frame(d)["member_defaults"][other]["section_id"]))
    if member["section_id"] != _frame(FIXTURE)["member_defaults"][other]["section_id"]:
        assert codes_of(wrong) == {"MEMBER_ASSIGNMENT_MISMATCH"}
        assert wrong.issues[0].related_paths[0].endswith(f".member_defaults.{role}.section_id")

    def remove(d, m):
        # With the connections that name it, so only the member is missing (CONN-001).
        gone = {m["id"]} | {c["id"] for c in entities_of(d, "Connection") if m["id"] in c["member_ids"]}
        d["entities"] = [e for e in d["entities"] if e["id"] not in gone]
        _frame(d)["member_ids"].remove(m["id"])
        _frame(d)["connection_ids"] = [i for i in _frame(d)["connection_ids"] if i not in gone]

    missing = mutated(remove)
    assert codes_of(missing) == {"MISSING_GENERATED_MEMBER"} and missing.issues[0].value == member["generation_key"]


def test_regenerated_snapshot_is_valid_and_exact():
    doc = regenerate(fresh_fixture())
    result = validate_value(doc)
    assert result.valid
    stored = {m["generation_key"]: m for m in entities_of(doc, "TimberMember")}
    for m in RULE.generate(result.snapshot):
        assert stored[m.generation_key]["start_m"] == list(m.start_m)
        assert stored[m.generation_key]["end_m"] == list(m.end_m)


@given(
    spacing=st.floats(0.3048, 1.2192),
    purlins=st.integers(0, 4),
    leg=st.floats(0.4572, 1.2192),
    level_1=st.booleans(),
    eave=st.booleans(),
    pitch=st.floats(math.atan(0.25), math.atan(1.0)),
)
def test_random_parameters_never_raise(spacing, purlins, leg, level_1, eave, pitch):
    """TIMBER-002 §10 test 11: the rule is defined for every supported parameter set."""
    doc = fresh_fixture()
    entities_of(doc, "GableRoof")[0]["pitch_rad"] = pitch
    doc = with_frame_parameters(doc, joist_spacing_m=spacing, purlins_per_slope=purlins, knee_brace_leg_m=leg, knee_braces_level_1=level_1, knee_braces_eave=eave)
    result = validate_value(doc)
    assert result.valid, result.to_dict()
    assert Counter(m.member_role for m in RULE.generate(result.snapshot)) == _expected_counts(doc)
