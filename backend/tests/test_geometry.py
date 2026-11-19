"""GEOM-001 acceptance tests (§5): `plan2d` and `mesh3d`."""

from __future__ import annotations

import json
import math

import jsonschema
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from conftest import FIXTURE, REPO_ROOT, VECTORS_PATH
from homedesign.geometry import build_mesh3d, build_plan2d
from homedesign.geometry.views import _plane_of
from homedesign.model import validate_value
from homedesign.model.canonical import fingerprint
from homedesign.model.commands import propose
from homedesign.model.jcs import canonical_json
from homedesign.model.schema import Snapshot
from homedesign.project import MemoryStore, ProjectService
from test_commands import BASE, cmd
from test_project import ACTOR, KEY, T0, at, create, envelope, head, preview_commit, width_cmd

FIXTURE_SNAPSHOT = Snapshot.model_validate(FIXTURE)
SCHEMA = json.loads((REPO_ROOT / "docs/architecture/schemas/artifacts.v1.schema.json").read_text())
VECTORS = json.loads(VECTORS_PATH.read_text())["geometry"]


def validate_against(name, value):
    jsonschema.Draft202012Validator({**SCHEMA, "$ref": f"#/$defs/{name}"}).validate(value)


def member_ids(snapshot):
    return {e.id for e in snapshot.entities if e.kind == "TimberMember"}


# 1. plan2d -------------------------------------------------------------------------------


def test_reference_house_plan():
    plan = build_plan2d(FIXTURE_SNAPSHOT)
    assert [(p["plane_id"], len(p["posts"]), len(p["beams"])) for p in plan["planes"]] == [
        ("level-0", 12, 0), ("level-1", 12, 17), ("eave", 0, 17)]
    assert [p["z_m"] for p in plan["planes"]] == [0.0, 3.048, 5.7912]
    assert plan["footprint"]["ring_m"] == [[0.0, 0.0], [10.9728, 0.0], [10.9728, 7.3152], [0.0, 7.3152]]
    assert plan["roof_plan"]["ridge_m"] == {"start_xy_m": [0.0, 3.6576], "end_xy_m": [10.9728, 3.6576]}
    assert plan["roof_plan"]["eave_ring_m"] == [[0.0, -0.6096], [10.9728, -0.6096], [10.9728, 7.9248], [0.0, 7.9248]]
    assert [(d["id"], d["value_m"]) for d in plan["dimensions"]] == [("footprint-width", 10.9728), ("footprint-depth", 7.3152)]
    for plane in plan["planes"]:
        for group in ("posts", "beams"):
            keys = [i["generation_key"] for i in plane[group]]
            assert keys == sorted(keys)
    validate_against("Plan2dPayload", plan)


# 2. mesh3d ---------------------------------------------------------------------------------


def test_reference_house_mesh():
    mesh, plan = build_mesh3d(FIXTURE_SNAPSHOT), build_plan2d(FIXTURE_SNAPSHOT)
    ids = [b["member_id"] for b in mesh["members"]]
    plan_ids = {i["member_id"] for p in plan["planes"] for g in ("posts", "beams") for i in p[g]}
    assert len(ids) == 58 and set(ids) == member_ids(FIXTURE_SNAPSHOT) == plan_ids
    sections = {e.id: e for e in FIXTURE_SNAPSHOT.entities if e.kind == "Section"}
    stored = {e.id: e for e in FIXTURE_SNAPSHOT.entities if e.kind == "TimberMember"}
    for box in mesh["members"]:
        s = sections[stored[box["member_id"]].section_id]
        assert (box["section_width_m"], box["section_depth_m"]) == (s.actual_width_m, s.actual_depth_m)
        assert box["axis_start_m"] == stored[box["member_id"]].start_m  # stored snapshot, not regenerated
    assert mesh["envelope"]["footprint_ring_m"] == plan["footprint"]["ring_m"]
    assert mesh["envelope"]["level_z_m"] == [0.0, 3.048] and mesh["envelope"]["z_eave_m"] == 5.7912
    validate_against("Mesh3dPayload", mesh)


# 3. roof slope (C1, D048) -------------------------------------------------------------------


def test_roof_planes_have_the_confirmed_pitch():
    roof = build_mesh3d(FIXTURE_SNAPSHOT)["envelope"]["roof"]
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


# 6. determinism and cross-language vectors --------------------------------------------------------


def test_plan_matches_independent_ecmascript_implementation():
    plan = build_plan2d(FIXTURE_SNAPSHOT)
    assert canonical_json(plan) == canonical_json(build_plan2d(FIXTURE_SNAPSHOT))
    assert len(canonical_json(plan)) == VECTORS["plan2d"]["canonical_bytes"]
    assert fingerprint(plan) == VECTORS["plan2d"]["fingerprint"]


def test_mesh_matches_independent_ecmascript_implementation():
    """Bit-identical except tan(pitch)-derived heights, within 1e-12 m (geometry.md)."""
    mesh, expected = build_mesh3d(FIXTURE_SNAPSHOT), VECTORS["mesh3d"]["payload"]
    assert mesh["members"] == expected["members"]
    ours, theirs = mesh["envelope"], expected["envelope"]
    assert {k: ours[k] for k in ("footprint_ring_m", "level_z_m", "z_eave_m")} == {k: theirs[k] for k in ("footprint_ring_m", "level_z_m", "z_eave_m")}
    assert ours["roof"]["pitch_rad"] == theirs["roof"]["pitch_rad"]
    ours_points = [ours["roof"]["ridge_start_m"], ours["roof"]["ridge_end_m"], *(p for s in ours["roof"]["surfaces"] for p in s["ring_m"])]
    their_points = [theirs["roof"]["ridge_start_m"], theirs["roof"]["ridge_end_m"], *(p for s in theirs["roof"]["surfaces"] for p in s["ring_m"])]
    for a, b in zip(ours_points, their_points, strict=True):
        assert a[:2] == b[:2] and abs(a[2] - b[2]) <= 1e-12
    # The two engines' tan differs in the last bit here, which is exactly why the tolerance exists.
    assert abs(math.tan(ours["roof"]["pitch_rad"]) - VECTORS["mesh3d"]["tan"]) <= 1e-15


# 7. robustness ----------------------------------------------------------------------------------------


@settings(max_examples=60, suppress_health_check=[HealthCheck.too_slow])
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
        plan, mesh = build_plan2d(snapshot), build_mesh3d(snapshot)
        assert sum(len(p["posts"]) + len(p["beams"]) for p in plan["planes"]) == len(member_ids(snapshot))
        assert {b["member_id"] for b in mesh["members"]} == member_ids(snapshot)
        validate_against("Plan2dPayload", plan)
        validate_against("Mesh3dPayload", mesh)


def test_unknown_member_key_is_a_derivation_error():
    with pytest.raises(ValueError):
        _plane_of("frame/x0/y0/level-2/post")
