"""GEOM-001 acceptance tests (§5) and ART-002 §13 tests 1–4, 9–13: `plan2d` and `mesh3d`."""

from __future__ import annotations

import json
import math
from collections import Counter

import jsonschema
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from conftest import FIXTURE, REPO_ROOT, VECTORS_PATH, fresh_fixture
from homedesign.estimating import ESTIMATE
from homedesign.geometry import MESH3D, PLAN2D, build_mesh3d, build_plan2d, select_mesh3d, select_plan2d
from homedesign.geometry.views import plan_slot
from homedesign.model import validate_value
from homedesign.model.canonical import fingerprint
from homedesign.model.commands import propose
from homedesign.model.jcs import canonical_json
from homedesign.model.schema import Snapshot
from homedesign.project import MemoryStore, ProjectService
from homedesign.timber.schedule import SCHEDULE
from test_commands import BASE, cmd
from test_project import ACTOR, KEY, T0, at, create, envelope, head, preview_commit, width_cmd

FIXTURE_SNAPSHOT = Snapshot.model_validate(FIXTURE)
SCHEMA = json.loads((REPO_ROOT / "docs/architecture/schemas/artifacts.v1.schema.json").read_text())
VECTORS = json.loads(VECTORS_PATH.read_text())["geometry"]
ARRAYS = ("posts", "beams", "sills", "joists", "braces", "rafters", "purlins")
ARTIFACTS = ("plan2d", "mesh3d", "timber_schedule", "preliminary_estimate")


def validate_against(name, value):
    jsonschema.Draft202012Validator({**SCHEMA, "$ref": f"#/$defs/{name}"}).validate(value)


def member_ids(snapshot):
    return {e.id for e in snapshot.entities if e.kind == "TimberMember"}


def connection_records(snapshot):
    return {e.id: e for e in snapshot.entities if e.kind == "Connection"}


def plan_entries(plan):
    return [(p["plane_id"], array, i) for p in plan["planes"] for array in ARRAYS for i in p[array]]


def utf16_sorted(keys):
    return keys == sorted(keys, key=lambda k: k.encode("utf-16-be"))


# 1. plan2d (ART-002 §13 tests 1–3) -----------------------------------------------------------------


def test_reference_house_plan():
    plan = build_plan2d(select_plan2d(FIXTURE_SNAPSHOT))
    counts = [(p["plane_id"], {a: len(p[a]) for a in ARRAYS if p[a]}, len(p["connections"])) for p in plan["planes"]]
    assert counts == [  # ART-002 §4.1, §4.2
        ("level-0", {"posts": 12, "sills": 17}, 12),
        ("level-1", {"posts": 12, "beams": 17, "joists": 30, "braces": 34}, 162),
        ("eave", {"beams": 17, "braces": 34}, 102),
        ("roof", {"rafters": 8, "purlins": 12}, 36),
    ]
    assert [(p["z_m"], p["level_id"] is None) for p in plan["planes"]] == [(0.0, False), (3.048, False), (5.7912, True), (5.7912, True)]
    assert plan["footprint"]["ring_m"] == [[0.0, 0.0], [10.9728, 0.0], [10.9728, 7.3152], [0.0, 7.3152]]
    assert plan["roof_plan"]["ridge_m"] == {"start_xy_m": [0.0, 3.6576], "end_xy_m": [10.9728, 3.6576]}
    assert plan["roof_plan"]["eave_ring_m"] == [[0.0, -0.6096], [10.9728, -0.6096], [10.9728, 7.9248], [0.0, 7.9248]]
    assert [(d["id"], d["value_m"]) for d in plan["dimensions"]] == [("footprint-width", 10.9728), ("footprint-depth", 7.3152)]
    for plane in plan["planes"]:
        assert set(plane) == {"plane_id", "level_id", "z_m", *ARRAYS, "connections"}  # every plane has every array
        for group in (*ARRAYS, "connections"):
            assert utf16_sorted([i["generation_key"] for i in plane[group]])
    assert not any("section_id" in entry for _, _, entry in plan_entries(plan))  # §4.3
    validate_against("Plan2dPayload", plan)


