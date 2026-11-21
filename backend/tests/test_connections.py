"""CONN-001 §12: connection generation, identity, the preview diff, and `SetConnectionType`.

Junction rules (§4, D059), keys (§5), counts (§6), regeneration (§7), and the command (§8).
Conformance mutations (§12 test 8) are in test_mutations.py; counts for the VS-01 commands are
asserted, with their reasons, in test_commands.py.
"""

from __future__ import annotations

import json
import math
import random
import time
import uuid
from collections import Counter

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from api_support import make_api
from conftest import FIXTURE, VECTORS_PATH, entities_of, fresh_fixture, grid_doc, largest_doc, regenerate, with_frame_parameters
from homedesign.model import canonical_json, codes, validate_value
from homedesign.model.commands import CLASSIFICATION, mint, propose, propose_create
from homedesign.model.connections import ALTERNATIVES, CONNECTION_TYPES, DEFAULTS, JUNCTION_CLASSES
from homedesign.model.schema import Connection, Snapshot
from homedesign.project import MemoryStore
from homedesign.timber import get_rule

RULE = get_rule("vs02-frame-1")
FT = 0.3048
P = "17ac32e0-0b3b-518e-b568-adf98f41bcd0"
ACTOR = "00000000-0000-4000-8000-000000000001"
CID = "44444444-4444-4444-8444-444444444444"
AT = "2026-11-20T12:00:00Z"
VF, UC = codes.VALIDATION_FAILED, codes.UNSUPPORTED_CONFIGURATION

# Receiving and entering roles per class (§4.2). Brace connections are received by a post (lower
# end) or the brace's own beam (upper end).
ROLES = {
    "post-beam": ({"POST"}, "BEAM"),
    "post-sill": ({"SILL"}, "POST"),
    "brace": ({"POST", "BEAM"}, "KNEE_BRACE"),
    "joist-beam": ({"BEAM"}, "FLOOR_JOIST"),
    "rafter-peak": ({"PRINCIPAL_RAFTER"}, "PRINCIPAL_RAFTER"),
    "rafter-foot": ({"BEAM"}, "PRINCIPAL_RAFTER"),
    "purlin-rafter": ({"PRINCIPAL_RAFTER"}, "PURLIN"),
}
REFERENCE_COUNTS = {
    "post-beam": 68, "post-sill": 12, "brace": 136, "joist-beam": 60, "rafter-peak": 4, "rafter-foot": 8, "purlin-rafter": 24,
}


def _utf16(text: str) -> bytes:
    return text.encode("utf-16-be")


def _snapshot(doc) -> Snapshot:
    return Snapshot.model_validate(doc)


def _frame(doc):
    return entities_of(doc, "FrameSystem")[0]








def _expected_counts(doc) -> Counter:
    """§6, restated from the member counts: two per beam, brace, joist, and purlin; one per
    Level 0 post; three per rafter pair."""
    grid = entities_of(doc, "TimberGrid")[0]
    nx, ny = len(grid["x_lines"]), len(grid["y_lines"])
    roles = Counter(m.member_role for m in RULE.generate(_snapshot(doc)))
    b = ny * (nx - 1) + nx * (ny - 1)
    assert roles["BEAM"] == 2 * b
    return +Counter({
        "post-beam": 4 * b,
        "post-sill": nx * ny,
        "brace": 2 * roles["KNEE_BRACE"],
        "joist-beam": 2 * roles["FLOOR_JOIST"],
        "rafter-peak": nx,
        "rafter-foot": 2 * nx,
        "purlin-rafter": 2 * roles["PURLIN"],
    })


def _on_axis(point, start, end, eps=1e-9) -> bool:
    ab = [e - s for s, e in zip(start, end)]
    ap = [p - s for s, p in zip(start, point)]
    t = sum(a * b for a, b in zip(ap, ab)) / sum(c * c for c in ab)
    closest = [s + t * c for s, c in zip(start, ab)]
    return -eps <= t <= 1 + eps and math.dist(point, closest) <= eps


