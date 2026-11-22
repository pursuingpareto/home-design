"""MODEL-003 acceptance tests (§8): typed commands and candidate snapshots."""

from __future__ import annotations

import json
import re
from collections import Counter

import jsonschema
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from conftest import FIXTURE, REPO_ROOT, VECTORS_PATH
from homedesign.model import canonical_snapshot, codes, validate_value
from homedesign.model.commands import (
    CLASSIFICATION,
    CLASSIFICATION_VERSION,
    mint,
    propose,
    propose_create,
)
from homedesign.model.jcs import canonical_json
from homedesign.model.schema import Snapshot
from homedesign.model.schema_export import COMMANDS_SCHEMA_PATH, render_commands_schema

P = "17ac32e0-0b3b-518e-b568-adf98f41bcd0"
P2 = "27ac32e0-0b3b-518e-b568-adf98f41bcd0"
ACTOR = "00000000-0000-4000-8000-000000000001"
ACTOR_B = "00000000-0000-4000-8000-000000000002"
CREATE_ID = "b8f9d645-5a10-4eb5-b2ca-38ce46e5d4aa"
CID = "11111111-1111-4111-8111-111111111111"
AT = "2026-11-18T12:00:00Z"
AT2 = "2026-11-18T13:30:00.5Z"
VECTORS = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))


def create(project_id=P, actor=ACTOR, command_id=CREATE_ID):
    result = propose_create({"command_id": command_id, "type": "CreateReferenceProject", "args": {}}, project_id=project_id, actor_id=actor, at=AT)
    assert result.accepted, result.rejection and result.rejection.to_dict()
    return result


BASE = create().change.candidate


def of_kind(snapshot, kind):
    return [e for e in snapshot.entities if e.kind == kind]


def one(snapshot, kind):
    return of_kind(snapshot, kind)[0]


def epath(entity, *steps):
    text = f"entities[{entity.id}]"
    for s in steps:
        text += f"[{s}]" if isinstance(s, int) else f".{s}"
    return text


def cmd(type_, args, base=BASE, cid=CID, **overrides):
    envelope = {"command_id": cid, "project_id": base.project_id, "base_revision_id": base.revision_id, "type": type_, "args": args}
    envelope.update(overrides)
    return envelope


def run(type_, args, base=BASE, actor=ACTOR, at=AT, target=None, cid=CID, **overrides):
    return propose(base, cmd(type_, args, base, cid, **overrides), actor_id=actor, at=at, target=target)


FP = one(BASE, "Footprint")
GRID = one(BASE, "TimberGrid")
FRAME = one(BASE, "FrameSystem")
L0, L1 = (next(e for e in BASE.entities if e.id == i) for i in BASE.building.level_ids)
ROOF = one(BASE, "GableRoof")
MATERIAL = one(BASE, "Material")
SECTIONS = {s.nominal_label: s for s in of_kind(BASE, "Section")}


def lines(axis, base=BASE):
    return [{"id": line.id, "fraction": line.fraction} for line in getattr(one(base, "TimberGrid"), axis)]


def members_by_key(snapshot):
    return {m.generation_key: m for m in of_kind(snapshot, "TimberMember")}


def connections_by_key(snapshot):
    return {c.generation_key: c for c in of_kind(snapshot, "Connection")}


def classes(entries):
    """Connection counts per junction class, from preview entries or generation keys."""
    keys = [e["generation_key"] if isinstance(e, dict) else e for e in entries]
    return dict(Counter(k.split("/")[1] for k in keys))


def token(key, line_id):
    return re.search(rf"(^|[/-]){line_id}([/-]|$)", key) is not None


# --- 1. width change ----------------------------------------------------------