def test_one_inventory_in_plan_mesh_and_schedule():
    """§13 test 1 (AC2-02): the same 193 member IDs everywhere."""
    from homedesign.timber.schedule import build_schedule, select_schedule

    plan, mesh, schedule = build_plan2d(select_plan2d(FIXTURE_SNAPSHOT)), build_mesh3d(select_mesh3d(FIXTURE_SNAPSHOT)), build_schedule(select_schedule(FIXTURE_SNAPSHOT))
    plan_ids = [i["member_id"] for _, _, i in plan_entries(plan)]
    assert len(plan_ids) == 193 and len(set(plan_ids)) == 193
    assert set(plan_ids) == {b["member_id"] for b in mesh["members"]} == {r["member_id"] for r in schedule["members"]} == member_ids(FIXTURE_SNAPSHOT)


def test_plan_positions_are_exact_projections():
    """§13 test 2: linear entries project the axis; posts take start x and y; roles pick arrays."""
    stored = {e.id: e for e in FIXTURE_SNAPSHOT.entities if e.kind == "TimberMember"}
    array_roles = {"posts": "POST", "beams": "BEAM", "sills": "SILL", "joists": "FLOOR_JOIST", "braces": "KNEE_BRACE",
                   "rafters": "PRINCIPAL_RAFTER", "purlins": "PURLIN"}
    for _, array, entry in plan_entries(build_plan2d(select_plan2d(FIXTURE_SNAPSHOT))):
        member = stored[entry["member_id"]]
        assert member.member_role == array_roles[array] and entry["generation_key"] == member.generation_key
        if array == "posts":
            assert entry["xy_m"] == member.start_m[:2]
        else:
            assert (entry["start_xy_m"], entry["end_xy_m"]) == (member.start_m[:2], member.end_m[:2])


def test_plan_markers_are_on_the_entering_members_plane():
    """§13 test 3: one marker per connection, at the projection of its location, on member_ids[1]'s plane."""
    plan = build_plan2d(select_plan2d(FIXTURE_SNAPSHOT))
    records = connection_records(FIXTURE_SNAPSHOT)
    plane_of = {entry["member_id"]: plane for plane, _, entry in plan_entries(plan)}
    markers = [(p["plane_id"], c) for p in plan["planes"] for c in p["connections"]]
    assert len(markers) == 312 and {c["connection_id"] for _, c in markers} == set(records)
    for plane, marker in markers:
        record = records[marker["connection_id"]]
        assert set(marker) == {"connection_id", "generation_key", "junction_class", "connection_type", "xy_m"}  # no member_ids
        assert (marker["generation_key"], marker["junction_class"], marker["connection_type"]) == (
            record.generation_key, record.junction_class, record.connection_type)
        assert marker["xy_m"] == record.location_m[:2] and plane == plane_of[record.member_ids[1]]
    by_plane = {p["plane_id"]: Counter(c["junction_class"] for c in p["connections"]) for p in plan["planes"]}
    assert by_plane == {
        "level-0": {"post-sill": 12},
        "level-1": {"post-beam": 34, "brace": 68, "joist-beam": 60},
        "eave": {"post-beam": 34, "brace": 68},
        "roof": {"rafter-peak": 4, "rafter-foot": 8, "purlin-rafter": 24},
    }


@pytest.mark.parametrize(
    "role,key",
    [("POST", "frame/x0/y0/level-2/post"), ("BEAM", "frame/x0/y0/level-0/post"), ("FLOOR_JOIST", "frame/axis-x/y0/x0-x1/plane-L1/beam"),
     ("PURLIN", "frame/roof/x0/south/principal-rafter")],
)
def test_member_matching_no_plane_raises(role, key):
    with pytest.raises(ValueError):
        plan_slot(role, key)


def test_member_matching_no_plane_fails_the_derivation():
    doc = fresh_fixture()
    member = next(e for e in doc["entities"] if e["kind"] == "TimberMember" and e["member_role"] == "SILL")
    member["generation_key"] = member["generation_key"].replace("/plane-L0/", "/plane-L9/")
    with pytest.raises(ValueError):
        build_plan2d(select_plan2d(Snapshot.model_validate(doc)))


# 2. mesh3d (ART-002 §13 tests 3–4) -------------------------------------------------------------------