def _check_junctions(doc) -> tuple:
    """§12 test 2 for every connection of ``doc``; returns the connections."""
    snapshot = _snapshot(doc)
    members = {m.generation_key: m for m in RULE.generate(snapshot)}
    connections = RULE.generate_connections(snapshot)
    defaults = _frame(doc)["connection_defaults"]
    for c in connections:
        receiving, entering = (members[k] for k in c.member_keys)
        receiving_roles, entering_role = ROLES[c.junction_class]
        assert receiving.member_role in receiving_roles and entering.member_role == entering_role, c.generation_key
        # Copied, bit for bit, from the entering member's endpoint.
        assert c.location_m in (entering.start_m, entering.end_m), c.generation_key
        assert _on_axis(c.location_m, receiving.start_m, receiving.end_m), c.generation_key
        assert c.connection_type == defaults[c.junction_class]
    return connections


# --- 1. the fixture's connections (AC2-03, AC2-06) ----------------------------------------------


def test_fixture_connections_are_exact_rule_output():
    generated = RULE.generate_connections(_snapshot(FIXTURE))
    member_ids = {m["generation_key"]: m["id"] for m in entities_of(FIXTURE, "TimberMember")}
    stored = {c["generation_key"]: c for c in entities_of(FIXTURE, "Connection")}
    assert [c.generation_key for c in generated] == sorted(stored, key=_utf16)
    for c in generated:
        record = stored[c.generation_key]
        assert {k: v for k, v in record.items() if k not in ("id", "kind", "schema_version")} == c.to_json([member_ids[k] for k in c.member_keys])
        assert record["location_m"] == list(c.location_m)  # bit-identical
    assert Counter(c.junction_class for c in generated) == REFERENCE_COUNTS
    assert len(generated) == 312 == sum(REFERENCE_COUNTS.values())
    frame = _frame(FIXTURE)
    assert frame["connection_ids"] == [stored[c.generation_key]["id"] for c in generated]
    assert len(FIXTURE["entities"]) == 518


def test_reference_house_receiving_members():
    """D059's choices where several members could receive (§4.3)."""
    by_key = {c.generation_key: c for c in RULE.generate_connections(_snapshot(FIXTURE))}
    examples = [
        # A beam end on plane-L1 enters the post below (Level 0), not the Level 1 post's foot.
        "connection/post-beam/frame/x1/y0/level-0/post/frame/axis-x/y0/x0-x1/plane-L1/beam",
        "connection/post-beam/frame/x1/y0/level-1/post/frame/axis-x/y0/x0-x1/plane-eave/beam",
        # Post feet enter the Y sill in their bent: the bay starting here, or ending on the last line.
        "connection/post-sill/frame/axis-y/x2/y1-y2/plane-L0/sill/frame/x2/y1/level-0/post",
        "connection/post-sill/frame/axis-y/x2/y1-y2/plane-L0/sill/frame/x2/y2/level-0/post",
        # A brace's lower end enters the post below; its upper end, its own beam.
        "connection/brace/frame/x0/y0/level-0/post/frame/axis-x/y0/x0-x1/plane-L1/brace/x0",
        "connection/brace/frame/axis-x/y0/x0-x1/plane-L1/beam/frame/axis-x/y0/x0-x1/plane-L1/brace/x0",
        # Joist ends enter the X beams of their Y lines, in their X bay.
        "connection/joist-beam/frame/axis-x/y0/x0-x1/plane-L1/beam/frame/axis-y/x0-x1/j1/y0-y1/plane-L1/joist",
        "connection/joist-beam/frame/axis-x/y1/x0-x1/plane-L1/beam/frame/axis-y/x0-x1/j1/y0-y1/plane-L1/joist",
        # South receives at the peak; rafter feet enter the tie beam in their bent.
        "connection/rafter-peak/frame/roof/x0/south/principal-rafter/frame/roof/x0/north/principal-rafter",
        "connection/rafter-foot/frame/axis-y/x0/y0-y1/plane-eave/beam/frame/roof/x0/south/principal-rafter",
        "connection/rafter-foot/frame/axis-y/x0/y1-y2/plane-eave/beam/frame/roof/x0/north/principal-rafter",
        "connection/purlin-rafter/frame/roof/x1/south/principal-rafter/frame/roof/x0-x1/south/p1/purlin",
    ]
    for key in examples:
        assert key in by_key, key
    peak = by_key[examples[8]]
    assert peak.location_m == (0.0, 7.3152 / 2, peak.location_m[2]) and abs(peak.location_m[2] - 8.5344) <= 1e-12
    assert by_key[examples[0]].location_m == (0.0 + 10.9728 * (1 / 3), 0.0, 3.048)  # x1, evaluated as written
    assert by_key[examples[4]].location_m == (0.0, 0.0, 3.048 - 0.9144)