def test_width_change_preserves_member_ids():
    change = run("SetFootprintDimensions", {"width_m": 12.192, "depth_m": FP.depth_m}).change
    cand = change.candidate
    before, after = members_by_key(BASE), members_by_key(cand)
    # Every base key survives with its ID (D042). The 40' width makes 13'-4" bays, so each bay
    # gains a sixth joist at 12'-0" in both spans (TIMBER-002 §5.4).
    assert before.keys() <= after.keys()
    assert all(after[k].id == m.id for k, m in before.items())
    added = sorted(m["generation_key"] for m in change.members.added)
    assert added == sorted(f"frame/axis-y/{bay}/j6/{span}/plane-L1/joist" for bay in ("x0-x1", "x1-x2", "x2-x3") for span in ("y0-y1", "y1-y2"))
    assert not change.members.removed
    # Exactly the members whose axes move are updated; members tied to x = 0 alone do not move.
    moved = {m.id for k, m in before.items() if (m.start_m, m.end_m) != (after[k].start_m, after[k].end_m)}
    assert set(change.members.updated) == moved
    assert len(change.members.updated) == 155
    # CONN-001 §5.3: every connection key survives with its ID; the six new joists add two
    # joist-beam connections each. Connections at x = 0 alone stay put: 3 post-sill, 14 post-beam
    # (the x0 Y beams' ends and the X beams' starts), 28 brace, 1 rafter-peak, and 2 rafter-foot.
    assert classes(change.connections.added) == {"joist-beam": 12} and not change.connections.removed
    assert len(change.connections.updated) == 312 - 72 == 240
    before_c, after_c = connections_by_key(BASE), connections_by_key(cand)
    assert all(after_c[k].id == c.id and after_c[k].member_ids == c.member_ids for k, c in before_c.items())
    assert [(c["entity_kind"], c["field"]) for c in change.changes] == [
        ("Footprint", "width_m"), ("FrameSystem", "connection_ids"), ("FrameSystem", "member_ids"),
    ]
    assert change.classification == "consequential" and change.confirmation_required


def test_width_change_on_fixture_base_preserves_ids():
    fixture = Snapshot.model_validate(FIXTURE)
    change = run("SetFootprintDimensions", {"width_m": 12.192, "depth_m": 7.3152}, base=fixture).change
    assert {e["id"] for e in FIXTURE["entities"] if e["kind"] == "TimberMember"} <= {m.id for m in of_kind(change.candidate, "TimberMember")}


# --- 2./3. grid edits ------------------------------------------------------------


def test_removing_interior_line_retires_exactly_its_members():
    x = [line for line in lines("x_lines") if line["id"] != "x2"]
    change = run("SetTimberGrid", {"x_lines": x, "y_lines": lines("y_lines")}).change
    before = members_by_key(BASE)
    removed = {m["generation_key"] for m in change.members.removed}
    # The x2 posts, and every sill, beam, brace, joist, rafter, and purlin of the x1-x2 and x2-x3 bays.
    assert removed == {k for k in before if token(k, "x2")} and len(removed) == 92
    added = {m["generation_key"]: m["id"] for m in change.members.added}
    # The merged 24' bay: 3 sills, 6 beams, 12 braces, 22 joists (11 per span), 4 purlins.
    assert set(added) == {k for k in members_by_key(change.candidate) if "x1-x3" in k} and len(added) == 47
    for key, member_id in added.items():
        assert member_id == mint("entity", P, ACTOR, CID, "generation/" + key)  # D041
    after = members_by_key(change.candidate)
    for key in before.keys() - removed:
        assert after[key].id == before[key].id
    # CONN-001 §5.3: the retired members' connections go (two per beam, brace, joist, and purlin
    # of the two bays, the x2 post feet, and the x2 rafter pair), and the merged bay's come back.
    # No surviving connection moves.
    assert classes(change.connections.removed) == {
        "brace": 64, "joist-beam": 40, "post-beam": 32, "post-sill": 3, "purlin-rafter": 16, "rafter-foot": 2, "rafter-peak": 1,
    }
    assert classes(change.connections.added) == {"brace": 24, "joist-beam": 44, "post-beam": 12, "purlin-rafter": 8}
    assert not change.connections.updated
    for c in change.connections.added:
        assert c["id"] == mint("entity", P, ACTOR, CID, "generation/" + c["generation_key"])  # D041


def test_inserting_line_mints_next_line_id():
    x = lines("x_lines")
    x.insert(2, {"fraction": 0.5})
    change = run("SetTimberGrid", {"x_lines": x, "y_lines": lines("y_lines")}).change
    grid = one(change.candidate, "TimberGrid")
    assert [line.id for line in grid.x_lines] == ["x0", "x1", "x4", "x2", "x3"]
    # The split bay's 35 members are retired; the two new bays and the x4 posts and rafters are added.
    assert len(change.members.added) == 80 and len(change.members.removed) == 35
    # Connections of the split bay's 32 members (two ends each) go; the new bays' and the x4
    # posts' and rafters' connections come.
    assert len(change.connections.removed) == 64 and len(change.connections.added) == 134
    assert classes(change.connections.added)["post-sill"] == 3 and classes(change.connections.added)["rafter-peak"] == 1
    assert {m["generation_key"] for m in change.members.removed} == {k for k in members_by_key(BASE) if "x1-x2" in k}
    before, after = members_by_key(BASE), members_by_key(change.candidate)
    for key in ("frame/x0/y0/level-0/post", "frame/x3/y2/level-1/post"):
        assert after[key].id == before[key].id