def test_reference_house_mesh():
    mesh, plan = build_mesh3d(select_mesh3d(FIXTURE_SNAPSHOT)), build_plan2d(select_plan2d(FIXTURE_SNAPSHOT))
    ids = [b["member_id"] for b in mesh["members"]]
    assert len(ids) == 193 and set(ids) == member_ids(FIXTURE_SNAPSHOT)
    sections = {e.id: e for e in FIXTURE_SNAPSHOT.entities if e.kind == "Section"}
    stored = {e.id: e for e in FIXTURE_SNAPSHOT.entities if e.kind == "TimberMember"}
    for box in mesh["members"]:
        s = sections[stored[box["member_id"]].section_id]
        assert (box["section_width_m"], box["section_depth_m"]) == (s.actual_width_m, s.actual_depth_m)
        assert box["axis_start_m"] == stored[box["member_id"]].start_m  # stored snapshot, not regenerated
    assert mesh["envelope"]["footprint_ring_m"] == plan["footprint"]["ring_m"]
    assert mesh["envelope"]["level_z_m"] == [0.0, 3.048] and mesh["envelope"]["z_eave_m"] == 5.7912
    validate_against("Mesh3dPayload", mesh)


def test_mesh_markers_copy_the_records():
    mesh = build_mesh3d(select_mesh3d(FIXTURE_SNAPSHOT))
    records = connection_records(FIXTURE_SNAPSHOT)
    assert len(mesh["connections"]) == 312 and {c["connection_id"] for c in mesh["connections"]} == set(records)
    assert utf16_sorted([c["generation_key"] for c in mesh["connections"]])
    for marker in mesh["connections"]:
        record = records[marker["connection_id"]]
        assert set(marker) == {"connection_id", "generation_key", "junction_class", "connection_type", "location_m"}  # no size or shape
        assert (marker["generation_key"], marker["junction_class"], marker["connection_type"]) == (
            record.generation_key, record.junction_class, record.connection_type)
        assert marker["location_m"] == record.location_m  # bit-identical


def box_basis(start, end):
    """The artifacts.md §6 orientation rule, restated: (width, depth) unit vectors."""
    axis = [e - s for s, e in zip(start, end, strict=True)]
    length = math.sqrt(sum(c * c for c in axis))
    along = [c / length for c in axis]
    if abs(along[2]) > 1 - 1e-9:
        return [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]
    h = math.hypot(along[0], along[1])
    width = [-along[1] / h, along[0] / h, 0.0]
    depth = [along[1] * width[2] - along[2] * width[1], along[2] * width[0] - along[0] * width[2], along[0] * width[1] - along[1] * width[0]]
    n = math.sqrt(sum(c * c for c in depth))
    depth = [c / n for c in depth]
    if depth[2] < 0:
        depth = [-c for c in depth]
    return width, depth


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b, strict=True))


def _close(a, b, eps=1e-12):
    return all(abs(x - y) <= eps for x, y in zip(a, b, strict=True))


def test_box_orientation_for_every_role():
    """§13 test 4: width horizontal (or +X for posts), depth perpendicular to the axis, per role."""
    mesh = build_mesh3d(select_mesh3d(FIXTURE_SNAPSHOT))
    pitch = mesh["envelope"]["roof"]["pitch_rad"]
    first = {}
    for box in mesh["members"]:
        first.setdefault(box["role"], box)
    assert set(first) == {"POST", "BEAM", "SILL", "FLOOR_JOIST", "PRINCIPAL_RAFTER", "PURLIN", "KNEE_BRACE"}
    for role, box in first.items():
        width, depth = box_basis(box["axis_start_m"], box["axis_end_m"])
        axis = [e - s for s, e in zip(box["axis_start_m"], box["axis_end_m"], strict=True)]
        assert abs(_dot(depth, axis)) <= 1e-12 and abs(_dot(width, axis)) <= 1e-12 and abs(_dot(width, depth)) <= 1e-12, role
        if role == "POST":
            assert (width, depth) == ([1.0, 0.0, 0.0], [0.0, 1.0, 0.0])
        else:
            assert width[2] == 0.0 and depth[2] >= 0.0, role
    for role in ("BEAM", "SILL", "FLOOR_JOIST", "PURLIN"):  # depth vertical (D053; purlins plumb, D060)
        assert _close(box_basis(first[role]["axis_start_m"], first[role]["axis_end_m"])[1], [0.0, 0.0, 1.0]), role
    rafter = first["PRINCIPAL_RAFTER"]
    width, depth = box_basis(rafter["axis_start_m"], rafter["axis_end_m"])
    slope = "south" if rafter["axis_end_m"][1] > rafter["axis_start_m"][1] else "north"
    normal = [0.0, -math.sin(pitch), math.cos(pitch)] if slope == "south" else [0.0, math.sin(pitch), math.cos(pitch)]
    assert _close([abs(c) for c in width], [1.0, 0.0, 0.0]) and _close(depth, normal)  # D053: perpendicular to the roof plane
    brace = first["KNEE_BRACE"]
    width, depth = box_basis(brace["axis_start_m"], brace["axis_end_m"])
    beam_plane_normal = [0.0, 1.0, 0.0] if brace["axis_start_m"][1] == brace["axis_end_m"][1] else [1.0, 0.0, 0.0]
    assert _close([abs(c) for c in width], beam_plane_normal) and abs(_dot(depth, beam_plane_normal)) <= 1e-12  # D058