def test_level_1_posts_sills_and_x_beams_only_receive():
    """§6 reconciliation: Level 1 posts, sills, and X eave and Level 1 beams never enter."""
    entering = {c.member_keys[1] for c in RULE.generate_connections(_snapshot(FIXTURE))}
    for m in RULE.generate(_snapshot(FIXTURE)):
        if m.member_role == "SILL" or "/level-1/post" in m.generation_key:
            assert m.generation_key not in entering
    per_member = Counter(c.member_keys[1] for c in RULE.generate_connections(_snapshot(FIXTURE)))
    for m in RULE.generate(_snapshot(FIXTURE)):
        want = {"BEAM": 2, "KNEE_BRACE": 2, "FLOOR_JOIST": 2, "PURLIN": 2, "SILL": 0}.get(m.member_role)
        if m.member_role == "POST":
            want = 1 if "/level-0/" in m.generation_key else 0
        if m.member_role == "PRINCIPAL_RAFTER":
            want = 2 if "/north/" in m.generation_key else 1
        assert per_member[m.generation_key] == want, m.generation_key


# --- 2./3. junction rules and counts ----------------------------------------------------------


def test_junction_rules_hold_for_the_fixture():
    assert len(_check_junctions(FIXTURE)) == 312


@pytest.mark.parametrize("nx", range(2, 8))
@pytest.mark.parametrize("ny", range(2, 8))
def test_counts_for_every_supported_grid(nx, ny):
    doc = grid_doc(nx, ny)
    assert validate_value(doc).valid
    connections = _check_junctions(doc)
    assert Counter(c.junction_class for c in connections) == _expected_counts(doc)
    members = RULE.generate(_snapshot(doc))
    keys = [m.generation_key for m in members] + [c.generation_key for c in connections]
    assert len(set(keys)) == len(keys)  # unique across members and connections (MODEL-005 §6.2)


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
def test_counts_at_parameter_bounds(parameters):
    doc = with_frame_parameters(**parameters)
    assert validate_value(doc).valid
    assert Counter(c.junction_class for c in _check_junctions(doc)) == _expected_counts(doc)


def test_largest_supported_case():
    """§6: 7 × 7 stations, 12" joists, 4 purlins, both brace planes: 2,110 connections."""
    doc = largest_doc()
    assert validate_value(doc).valid
    connections = _check_junctions(doc)
    assert len(RULE.generate(_snapshot(doc))) == 1216
    assert len(connections) == 2110
    assert Counter(c.junction_class for c in connections) == {
        "post-beam": 336, "post-sill": 49, "brace": 672, "joist-beam": 936, "rafter-peak": 7, "rafter-foot": 14, "purlin-rafter": 96,
    }


def test_largest_case_propose_time(capsys):
    """§12 test 3: the `propose` time for 2,110 connections is reported; TEST-002 sets any budget."""
    base = _snapshot(largest_doc())
    current = base.model_dump(mode="json")
    footprint = next(e for e in current["entities"] if e["kind"] == "Footprint")
    # One foot narrower: every connection is regenerated and most move.
    command = {"command_id": CID, "project_id": base.project_id, "base_revision_id": base.revision_id,
               "type": "SetFootprintDimensions", "args": {"width_m": footprint["width_m"] - 0.3048, "depth_m": footprint["depth_m"]}}
    start = time.perf_counter()
    result = propose(base, command, actor_id=ACTOR, at=AT)
    elapsed = time.perf_counter() - start
    assert result.accepted, result.rejection and result.rejection.to_dict()
    assert len(entities_of(result.change.candidate.model_dump(mode="json"), "Connection")) == 2110
    with capsys.disabled():
        print(f"\n[CONN-001] propose, largest supported case (1,216 members, 2,110 connections): {elapsed:.3f} s")