def test_new_line_numbers_skip_removed_and_listed_lines():
    # Remove x3 (an endpoint) and add a new end line in the same command: it must not reuse x3.
    x = [line for line in lines("x_lines") if line["id"] != "x3"] + [{"fraction": 1.0}]
    x[2]["fraction"] = 0.6
    change = run("SetTimberGrid", {"x_lines": x, "y_lines": lines("y_lines")}).change
    assert [line.id for line in one(change.candidate, "TimberGrid").x_lines] == ["x0", "x1", "x2", "x4"]


# --- other commands ------------------------------------------------------------


def test_story_heights():
    change = run("SetStoryHeights", {"story_heights_m": [3.3528, 2.7432]}).change
    l0, l1 = (next(e for e in change.candidate.entities if e.id == i) for i in change.candidate.building.level_ids)
    assert (l0.elevation_m, l0.story_height_m, l1.elevation_m, l1.story_height_m) == (0.0, 3.3528, 3.3528, 2.7432)
    assert change.members.updated and not change.members.added
    # Every connection above Level 0 moves; the 12 post feet stay on Level 0.
    assert len(change.connections.updated) == 300 and not (change.connections.added or change.connections.removed)


def test_roof_is_consequential_and_moves_rafters_and_purlins():
    """D057: the pitch places principal rafters and purlins, so roof edits are consequential."""
    change = run("SetGableRoofParameters", {"pitch_rad": 0.5, "eave_overhang_m": 0.3048}).change
    assert change.classification == "consequential" and change.confirmation_required
    assert {c["field"] for c in change.changes} == {"pitch_rad", "eave_overhang_m"}
    assert not (change.members.added or change.members.removed)
    roles = {m.id: m.member_role for m in of_kind(BASE, "TimberMember")}
    assert {roles[i] for i in change.members.updated} == {"PRINCIPAL_RAFTER", "PURLIN"} and len(change.members.updated) == 20
    # Only the tan-derived locations move: peaks and purlin ends. Rafter feet stay at z_eave.
    by_id = {c.id: c.junction_class for c in of_kind(BASE, "Connection")}
    assert Counter(by_id[i] for i in change.connections.updated) == {"purlin-rafter": 24, "rafter-peak": 4}


def test_overhang_alone_moves_no_member():
    change = run("SetGableRoofParameters", {"pitch_rad": ROOF.pitch_rad, "eave_overhang_m": 0.3048}).change
    assert not (change.members.added or change.members.removed or change.members.updated)  # D058: no rafter tails
    assert not (change.connections.added or change.connections.removed or change.connections.updated)


def test_frame_parameters():
    """MODEL-005 §7.1, D057: one command, consequential, IDs kept on surviving ordinals."""
    args = {"joist_spacing_m": 0.4064, "purlins_per_slope": 3, "knee_brace_leg_m": 0.9144, "knee_braces_level_1": True, "knee_braces_eave": False}
    change = run("SetFrameParameters", args).change
    assert change.classification == "consequential"
    assert [(c["entity_kind"], c["field"]) for c in change.changes] == [
        ("FrameSystem", "connection_ids"), ("FrameSystem", "member_ids"), ("FrameSystem", "parameters"),
    ]
    removed = {m["generation_key"] for m in change.members.removed}
    added = {m["generation_key"] for m in change.members.added}
    assert {k for k in removed if "/brace/" in k} == {k for k in members_by_key(BASE) if "plane-eave/brace" in k}
    assert all("/p3/" in k or "/j" in k for k in added)  # 16" spacing: j6–j8; a third purlin
    before, after = members_by_key(BASE), members_by_key(change.candidate)
    assert all(after[k].id == before[k].id for k in before.keys() & after.keys())
    # Eave braces off: 34 braces, two connections each. 16" joists: 3 more per span (j6–j8), two
    # ends each, in 6 spans; every joist moves. A third purlin: 2 slopes × 3 bays × 2 ends; p1 and p2 move.
    assert classes(change.connections.removed) == {"brace": 68}
    assert classes(change.connections.added) == {"joist-beam": 36, "purlin-rafter": 12}
    assert len(change.connections.updated) == 60 + 24