# 3. roof slope (C1, D048) -------------------------------------------------------------------


def test_roof_planes_have_the_confirmed_pitch():
    roof = build_mesh3d(select_mesh3d(FIXTURE_SNAPSHOT))["envelope"]["roof"]
    t = math.tan(roof["pitch_rad"])
    for surface in roof["surfaces"]:
        zs = [p[2] for p in surface["ring_m"]]
        z_edge, z_ridge = min(zs), max(zs)
        assert abs((z_ridge - z_edge) / (7.3152 / 2 + 0.6096) - t) <= 1e-9
    assert abs(roof["ridge_start_m"][2] - 8.5344) <= 1e-6
    assert all(abs(min(p[2] for p in s["ring_m"]) - 5.334) <= 1e-6 for s in roof["surfaces"])


# 4./5. through the service --------------------------------------------------------------------


def test_service_derives_geometry_and_tracks_width_changes(store):
    svc = ProjectService(store, token_key=KEY)  # production registry
    created = create(svc)
    statuses = created.body()["artifact_statuses"]
    assert (statuses["plan2d"], statuses["mesh3d"]) == ("CURRENT", "CURRENT")
    pid = created.project_id
    old = svc.artifacts.get_artifact(pid, "plan2d", now=T0)
    preview_commit(svc, pid, width_cmd(svc, pid, 12.192), now=at(1))
    plan = svc.artifacts.get_artifact(pid, "plan2d", now=at(1))
    mesh = svc.artifacts.get_artifact(pid, "mesh3d", now=at(1))
    assert plan["payload"]["dimensions"][0]["value_m"] == 12.192
    assert mesh["payload"]["envelope"]["footprint_ring_m"][1] == [12.192, 0.0]
    assert plan["input_fingerprint"] != old["input_fingerprint"] and plan["head"] is True


def test_section_change_resizes_only_that_role(store):
    svc = ProjectService(store, token_key=KEY)
    pid = create(svc).project_id
    snapshot = head(svc, pid)
    beam_section = next(e for e in snapshot.entities if e.kind == "Section" and e.nominal_label == "8x12")
    before = {b["member_id"]: b for b in svc.artifacts.get_artifact(pid, "mesh3d", now=T0)["payload"]["members"]}
    preview_commit(svc, pid, envelope(svc, pid, "SetMemberSection", {"role": "POST", "section_id": beam_section.id}), now=at(1))
    after = svc.artifacts.get_artifact(pid, "mesh3d", now=at(1))["payload"]["members"]
    for box in after:
        if box["role"] == "POST":
            assert (box["section_width_m"], box["section_depth_m"]) == (0.2032, 0.3048)
        else:
            assert box == before[box["member_id"]]