# --- 4. keys ------------------------------------------------------------------------------------


def test_keys_split_back_into_member_keys():
    for doc in (FIXTURE, largest_doc()):
        snapshot = _snapshot(doc)
        member_keys = {m.generation_key for m in RULE.generate(snapshot)}
        assert all(k.startswith("frame/") and "/frame/" not in k for k in member_keys)
        for c in RULE.generate_connections(snapshot):
            assert c.generation_key.startswith(f"connection/{c.junction_class}/frame/")
            rest = c.generation_key[len(f"connection/{c.junction_class}/"):]
            split = rest.index("/frame/")
            assert (rest[:split], rest[split + 1:]) == c.member_keys
            assert set(c.member_keys) <= member_keys
    assert max(len(c.generation_key) for c in RULE.generate_connections(_snapshot(FIXTURE))) == 100


def test_connection_ids_sorted_by_key():
    keys = [c["generation_key"] for c in entities_of(FIXTURE, "Connection")]
    by_id = {c["id"]: c["generation_key"] for c in entities_of(FIXTURE, "Connection")}
    listed = [by_id[i] for i in _frame(FIXTURE)["connection_ids"]]
    assert listed == sorted(keys, key=_utf16)
    assert [k.split("/")[1] for k in listed] == sorted((k.split("/")[1] for k in listed), key=_utf16)  # grouped by class


# --- 5./6. identity and the preview diff ------------------------------------------------------


def _create():
    result = propose_create({"command_id": "b8f9d645-5a10-4eb5-b2ca-38ce46e5d4aa", "type": "CreateReferenceProject", "args": {}},
                            project_id=P, actor_id=ACTOR, at=AT)
    assert result.accepted
    return result.change.candidate


BASE = _create()
BASE_FRAME = next(e for e in BASE.entities if e.kind == "FrameSystem")


def run(type_, args, base=BASE, cid=CID, target=None):
    command = {"command_id": cid, "project_id": base.project_id, "base_revision_id": base.revision_id, "type": type_, "args": args}
    return propose(base, command, actor_id=ACTOR, at=AT, target=target)


def connections_of(snapshot) -> dict[str, Connection]:
    return {e.generation_key: e for e in snapshot.entities if e.kind == "Connection"}


def _parameters(**changes):
    return {**BASE_FRAME.parameters.model_dump(mode="json"), **changes}


def test_preview_diff_lists_exactly_the_changed_records():
    change = run("SetFrameParameters", _parameters(knee_braces_eave=False, purlins_per_slope=3)).change
    preview = change.to_preview_dict()
    before, after = connections_of(BASE), connections_of(change.candidate)
    added, removed = after.keys() - before.keys(), before.keys() - after.keys()
    assert [c["generation_key"] for c in preview["connections"]["added"]] == sorted(added, key=_utf16)
    assert [c["generation_key"] for c in preview["connections"]["removed"]] == sorted(removed, key=_utf16)
    assert all(c["id"] == after[c["generation_key"]].id for c in preview["connections"]["added"])  # IDs the commit creates
    assert all(c["id"] == mint("entity", P, ACTOR, CID, "generation/" + c["generation_key"]) for c in preview["connections"]["added"])
    assert all(c["id"] == before[c["generation_key"]].id for c in preview["connections"]["removed"])
    moved = sorted(c.id for k, c in before.items() if k in after and c.model_dump() != after[k].model_dump())
    assert preview["connections"]["updated"] == moved
    assert all(k.startswith("connection/brace/") for k in removed) and len(removed) == 68
    assert {k.split("/")[1] for k in added} == {"purlin-rafter"} and len(added) == 12
    # Generated records never appear in `changes`; the frame's connection_ids do.
    assert not {c["entity_kind"] for c in preview["changes"]} & {"Connection", "TimberMember"}
    assert ("FrameSystem", "connection_ids") in {(c["entity_kind"], c["field"]) for c in preview["changes"]}