def test_frame_parameters_no_op_and_errors():
    current = FRAME.parameters.model_dump(mode="json")
    assert run("SetFrameParameters", current).change.is_noop
    rejected = run("SetFrameParameters", {**current, "knee_brace_leg_m": 2.0}).rejection
    assert rejected.code == UC
    # MODEL-006 §10: a 2 m leg also crosses the framed openings now, so the leg issue is found by path.
    issue = next(i for i in rejected.issues if i.path == epath(FRAME, "parameters", "knee_brace_leg_m"))
    assert "args.knee_brace_leg_m" in issue.related_paths
    unknown = run("SetFrameParameters", {**current, "girts": True}).rejection
    assert (unknown.code, unknown.issues[0].code, unknown.issues[0].path) == (VF, codes.UNKNOWN_FIELD, "args.girts")


def test_brace_fit_links_grid_arguments():
    """MODEL-005 §5.2: a grid edit that leaves a 5' bay cannot hold two 3' braces."""
    x = lines("x_lines")
    x.insert(2, {"fraction": x[1]["fraction"] + 5 * 0.3048 / FP.width_m})
    rejected = run("SetTimberGrid", {"x_lines": x, "y_lines": lines("y_lines")}).rejection
    assert rejected.code == UC
    issue = next(i for i in rejected.issues if i.path == epath(FRAME, "parameters", "knee_brace_leg_m"))
    assert "args.x_lines" in issue.related_paths


def test_add_section_with_existing_label_is_rejected():
    result = run("AddSection", {"nominal_label": "8x8", "actual_width_m": 0.1905, "actual_depth_m": 0.1905})
    assert result.rejection.code == VF
    issue = next(i for i in result.rejection.issues if i.code == codes.DUPLICATE_SECTION_LABEL)
    assert "args.nominal_label" in issue.related_paths  # D049 + interfaces.md §7.1 linking


def test_add_section_then_use_it():
    added = run("AddSection", {"nominal_label": "10x12", "actual_width_m": 0.254, "actual_depth_m": 0.3048}).change
    section_id = mint("entity", P, ACTOR, CID, "section")
    assert added.classification == "routine"
    assert [(c["entity_kind"], c["entity_id"], c["field"], c["before"]) for c in added.changes] == [("Section", section_id, "", None)]
    used = run("SetMemberSection", {"role": "POST", "section_id": section_id}, base=added.candidate, cid="22222222-2222-4222-8222-222222222222").change
    assert len(used.members.updated) == 24
    assert all(m.section_id == section_id for m in of_kind(used.candidate, "TimberMember") if m.member_role == "POST")


# --- 4. rejections ---------------------------------------------------------------

VF, UC = codes.VALIDATION_FAILED, codes.UNSUPPORTED_CONFIGURATION


def _dup_lines():
    x = lines("x_lines")
    x[2] = {"id": "x1", "fraction": x[2]["fraction"]}
    return {"x_lines": x, "y_lines": lines("y_lines")}


def _unordered():
    x = lines("x_lines")
    x[1]["fraction"], x[2]["fraction"] = x[2]["fraction"], x[1]["fraction"]
    return {"x_lines": x, "y_lines": lines("y_lines")}