def test_section_change_leaves_the_plan_byte_identical(store):
    """§13 test 9 (§4.3, D056): a new section changes the mesh and schedule for that role only."""
    svc = ProjectService(store, token_key=KEY)
    pid = create(svc).project_id
    base = {t: svc.artifacts.get_artifact(pid, t, now=T0)["payload"] for t in ARTIFACTS[:3]}
    preview_commit(svc, pid, envelope(svc, pid, "AddSection", {"nominal_label": "10x12", "actual_width_m": 0.2413, "actual_depth_m": 0.2921}), now=at(1))
    section = next(e for e in head(svc, pid).entities if e.kind == "Section" and e.nominal_label == "10x12")
    preview_commit(svc, pid, envelope(svc, pid, "SetMemberSection", {"role": "BEAM", "section_id": section.id}), now=at(2))
    after = {t: svc.artifacts.get_artifact(pid, t, now=at(2))["payload"] for t in ARTIFACTS[:3]}
    assert canonical_json(after["plan2d"]) == canonical_json(base["plan2d"])
    old_boxes = {b["member_id"]: b for b in base["mesh3d"]["members"]}
    for box in after["mesh3d"]["members"]:
        expected = {**old_boxes[box["member_id"]], "section_width_m": 0.2413, "section_depth_m": 0.2921} if box["role"] == "BEAM" else old_boxes[box["member_id"]]
        assert box == expected
    assert after["mesh3d"]["connections"] == base["mesh3d"]["connections"]
    old_rows = {r["member_id"]: r for r in base["timber_schedule"]["members"]}
    for row in after["timber_schedule"]["members"]:
        if row["role"] == "BEAM":
            assert {**row, "nominal_section": "8x12", "section_id": old_rows[row["member_id"]]["section_id"]} == old_rows[row["member_id"]]
        else:
            assert row == old_rows[row["member_id"]]
    assert after["timber_schedule"]["connections"] == base["timber_schedule"]["connections"]


def test_zero_cases_through_the_service(store):
    """§13 test 10: both brace planes off and zero purlins empty those arrays and markers; all artifacts derive."""
    svc = ProjectService(store, token_key=KEY)
    pid = create(svc).project_id
    frame = next(e for e in head(svc, pid).entities if e.kind == "FrameSystem")
    parameters = {**frame.parameters.model_dump(mode="json"), "knee_braces_level_1": False, "knee_braces_eave": False, "purlins_per_slope": 0}
    preview_commit(svc, pid, envelope(svc, pid, "SetFrameParameters", parameters), now=at(1))
    envelopes = {t: svc.artifacts.get_artifact(pid, t, now=at(1)) for t in ARTIFACTS}
    assert [envelopes[t]["status"] for t in ARTIFACTS] == ["CURRENT", "CURRENT", "CURRENT", "UNAVAILABLE"]
    plan = envelopes["plan2d"]["payload"]
    assert all(p["braces"] == [] and p["purlins"] == [] for p in plan["planes"])
    classes = {c["junction_class"] for p in plan["planes"] for c in p["connections"]}
    assert not classes & {"brace", "purlin-rafter"}
    assert {a["junction_class"] for a in envelopes["timber_schedule"]["payload"]["connection_aggregates"]} == classes
    assert len(envelopes["mesh3d"]["payload"]["connections"]) == sum(len(p["connections"]) for p in plan["planes"])


# 6. determinism, versions, and cross-language vectors ------------------------------------------------


def test_generator_versions():
    """ART-002 §8: every payload changed shape, so every derivation is at version 2 with its ID unchanged."""
    assert [(d.artifact_type, d.generator_id, d.generator_version) for d in (PLAN2D, MESH3D, SCHEDULE, ESTIMATE)] == [
        ("plan2d", "plan2d-vs01", "2"), ("mesh3d", "mesh3d-vs01", "2"), ("timber_schedule", "schedule-vs01", "2"),
        ("preliminary_estimate", "estimate-vs01", "2")]


def test_plan_matches_independent_ecmascript_implementation():
    plan = build_plan2d(select_plan2d(FIXTURE_SNAPSHOT))
    assert canonical_json(plan) == canonical_json(build_plan2d(select_plan2d(FIXTURE_SNAPSHOT)))
    assert len(canonical_json(plan)) == VECTORS["plan2d"]["canonical_bytes"]
    assert fingerprint(plan) == VECTORS["plan2d"]["fingerprint"]