def test_surviving_connections_keep_ids_and_members():
    """§5.2 invariant across a chain of edits."""
    snapshot = BASE
    steps = [
        ("SetFootprintDimensions", {"width_m": 12.192, "depth_m": 7.3152}),
        ("SetStoryHeights", {"story_heights_m": [3.3528, 2.7432]}),
        ("SetGableRoofParameters", {"pitch_rad": 0.5, "eave_overhang_m": 0.3048}),
        ("SetFrameParameters", _parameters(joist_spacing_m=0.4064, purlins_per_slope=1)),
    ]
    for k, (type_, args) in enumerate(steps):
        change = run(type_, args, base=snapshot, cid=str(uuid.UUID(int=k + 1, version=4))).change
        before, after = connections_of(snapshot), connections_of(change.candidate)
        for key in before.keys() & after.keys():
            assert (after[key].id, after[key].member_ids) == (before[key].id, before[key].member_ids), key
        snapshot = change.candidate


def test_member_section_changes_no_connection():
    sections = [e for e in BASE.entities if e.kind == "Section"]
    other = next(s for s in sections if s.id != BASE_FRAME.member_defaults["KNEE_BRACE"].section_id)
    change = run("SetMemberSection", {"role": "KNEE_BRACE", "section_id": other.id}).change
    c = change.connections
    assert not (c.added or c.removed or c.updated)  # D058: sections never move axes


def test_brace_toggle_mints_new_ids_and_undo_restores_originals():
    off = run("SetFrameParameters", _parameters(knee_braces_level_1=False)).change
    assert len(off.connections.removed) == 68 and not off.connections.added
    on = run("SetFrameParameters", _parameters(knee_braces_level_1=True), base=off.candidate, cid="55555555-5555-4555-8555-555555555555").change
    original = {c["generation_key"]: c["id"] for c in off.connections.removed}
    returned = {c["generation_key"]: c["id"] for c in on.connections.added}
    assert returned.keys() == original.keys()
    assert not set(returned.values()) & set(original.values())  # D041: never reused
    undo = run("UndoToRevision", {"target_revision_id": BASE.revision_id}, base=on.candidate, target=BASE, cid="66666666-6666-4666-8666-666666666666").change
    assert {c["generation_key"]: c["id"] for c in undo.connections.added} == original  # D044
    assert {c["id"] for c in undo.connections.removed} == set(returned.values())


def test_spacing_and_purlin_changes_keep_surviving_ordinals():
    wider = run("SetFrameParameters", _parameters(joist_spacing_m=0.9144)).change  # 3 joists per bay, j1–j3 kept
    assert {c["generation_key"].split("/")[1] for c in wider.connections.removed} == {"joist-beam"}
    assert all("/j4/" in c["generation_key"] or "/j5/" in c["generation_key"] for c in wider.connections.removed)
    assert len(wider.connections.removed) == 2 * 2 * 3 * 2 and not wider.connections.added
    fewer = run("SetFrameParameters", _parameters(purlins_per_slope=1)).change
    assert all("/p2/purlin" in c["generation_key"] for c in fewer.connections.removed) and len(fewer.connections.removed) == 12
    assert len(fewer.connections.updated) == 12  # p1 moves to mid-slope


def test_noop_has_empty_connection_lists():
    change = run("SetFrameParameters", _parameters()).change
    assert change.is_noop
    assert change.to_preview_dict()["connections"] == {"added": [], "removed": [], "updated": []}


# --- 7. SetConnectionType ---------------------------------------------------------------------