REJECTIONS = [
    ("negative-width", "SetFootprintDimensions", {"width_m": -1, "depth_m": 7.3152}, {}, VF, codes.OUT_OF_RANGE, epath(FP, "width_m"), ["args.width_m"]),
    ("width-30m", "SetFootprintDimensions", {"width_m": 30, "depth_m": 7.3152}, {}, UC, codes.OUT_OF_SUPPORTED_RANGE, epath(FP, "width_m"), ["args.width_m"]),
    ("bay-too-long", "SetFootprintDimensions", {"width_m": 23, "depth_m": 7.3152}, {}, UC, codes.OUT_OF_SUPPORTED_RANGE, epath(GRID, "x_lines"), ["args.width_m", epath(FP, "width_m")]),
    ("missing-arg", "SetFootprintDimensions", {"width_m": 12}, {}, VF, codes.MISSING_FIELD, "args.depth_m", None),
    ("unknown-arg", "SetFootprintDimensions", {"width_m": 12, "depth_m": 7, "foo": 1}, {}, VF, codes.UNKNOWN_FIELD, "args.foo", None),
    ("wrong-type", "SetFootprintDimensions", {"width_m": "36", "depth_m": 7}, {}, VF, codes.WRONG_TYPE, "args.width_m", None),
    ("unknown-type", "SetWallHeight", {}, {}, VF, codes.INVALID_ENUM, "type", None),
    ("unknown-line", "SetTimberGrid", {"x_lines": [{"id": "x0", "fraction": 0.0}, {"id": "x7", "fraction": 0.5}, {"id": "x3", "fraction": 1.0}], "y_lines": lines("y_lines")}, {}, VF, codes.DANGLING_REFERENCE, "args.x_lines[1].id", None),
    ("duplicate-line", "SetTimberGrid", _dup_lines(), {}, VF, codes.DUPLICATE_LINE_ID, "args.x_lines[2].id", ["args.x_lines[1].id"]),
    ("null-line-id", "SetTimberGrid", {"x_lines": [{"id": None, "fraction": 0.0}], "y_lines": []}, {}, VF, codes.WRONG_TYPE, "args.x_lines[0]", None),
    ("fractions-unordered", "SetTimberGrid", _unordered(), {}, VF, codes.NOT_STRICTLY_ASCENDING, epath(GRID, "x_lines", 2, "fraction"), ["args.x_lines[2].fraction"]),
    ("role-retired", "SetMemberSection", {"role": "RAFTER", "section_id": SECTIONS["8x8"].id}, {}, VF, codes.INVALID_ENUM, "args.role", None),
    ("role-unknown", "SetMemberSection", {"role": "COLUMN", "section_id": SECTIONS["8x8"].id}, {}, VF, codes.INVALID_ENUM, "args.role", None),
    ("section-missing", "SetMemberSection", {"role": "POST", "section_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"}, {}, VF, codes.DANGLING_REFERENCE, "args.section_id", None),
    ("section-wrong-kind", "SetMemberSection", {"role": "POST", "section_id": MATERIAL.id}, {}, VF, codes.WRONG_REFERENCE_KIND, "args.section_id", None),
    ("story-height-15ft", "SetStoryHeights", {"story_heights_m": [4.572, 2.7432]}, {}, UC, codes.OUT_OF_SUPPORTED_RANGE, epath(L0, "story_height_m"), ["args.story_heights_m[0]"]),
    ("undo-unknown-target", "UndoToRevision", {"target_revision_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"}, {}, VF, codes.DANGLING_REFERENCE, "args.target_revision_id", None),
    ("project-mismatch", "SetFootprintDimensions", {"width_m": 12, "depth_m": 7}, {"project_id": P2}, VF, codes.DANGLING_REFERENCE, "project_id", None),
]


@pytest.mark.parametrize("name,type_,args,overrides,top,code,path,related", REJECTIONS, ids=[r[0] for r in REJECTIONS])
def test_rejections(name, type_, args, overrides, top, code, path, related):
    before = canonical_snapshot(BASE)
    result = run(type_, args, **overrides)
    assert not result.accepted
    assert result.rejection.code == top, result.rejection.to_dict()
    issue = next((i for i in result.rejection.issues if (i.code, i.path) == (code, path)), None)
    assert issue is not None, result.rejection.to_dict()
    if related is not None:
        assert list(issue.related_paths) == related
    assert canonical_snapshot(BASE) == before  # 5. base unchanged


def test_creation_envelope_is_not_accepted_by_propose():
    result = propose(BASE, {"command_id": CID, "type": "CreateReferenceProject", "args": {}}, actor_id=ACTOR, at=AT)
    assert (result.rejection.code, result.rejection.issues[0].code, result.rejection.issues[0].path) == (VF, codes.INVALID_ENUM, "type")
    # A creation command wrapped in a normal envelope fails stage 1: the creation envelope has no project or base.
    wrapped = run("CreateReferenceProject", {})
    assert {i.path for i in wrapped.rejection.issues} == {"project_id", "base_revision_id"}