def test_mesh_matches_independent_ecmascript_implementation():
    """Bit-identical except tan(pitch)-derived heights, within 1e-12 m (geometry.md)."""
    mesh, expected = build_mesh3d(select_mesh3d(FIXTURE_SNAPSHOT)), VECTORS["mesh3d"]["payload"]
    assert mesh["members"] == expected["members"]
    assert mesh["connections"] == expected["connections"]  # copied from the records on both sides
    ours, theirs = mesh["envelope"], expected["envelope"]
    assert {k: ours[k] for k in ("footprint_ring_m", "level_z_m", "z_eave_m")} == {k: theirs[k] for k in ("footprint_ring_m", "level_z_m", "z_eave_m")}
    assert ours["roof"]["pitch_rad"] == theirs["roof"]["pitch_rad"]
    ours_points = [ours["roof"]["ridge_start_m"], ours["roof"]["ridge_end_m"], *(p for s in ours["roof"]["surfaces"] for p in s["ring_m"])]
    their_points = [theirs["roof"]["ridge_start_m"], theirs["roof"]["ridge_end_m"], *(p for s in theirs["roof"]["surfaces"] for p in s["ring_m"])]
    for a, b in zip(ours_points, their_points, strict=True):
        assert a[:2] == b[:2] and abs(a[2] - b[2]) <= 1e-12
    # The two engines' tan differs in the last bit here, which is exactly why the tolerance exists.
    assert abs(math.tan(ours["roof"]["pitch_rad"]) - VECTORS["mesh3d"]["tan"]) <= 1e-15


def _keys(value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from _keys(v)
    elif isinstance(value, list):
        for v in value:
            yield from _keys(v)


def test_no_capacity_size_or_fastener_fields():
    """§13 test 13 (AC2-07): the payloads say where connections are and what type, nothing more."""
    from homedesign.estimating import build_estimate
    from homedesign.timber.schedule import build_schedule, select_schedule

    schedule = build_schedule(select_schedule(FIXTURE_SNAPSHOT))
    payloads = (build_plan2d(select_plan2d(FIXTURE_SNAPSHOT)), build_mesh3d(select_mesh3d(FIXTURE_SNAPSHOT)), schedule, build_estimate(schedule, None)[1])
    keys = {k for p in payloads for k in _keys(p)}
    assert not {k for k in keys if any(w in k for w in ("capacity", "fastener", "size", "peg", "plate", "dowel", "load"))}


# 7. robustness ----------------------------------------------------------------------------------------


# No deadline: each example runs three full proposes, which regenerate every member and connection
# (CONN-001), as in the other propose-driven property tests.
@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    st.floats(3.0, 26.0), st.floats(3.0, 26.0),
    st.lists(st.floats(0.05, 0.95), max_size=3),
    st.floats(2.3, 4.4), st.floats(2.3, 4.4),
)
def test_views_for_any_accepted_candidate(width, depth, extra_x, h0, h1):
    candidates = []
    for type_, args in (
        ("SetFootprintDimensions", {"width_m": width, "depth_m": depth}),
        ("SetStoryHeights", {"story_heights_m": [h0, h1]}),
        ("SetTimberGrid", {"x_lines": [{"id": "x0", "fraction": 0.0}, *({"fraction": f} for f in sorted(set(extra_x))), {"id": "x3", "fraction": 1.0}],
                           "y_lines": [{"id": "y0", "fraction": 0.0}, {"id": "y2", "fraction": 1.0}]}),
    ):
        result = propose(BASE, cmd(type_, args), actor_id=ACTOR, at="2026-11-19T12:00:00Z")
        if result.accepted:
            candidates.append(result.change.candidate)
    for snapshot in candidates:
        assert validate_value(snapshot.model_dump(mode="json")).valid
        plan, mesh = build_plan2d(select_plan2d(snapshot)), build_mesh3d(select_mesh3d(snapshot))
        plan_ids = [i["member_id"] for _, _, i in plan_entries(plan)]
        assert len(plan_ids) == len(set(plan_ids)) and set(plan_ids) == member_ids(snapshot)
        assert {b["member_id"] for b in mesh["members"]} == member_ids(snapshot)
        records = connection_records(snapshot)
        assert sorted(c["connection_id"] for p in plan["planes"] for c in p["connections"]) == sorted(records)
        assert sorted(c["connection_id"] for c in mesh["connections"]) == sorted(records)
        validate_against("Plan2dPayload", plan)
        validate_against("Mesh3dPayload", mesh)