@pytest.mark.parametrize("junction_class", JUNCTION_CLASSES)
def test_set_connection_type_switches_one_class_and_back(junction_class):
    change = run("SetConnectionType", {"junction_class": junction_class, "connection_type": ALTERNATIVES[junction_class]}).change
    assert change.classification == "consequential" and change.confirmation_required
    assert not (change.members.added or change.members.removed or change.members.updated)
    assert not (change.connections.added or change.connections.removed)
    of_class = sorted(c.id for c in BASE.entities if c.kind == "Connection" and c.junction_class == junction_class)
    assert sorted(change.connections.updated) == of_class and len(of_class) == REFERENCE_COUNTS[junction_class]
    for c in connections_of(change.candidate).values():
        assert c.connection_type == (ALTERNATIVES[junction_class] if c.junction_class == junction_class else DEFAULTS[c.junction_class])
    assert [(c["entity_kind"], c["field"]) for c in change.changes] == [("FrameSystem", "connection_defaults")]
    back = run("SetConnectionType", {"junction_class": junction_class, "connection_type": DEFAULTS[junction_class]},
               base=change.candidate, cid="77777777-7777-4777-8777-777777777777").change
    assert sorted(back.connections.updated) == of_class
    strip = lambda s: canonical_json(sorted((e.model_dump(mode="json") for e in s.entities), key=lambda e: e["id"]))  # noqa: E731
    assert strip(back.candidate) == strip(BASE)


def test_set_connection_type_current_type_is_noop():
    change = run("SetConnectionType", {"junction_class": "joist-beam", "connection_type": "HOUSED_DOVETAIL"}).change
    assert change.is_noop and not change.confirmation_required
    assert change.to_preview_dict()["revision_id"] is None


def test_set_connection_type_for_a_class_with_no_connections():
    off = run("SetFrameParameters", _parameters(knee_braces_level_1=False, knee_braces_eave=False)).change
    change = run("SetConnectionType", {"junction_class": "brace", "connection_type": "STEEL_KNIFE_PLATE"},
                 base=off.candidate, cid="88888888-8888-4888-8888-888888888888").change
    assert not change.is_noop
    assert change.to_preview_dict()["connections"] == {"added": [], "removed": [], "updated": []}
    frame = next(e for e in change.candidate.entities if e.kind == "FrameSystem")
    assert frame.connection_defaults["brace"] == "STEEL_KNIFE_PLATE"


FRAME_PATH = f"entities[{BASE_FRAME.id}]"
ERRORS = [
    ("missing-type", {"junction_class": "brace"}, VF, codes.MISSING_FIELD, "args.connection_type", None),
    ("missing-class", {"connection_type": "BRIDLE"}, VF, codes.MISSING_FIELD, "args.junction_class", None),
    ("unknown-arg", {"junction_class": "brace", "connection_type": "BRIDLE", "member_id": "x"}, VF, codes.UNKNOWN_FIELD, "args.member_id", None),
    ("args-not-an-object", "brace", VF, codes.WRONG_TYPE, "args", None),
    # Like SetMemberSection's role, an enum argument of another JSON type is not one of the values.
    ("class-not-a-string", {"junction_class": 3, "connection_type": "BRIDLE"}, VF, codes.INVALID_ENUM, "args.junction_class", None),
    ("unknown-class", {"junction_class": "post-post", "connection_type": "BRIDLE"}, VF, codes.INVALID_ENUM, "args.junction_class", None),
    ("unknown-type", {"junction_class": "brace", "connection_type": "LAG_SCREW"}, VF, codes.INVALID_ENUM, "args.connection_type", None),
    ("disallowed-pair", {"junction_class": "joist-beam", "connection_type": "BRIDLE"}, UC, codes.UNSUPPORTED_VALUE,
     FRAME_PATH + '.connection_defaults["joist-beam"]', ["args.connection_type"]),
]


@pytest.mark.parametrize("name,args,top,code,path,related", ERRORS, ids=[e[0] for e in ERRORS])
def test_set_connection_type_errors(name, args, top, code, path, related):
    rejection = run("SetConnectionType", args).rejection
    assert rejection is not None and rejection.code == top, rejection and rejection.to_dict()
    issue = next((i for i in rejection.issues if (i.code, i.path) == (code, path)), None)
    assert issue is not None, rejection.to_dict()
    if related is not None:
        assert list(issue.related_paths) == related
        assert len(rejection.issues) == 1 and issue.value == args["connection_type"]