def test_stale_base_is_a_revision_conflict():
    result = run("SetFootprintDimensions", {"width_m": "not even valid"}, base_revision_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    assert result.rejection.code == "REVISION_CONFLICT" and result.rejection.issues == ()


# --- 5./6. immutability and determinism ------------------------------------------


def test_base_unchanged_after_accepted_command():
    before = canonical_snapshot(BASE)
    assert run("SetFootprintDimensions", {"width_m": 12.192, "depth_m": FP.depth_m}).accepted
    assert canonical_snapshot(BASE) == before


def test_preview_and_commit_agree():
    args = {"x_lines": lines("x_lines")[:2] + [{"fraction": 0.5}] + lines("x_lines")[2:], "y_lines": lines("y_lines")}
    preview = run("SetTimberGrid", args, at=AT).change
    commit = run("SetTimberGrid", args, at=AT2).change
    assert preview.to_preview_dict() == commit.to_preview_dict()
    assert preview.revision_id == commit.revision_id and preview.operation_id == commit.operation_id
    a = preview.candidate.model_dump(mode="json")
    b = commit.candidate.model_dump(mode="json")
    assert (a.pop("created_at"), b.pop("created_at")) == (AT, AT2)
    assert canonical_json(a) == canonical_json(b)
    again = run("SetTimberGrid", args, at=AT).change
    assert canonical_snapshot(again.candidate) == canonical_snapshot(preview.candidate)


# --- 7./8. ID minting --------------------------------------------------------------


@pytest.mark.parametrize("case", VECTORS["ids"]["cases"], ids=lambda c: c["id"])
def test_mint_matches_independent_uuidv5(case):
    assert VECTORS["ids"]["namespace"] == "6652101f-3d1d-4a2b-bd82-9d87e0207354"
    assert mint(*case["parts"]) == case["id"]


def test_d041_documented_vector():
    assert mint("entity", P, ACTOR, CREATE_ID, "generation/frame/x0/y0/level-0/post") == "5f9ff518-e552-59c3-b2a6-798263c3f9ac"


def test_two_actors_same_command_id_mint_different_ids():
    args = {"x_lines": lines("x_lines")[:2] + [{"fraction": 0.5}] + lines("x_lines")[2:], "y_lines": lines("y_lines")}
    a = run("SetTimberGrid", args, actor=ACTOR).change
    b = run("SetTimberGrid", args, actor=ACTOR_B).change
    assert a.revision_id != b.revision_id
    assert not {m["id"] for m in a.members.added} & {m["id"] for m in b.members.added}


# --- 9. undo ------------------------------------------------------------------------


def test_undo_round_trip_restores_original_ids():
    removed = run("SetTimberGrid", {"x_lines": [line for line in lines("x_lines") if line["id"] != "x2"], "y_lines": lines("y_lines")}).change
    mid = removed.candidate
    undo = run("UndoToRevision", {"target_revision_id": BASE.revision_id}, base=mid, target=BASE, cid="33333333-3333-4333-8333-333333333333").change
    cand = undo.candidate
    assert cand.parent_revision_id == mid.revision_id and cand.revision_id not in (BASE.revision_id, mid.revision_id)
    content = lambda s: canonical_json({"building": s.model_dump(mode="json")["building"], "entities": sorted(s.model_dump(mode="json")["entities"], key=lambda e: e["id"])})  # noqa: E731
    assert content(cand) == content(BASE)
    assert {m["id"] for m in undo.members.added} == {m["id"] for m in removed.members.removed}  # D044: original IDs
    assert {c["id"] for c in undo.connections.added} == {c["id"] for c in removed.connections.removed}


def test_undo_to_identical_content_is_noop():
    change = run("UndoToRevision", {"target_revision_id": BASE.revision_id}, target=BASE).change
    assert change.is_noop and change.to_preview_dict()["revision_id"] is None


# --- 10. template ------------------------------------------------------------------


def test_template_package_copy_matches_fixture():
    from homedesign.model.commands.propose import _template_text

    assert _template_text() == (REPO_ROOT / "docs/reference-projects/vermont-timber-house/fixture.snapshot.json").read_text(encoding="utf-8")


def test_created_project_equals_fixture_exactly():
    """TIMBER-002 §7: the fixture stores generator output, so only IDs and revision metadata differ."""
    result = create()
    change, cand = result.change, result.change.candidate
    assert cand.parent_revision_id is None and cand.project_id == P
    assert len(change.members.added) == 193 and change.classification == "consequential"
    assert len(change.connections.added) == 312  # CONN-001 §5.2: minted by the regeneration
    id_map = {}
    generated = ("TimberMember", "Connection", "Wall", "WallFramingPiece")
    fixture_records = [FIXTURE["building"], *(e for e in FIXTURE["entities"] if e["kind"] not in generated)]
    for record in fixture_records:
        id_map[record["id"]] = mint("entity", P, ACTOR, CREATE_ID, "template/" + record["id"])
    for wall in (e for e in FIXTURE["entities"] if e["kind"] == "Wall"):  # MODEL-006 §9.2: openings follow their walls
        id_map[wall["id"]] = mint("entity", P, ACTOR, CREATE_ID, "generation/" + wall["generation_key"])

    def remap(v):
        if isinstance(v, dict):
            return {k: remap(x) for k, x in v.items()}
        if isinstance(v, list):
            return [remap(x) for x in v]
        return id_map.get(v, v) if isinstance(v, str) else v

    created = {e["id"]: e for e in [cand.model_dump(mode="json")["building"], *cand.model_dump(mode="json")["entities"]]}
    for record in fixture_records:
        expected = remap(record)
        if record["kind"] == "FrameSystem":
            expected["member_ids"] = created[expected["id"]]["member_ids"]
            expected["connection_ids"] = created[expected["id"]]["connection_ids"]
        if record["kind"] == "WallSystem":
            expected["opening_ids"] = sorted(expected["opening_ids"])  # ID order, and the IDs are new
        assert created[expected["id"]] == expected
    fixture_members = {e["generation_key"]: e for e in FIXTURE["entities"] if e["kind"] == "TimberMember"}
    for key, member in members_by_key(cand).items():
        f = fixture_members[key]
        assert member.id == mint("entity", P, ACTOR, CREATE_ID, "generation/" + key)
        assert (member.member_role, member.section_id, member.material_id) == (f["member_role"], id_map[f["section_id"]], id_map[f["material_id"]])
        assert (member.start_m, member.end_m) == (f["start_m"], f["end_m"])  # bit-identical
    assert set(fixture_members) == set(members_by_key(cand))
    member_keys = {m.id: m.generation_key for m in of_kind(cand, "TimberMember")}
    fixture_member_keys = {m["id"]: k for k, m in fixture_members.items()}
    fixture_connections = {e["generation_key"]: e for e in FIXTURE["entities"] if e["kind"] == "Connection"}
    assert set(fixture_connections) == set(connections_by_key(cand))
    for key, connection in connections_by_key(cand).items():
        f = fixture_connections[key]
        assert connection.id == mint("entity", P, ACTOR, CREATE_ID, "generation/" + key)
        assert (connection.junction_class, connection.connection_type) == (f["junction_class"], f["connection_type"])
        assert [member_keys[i] for i in connection.member_ids] == [fixture_member_keys[i] for i in f["member_ids"]]
        assert connection.location_m == f["location_m"]  # bit-identical


def test_two_projects_share_no_ids():
    a = create(P).change.candidate
    b = create(P2).change.candidate
    ids = lambda s: {s.building.id, s.revision_id, *(e.id for e in s.entities)}  # noqa: E731
    assert not ids(a) & ids(b)


def test_create_rejects_other_types():
    result = propose_create(cmd("SetFootprintDimensions", {"width_m": 12, "depth_m": 7}), project_id=P, actor_id=ACTOR, at=AT)
    assert result.rejection.issues[0].path == "type"


# --- 11. no-op -------------------------------------------------------------------------


def test_noop_on_generated_base():
    change = run("SetFootprintDimensions", {"width_m": FP.width_m, "depth_m": FP.depth_m}).change
    preview = change.to_preview_dict()
    assert change.is_noop and preview["revision_id"] is None and preview["confirmation_required"] is False
    assert preview["changes"] == [] and preview["members"] == {"added": [], "removed": [], "updated": []}
    assert preview["connections"] == {"added": [], "removed": [], "updated": []}  # D045


def test_fixture_base_is_exact_generator_output():
    # TIMBER-002 §7: regenerating the fixture with its own parameters changes nothing.
    fixture = Snapshot.model_validate(FIXTURE)
    change = run("SetFootprintDimensions", {"width_m": 10.9728, "depth_m": 7.3152}, base=fixture).change
    assert change.is_noop and not change.members.updated and change.changes == ()


# --- preview contract and classification -----------------------------------------------


def test_preview_dict_shape():
    preview = run("SetFootprintDimensions", {"width_m": 12.192, "depth_m": FP.depth_m}).change.to_preview_dict()
    assert set(preview) == {
        "base_revision_id", "revision_id", "command_hash", "classification", "classification_version",
        "confirmation_required", "is_noop", "changes", "members", "connections", "walls", "wall_framing", "warnings",
    }  # impacted_artifacts is computed by the service, which knows the derivations (DEP-001 §6)
    assert preview["classification_version"] == CLASSIFICATION_VERSION
    assert preview["warnings"][0]["code"] == "PRELIMINARY_UNVERIFIED"
    assert preview["command_hash"].startswith("sha256:")
    json.dumps(preview, allow_nan=False)


def test_classification_table_matches_dependencies_doc():
    text = (REPO_ROOT / "docs/architecture/dependencies.md").read_text(encoding="utf-8")
    section = text[text.index("### 4.1") : text.index("## 5.")]
    documented = dict(re.findall(r"^\| `(\w+)` \| (routine|consequential) \|", section, flags=re.MULTILINE))
    assert documented == CLASSIFICATION
    assert CLASSIFICATION_VERSION in section


# --- 12. robustness -----------------------------------------------------------------------

numbers = st.one_of(st.floats(allow_nan=True, allow_infinity=True), st.integers(min_value=-10**20, max_value=10**20))
json_values = st.recursive(
    st.none() | st.booleans() | numbers | st.text(max_size=8),
    lambda c: st.lists(c, max_size=4) | st.dictionaries(st.text(max_size=8), c, max_size=4),
    max_leaves=16,
)


def _check(result):
    if result.accepted:
        assert validate_value(result.change.candidate.model_dump(mode="json")).valid
        json.dumps(result.change.to_preview_dict(), allow_nan=False)
    else:
        assert result.rejection.code is not None


@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
@given(json_values)
def test_arbitrary_commands_never_raise(value):
    _check(propose(BASE, value, actor_id=ACTOR, at=AT))


@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
@given(numbers, numbers)
def test_random_footprints_never_raise(width, depth):
    _check(run("SetFootprintDimensions", {"width_m": width, "depth_m": depth}))


@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
@given(
    st.lists(st.fixed_dictionaries({"fraction": st.floats(-0.5, 1.5)}, optional={"id": st.sampled_from(["x0", "x1", "x2", "x3", "x9", "y0"])}), max_size=8),
    st.lists(st.fixed_dictionaries({"fraction": st.floats(-0.5, 1.5)}, optional={"id": st.sampled_from(["y0", "y1", "y2", "x0"])}), max_size=8),
)
def test_random_grids_never_raise(x_lines, y_lines):
    _check(run("SetTimberGrid", {"x_lines": x_lines, "y_lines": y_lines}))


# --- 13. command schema -----------------------------------------------------------------------


def test_committed_command_schema_is_current():
    assert COMMANDS_SCHEMA_PATH.read_text(encoding="utf-8") == render_commands_schema()


def test_command_schema_validates_examples():
    schema = json.loads(COMMANDS_SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    good = [
        {"command_id": CID, "type": "CreateReferenceProject", "args": {}},
        cmd("SetFootprintDimensions", {"width_m": 12.192, "depth_m": 7.3152}),
        cmd("SetStoryHeights", {"story_heights_m": [3.048, 2.7432]}),
        cmd("SetGableRoofParameters", {"pitch_rad": 0.6435011087932844, "eave_overhang_m": 0.6096}),
        cmd("SetTimberGrid", {"x_lines": [{"id": "x0", "fraction": 0}, {"fraction": 0.5}, {"id": "x3", "fraction": 1}], "y_lines": lines("y_lines")}),
        cmd("SetMemberSection", {"role": "POST", "section_id": SECTIONS["8x12"].id}),
        cmd("AddSection", {"nominal_label": "10x12", "actual_width_m": 0.254, "actual_depth_m": 0.3048}),
        cmd("UndoToRevision", {"target_revision_id": BASE.revision_id}),
    ]
    for example in good:
        validator.validate(example)
    for bad in (cmd("SetFootprintDimensions", {"width_m": 12}), cmd("SetWallHeight", {}), {"type": "CreateReferenceProject", "args": {}}):
        assert not validator.is_valid(bad)


@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    spacing=st.floats(-1, 2, allow_nan=False),
    purlins=st.one_of(st.integers(-2, 6), st.floats(-1, 5, allow_nan=False)),
    leg=st.floats(-1, 2, allow_nan=False),
    level_1=st.booleans(),
    eave=st.booleans(),
)
def test_frame_parameters_never_raise(spacing, purlins, leg, level_1, eave):
    """MODEL-005 §10 test 11: random SetFrameParameters never raise; accepted candidates re-validate."""
    args = {"joist_spacing_m": spacing, "purlins_per_slope": purlins, "knee_brace_leg_m": leg, "knee_braces_level_1": level_1, "knee_braces_eave": eave}
    result = run("SetFrameParameters", args)
    if result.accepted:
        assert validate_value(result.change.candidate.model_dump(mode="json")).valid
    else:
        assert result.rejection.code in (VF, UC)