def test_classification_row():
    assert CLASSIFICATION["SetConnectionType"] == "consequential"  # D059


def test_api_requires_a_preview_and_validates_the_response():
    api = make_api(MemoryStore())
    pid = api.create()
    command = api.command(pid, "SetConnectionType", {"junction_class": "post-beam", "connection_type": "STEEL_KNIFE_PLATE"})
    assert api.commit(pid, command).status_code == 428
    assert api.commit(pid, command).json()["error"]["code"] == "PREVIEW_REQUIRED"
    preview = api.preview(pid, command)  # validated against the committed OpenAPI by api_support
    assert preview.status_code == 200
    body = preview.json()
    assert len(body["connections"]["updated"]) == 68 and body["connections"]["added"] == body["connections"]["removed"] == []
    assert "PRELIMINARY_UNVERIFIED" in [w["code"] for w in body["warnings"]]
    committed = api.commit(pid, command, body["preview_token"])
    assert committed.status_code == 201, committed.text


# --- 9. the ECMAScript oracle -----------------------------------------------------------------


def test_connections_match_independent_ecmascript_implementation():
    """§9: bit-identical, except rafter-peak and purlin-rafter z values (tan), within 1e-12 m."""
    vector = next(v for v in json.loads(VECTORS_PATH.read_text(encoding="utf-8"))["inventories"] if v["rule"] == "vs02-frame-1")
    ours = RULE.generate_connections(_snapshot(FIXTURE))
    theirs = vector["connections"]
    assert len(ours) == len(theirs) == vector["connection_count"] == 312
    for a, b in zip(ours, theirs):
        assert (a.generation_key, a.junction_class, a.connection_type, list(a.member_keys)) == (
            b["generation_key"], b["junction_class"], b["connection_type"], b["member_keys"])
        if a.junction_class in ("rafter-peak", "purlin-rafter"):
            assert list(a.location_m[:2]) == b["location_m"][:2], a.generation_key
            assert abs(a.location_m[2] - b["location_m"][2]) <= 1e-12, a.generation_key
        else:
            assert list(a.location_m) == b["location_m"], a.generation_key


# --- 10. zero cases ---------------------------------------------------------------------------


def test_zero_cases_generate_no_connections_of_those_classes():
    doc = with_frame_parameters(purlins_per_slope=0, knee_braces_level_1=False, knee_braces_eave=False, joist_spacing_m=1.2192)
    grid = entities_of(doc, "TimberGrid")[0]
    width = entities_of(doc, "Footprint")[0]["width_m"]
    x = {line["id"]: line for line in grid["x_lines"]}
    # A 4'-0" bay with 48" spacing has no joists.
    grid["x_lines"] = [x["x0"], x["x1"], {"id": "x4", "fraction": x["x1"]["fraction"] + 4 * FT / width}, x["x2"], x["x3"]]
    doc = regenerate(doc)
    assert validate_value(doc).valid
    classes = Counter(c.junction_class for c in _check_junctions(doc))
    assert classes["purlin-rafter"] == 0 and classes["brace"] == 0
    assert not any("/x1-x4/j" in c.generation_key for c in RULE.generate_connections(_snapshot(doc)))
    assert set(_frame(doc)["connection_defaults"]) == set(JUNCTION_CLASSES)  # still required (MODEL-005 §5.2)


# --- 11. determinism and robustness -----------------------------------------------------------


@pytest.mark.parametrize("seed", [5, 17])
def test_connections_are_deterministic_and_order_independent(seed):
    def render(doc):
        return canonical_json([[c.generation_key, c.junction_class, c.connection_type, list(c.member_keys), list(c.location_m)]
                               for c in RULE.generate_connections(_snapshot(doc))])

    baseline = render(FIXTURE)
    assert render(FIXTURE) == baseline
    doc = fresh_fixture()
    random.Random(seed).shuffle(doc["entities"])
    assert render(doc) == baseline


_ARG = st.one_of(st.sampled_from(JUNCTION_CLASSES), st.sampled_from(CONNECTION_TYPES), st.text(max_size=12), st.integers(), st.none())


@settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(args=st.one_of(
    st.fixed_dictionaries({"junction_class": _ARG, "connection_type": _ARG}),
    st.dictionaries(st.sampled_from(["junction_class", "connection_type", "member_ids"]), _ARG),
    st.lists(_ARG, max_size=2),
    _ARG,
))
def test_random_set_connection_type_never_raises(args):
    result = run("SetConnectionType", args)
    if result.accepted:
        assert validate_value(result.change.candidate.model_dump(mode="json")).valid
        assert args["connection_type"] in (DEFAULTS[args["junction_class"]], ALTERNATIVES[args["junction_class"]])
    else:
        assert result.rejection.code in (VF, UC)


@settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(
    spacing=st.floats(0.25, 1.3),
    purlins=st.integers(-1, 5),
    leg=st.floats(0.4, 1.3),
    level_1=st.booleans(),
    eave=st.booleans(),
)
def test_random_frame_parameters_regenerate_valid_connections(spacing, purlins, leg, level_1, eave):
    result = run("SetFrameParameters", _parameters(joist_spacing_m=spacing, purlins_per_slope=purlins, knee_brace_leg_m=leg,
                                                   knee_braces_level_1=level_1, knee_braces_eave=eave))
    if not result.accepted:
        assert result.rejection.code in (VF, UC)
        return
    candidate = result.change.candidate.model_dump(mode="json")
    assert validate_value(candidate).valid
    assert Counter(c["junction_class"] for c in entities_of(candidate, "Connection")) == _expected_counts(candidate)


# --- 12. still preliminary (AC2-07) -----------------------------------------------------------


def test_connections_make_no_claims():
    fields = set(Connection.model_fields)
    assert fields == {"id", "kind", "schema_version", "junction_class", "connection_type", "member_ids", "location_m", "generation_key"}
    for word in ("capacity", "size", "fastener", "peg", "dowel", "plate_", "load", "adequa", "code"):
        assert not any(word in f for f in fields - {"id"}), word
    change = run("SetConnectionType", {"junction_class": "brace", "connection_type": "STEEL_KNIFE_PLATE"}).change
    preview = change.to_preview_dict()
    assert [w["code"] for w in preview["warnings"]] == ["PRELIMINARY_UNVERIFIED"]
    assert set(preview["connections"]) == {"added", "removed", "updated"}


def test_committed_connection_catalog_is_current():
    """D062, UI-003 §10: the browser's catalog is an export of model/connections.py, drift-checked."""
    from homedesign.model.connections import ALLOWED, CATALOG_VERSION, DESCRIPTIONS, FAMILIES
    from homedesign.model.schema_export import CONNECTION_CATALOG_PATH, render_connection_catalog

    assert CONNECTION_CATALOG_PATH.read_text(encoding="utf-8") == render_connection_catalog(), (
        "connection-catalog.json is stale. Run `uv run python -m homedesign.model.schema_export` and commit the result."
    )
    exported = json.loads(CONNECTION_CATALOG_PATH.read_text(encoding="utf-8"))
    assert exported["catalog_version"] == CATALOG_VERSION
    assert [c["junction_class"] for c in exported["junction_classes"]] == list(JUNCTION_CLASSES)
    for row in exported["junction_classes"]:
        assert {row["default"], row["alternative"]} == ALLOWED[row["junction_class"]]
        assert row["default"] == DEFAULTS[row["junction_class"]] and row["alternative"] == ALTERNATIVES[row["junction_class"]]
    assert [t["connection_type"] for t in exported["connection_types"]] == list(CONNECTION_TYPES)
    for t in exported["connection_types"]:
        assert t["family"] == FAMILIES[t["connection_type"]]
        assert t["description"] == DESCRIPTIONS[t["connection_type"]]
        assert "Representational only" in t["description"]
