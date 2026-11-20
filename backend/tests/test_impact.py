"""DEP-001 §8 and §14: exact `impacted_artifacts` and reuse on Reference House 001 v2, with the real derivations.

Each case commits one command from the created house (with a complete price book), and checks that:
- the preview lists exactly the expected artifacts (the §8 table, measured while drafting);
- exactly those artifacts' stored payloads change (AC2-04);
- every other artifact is reused: the new revision's row has the base's payload, fingerprint, and
  `generated_at`, and its envelope names the new revision as head (D056 item 3).
"""

from __future__ import annotations

import math

import pytest

from api_support import FULL_PRICES, book
from homedesign.model.canonical import fingerprint
from homedesign.project import MemoryStore, ProjectService
from test_project import ACTOR, KEY, T0, at, create, envelope, head

FT = 0.3048
ALL = ["mesh3d", "plan2d", "preliminary_estimate", "timber_schedule"]
TYPES = ("plan2d", "mesh3d", "timber_schedule", "preliminary_estimate")


def house(store):
    svc = ProjectService(store, token_key=KEY)
    created = create(svc)
    svc.set_price_book(created.project_id, book(**FULL_PRICES), actor_id=ACTOR, now=T0)
    for kind in TYPES:  # the estimate is re-derived under the book, at T0
        svc.artifacts.get_artifact(created.project_id, kind, now=T0)
    return svc, created.project_id


def entity(svc, pid, kind):
    return next(e for e in head(svc, pid).entities if e.kind == kind)


def envelopes(svc, pid, rev, now):
    return {kind: svc.artifacts.get_artifact(pid, kind, rev, now=now) for kind in TYPES}


def commit(svc, pid, type_, args, now):
    command = envelope(svc, pid, type_, args)
    preview = svc.preview(pid, command, actor_id=ACTOR, now=now)
    result = svc.commit(pid, command, preview.preview_token, actor_id=ACTOR, now=now)
    return preview, result


def grid_args(svc, pid, axis, k, line):
    grid = entity(svc, pid, "TimberGrid").model_dump(mode="json")
    lines = grid[f"{axis}_lines"]
    lines[k] = line(lines[k])
    other = "y" if axis == "x" else "x"
    return {f"{axis}_lines": lines, f"{other}_lines": grid[f"{other}_lines"]}


def frame(svc, pid, **changes):
    return {**entity(svc, pid, "FrameSystem").parameters.model_dump(mode="json"), **changes}


def add_section(svc, pid, label, width, depth, now):
    commit(svc, pid, "AddSection", {"nominal_label": label, "actual_width_m": width, "actual_depth_m": depth}, now)
    return next(e.id for e in head(svc, pid).entities if e.kind == "Section" and e.nominal_label == label)


def pitch(p):
    return lambda svc, pid: ("SetGableRoofParameters", {"pitch_rad": p, "eave_overhang_m": entity(svc, pid, "GableRoof").eave_overhang_m})


def overhang(o):
    return lambda svc, pid: ("SetGableRoofParameters", {"pitch_rad": entity(svc, pid, "GableRoof").pitch_rad, "eave_overhang_m": o})


def move(axis, k, fraction):
    return lambda svc, pid: ("SetTimberGrid", grid_args(svc, pid, axis, k, lambda line: {**line, "fraction": fraction}))


def reidentify(axis, k):
    return lambda svc, pid: ("SetTimberGrid", grid_args(svc, pid, axis, k, lambda line: {"fraction": line["fraction"]}))


def width(w=None, d=None):
    def make(svc, pid):
        fp = entity(svc, pid, "Footprint")
        return "SetFootprintDimensions", {"width_m": w or fp.width_m, "depth_m": d or fp.depth_m}
    return make


def stories(h0=None, h1=None):
    def make(svc, pid):
        levels = sorted((e for e in head(svc, pid).entities if e.kind == "Level"), key=lambda lv: lv.index)
        return "SetStoryHeights", {"story_heights_m": [h0 or levels[0].story_height_m, h1 or levels[1].story_height_m]}
    return make


def member_section(label, width_m=None, depth_m=None):
    """SetMemberSection BEAM -> a section added first; with no dimensions, the beam section's own."""
    def make(svc, pid):
        beam = next(e for e in head(svc, pid).entities if e.kind == "Section" and e.nominal_label == "8x12")
        section_id = add_section(svc, pid, label, width_m or beam.actual_width_m, depth_m or beam.actual_depth_m, at(0.5))
        return "SetMemberSection", {"role": "BEAM", "section_id": section_id}
    return make


def connection(junction_class, connection_type):
    return lambda svc, pid: ("SetConnectionType", {"junction_class": junction_class, "connection_type": connection_type})


def frame_args(**changes):
    return lambda svc, pid: ("SetFrameParameters", frame(svc, pid, **changes))


# DEP-001 §8, row by row. Expected lists are sorted, as the preview returns them.
CASES = [
    ("width 40'", width(w=40 * FT), ALL),
    ("depth 26'", width(d=26 * FT), ALL),
    ("story 0 only", stories(h0=11 * FT), ALL),
    ("story 1 only", stories(h1=10 * FT), ALL),
    *((f"pitch only {p:.4f}", pitch(p), ["mesh3d", "preliminary_estimate", "timber_schedule"])
      for p in (math.atan(10 / 12), math.atan(6 / 12), math.atan(12 / 12), 0.5)),
    ("overhang only 1'", overhang(1 * FT), ["mesh3d", "plan2d"]),
    ("overhang only 0", overhang(0.0), ["mesh3d", "plan2d"]),
    *((f"move y1 to {f}", move("y", 1, f), ALL) for f in (0.4, 0.45, 0.55, 0.6, 0.3)),
    *((f"move x1 to {f}", move("x", 1, f), ALL) for f in (0.3, 0.32, 0.35)),
    ("re-identify y1", reidentify("y", 1), ["mesh3d", "plan2d", "timber_schedule"]),
    ("re-identify x1", reidentify("x", 1), ALL),  # the purlin total moves in its last bit (C6)
    *((f"joist spacing {s}", frame_args(joist_spacing_m=s), ["mesh3d", "plan2d"]) for s in (0.62, 0.65, 0.70)),
    ("joist spacing 0.5", frame_args(joist_spacing_m=0.5), ALL),
    ("brace leg 2'-6\"", frame_args(knee_brace_leg_m=2.5 * FT), ALL),
    ("3 purlins", frame_args(purlins_per_slope=3), ALL),
    ("eave braces off", frame_args(knee_braces_eave=False), ALL),
    ("add section", lambda svc, pid: ("AddSection", {"nominal_label": "10x12", "actual_width_m": 0.2413, "actual_depth_m": 0.2921}), []),
    ("beam to a new 10x12", member_section("10x12", 0.2413, 0.2921), ["mesh3d", "preliminary_estimate", "timber_schedule"]),
    ("beam to 8x12's dimensions, another label", member_section("8x12b"), ["preliminary_estimate", "timber_schedule"]),
    ("joist-beam to JOIST_HANGER", connection("joist-beam", "JOIST_HANGER"), ALL),
    ("post-beam to STEEL_KNIFE_PLATE", connection("post-beam", "STEEL_KNIFE_PLATE"), ALL),
]


@pytest.mark.parametrize("name, make, expected", CASES, ids=[c[0] for c in CASES])
def test_measured_impact(name, make, expected):
    # The in-memory store only: the table is about derivations; the PostgreSQL lookup and copy are
    # covered by the other tests here, which run on both stores.
    svc, pid = house(MemoryStore())
    type_, args = make(svc, pid)
    base = svc.get_project(pid)["head_revision_id"]
    before = envelopes(svc, pid, base, at(0.9))
    preview, result = commit(svc, pid, type_, args, at(1))
    assert preview.impacted_artifacts == expected == preview.body["impacted_artifacts"]
    assert result.http_status == 201 and result.body()["artifact_statuses"] == {k: "CURRENT" for k in TYPES}
    after = envelopes(svc, pid, result.revision_id, at(2))
    for kind in TYPES:
        old, new = before[kind], after[kind]
        assert (new["source_revision_id"], new["head"]) == (result.revision_id, True)
        assert (fingerprint(old["payload"]) != fingerprint(new["payload"])) == (kind in expected), kind
        if kind in expected:
            assert new["input_fingerprint"] != old["input_fingerprint"] and new["generated_at"] == "2026-11-19T12:01:00.000000Z", kind
        else:  # reused: the base's row, copied
            assert (new["input_fingerprint"], new["generated_at"], new["payload"]) == (old["input_fingerprint"], old["generated_at"], old["payload"]), kind


def test_undo_reuses_every_payload_of_its_target(store):
    svc, pid = house(store)
    target = svc.get_project(pid)["head_revision_id"]
    original = envelopes(svc, pid, target, at(0.5))
    commit(svc, pid, *width(w=40 * FT)(svc, pid), at(1))
    preview, result = commit(svc, pid, "UndoToRevision", {"target_revision_id": target}, at(2))
    assert preview.impacted_artifacts == ALL  # versus its base, the width change
    for kind, envelope_ in envelopes(svc, pid, result.revision_id, at(3)).items():
        assert envelope_["source_revision_id"] == result.revision_id
        assert (envelope_["input_fingerprint"], envelope_["generated_at"], envelope_["payload"]) == (
            original[kind]["input_fingerprint"], original[kind]["generated_at"], original[kind]["payload"]), kind


def test_noop_impacts_nothing(store):
    svc, pid = house(store)
    preview = svc.preview(pid, envelope(svc, pid, *width()(svc, pid)), actor_id=ACTOR, now=at(1))
    assert preview.change.is_noop and preview.impacted_artifacts == []


def test_connection_type_for_a_class_without_connections_impacts_nothing_but_needs_confirmation(store):
    svc, pid = house(store)
    commit(svc, pid, *frame_args(knee_braces_level_1=False, knee_braces_eave=False)(svc, pid), at(1))
    preview = svc.preview(pid, envelope(svc, pid, *connection("brace", "STEEL_KNIFE_PLATE")(svc, pid)), actor_id=ACTOR, now=at(2))
    assert preview.impacted_artifacts == [] and not preview.change.is_noop
    assert preview.change.confirmation_required  # vs02-change-classes-1 is unchanged (DEP-001 §3)


def test_price_book_change_makes_only_the_head_estimate_stale(store):
    svc, pid = house(store)
    rev = svc.get_project(pid)["head_revision_id"]
    svc.set_price_book(pid, book(**{**FULL_PRICES, "timber.POST.8x8": 3200}), actor_id=ACTOR, now=at(1))
    assert svc.artifacts.statuses(pid, rev) == {"plan2d": "CURRENT", "mesh3d": "CURRENT", "timber_schedule": "CURRENT", "preliminary_estimate": "STALE"}
    assert svc.artifacts.get_artifact(pid, "preliminary_estimate", now=at(2))["payload"]["price_book"]["price_book_version"] == 2


def test_two_revisions_with_equal_selections_have_equal_fingerprints(store):
    """§14 item 9: and no fingerprint depends on the revision (AddSection changes nothing any derivation reads)."""
    svc, pid = house(store)
    base = svc.get_project(pid)["head_revision_id"]
    _, result = commit(svc, pid, "AddSection", {"nominal_label": "x", "actual_width_m": 0.1, "actual_depth_m": 0.1}, at(1))
    assert result.revision_id != base
    assert [e["input_fingerprint"] for e in svc.artifacts.manifest(pid, base)["artifacts"]] == [
        e["input_fingerprint"] for e in svc.artifacts.manifest(pid, result.revision_id)["artifacts"]]


def test_reuse_lookup_never_crosses_projects(store):
    """§7.2: a row with the very fingerprint another project needs is never returned to it.

    An estimate without a price book selects only the schedule's aggregates, which carry no IDs, so two
    created houses share that fingerprint, and the second project must still derive its own row.
    """
    svc, a = house(store)  # its first estimate row, without a book, was stored at T0
    created_b = svc.create_project({"command_id": "00000000-0000-4000-8000-00000000000b", "type": "CreateReferenceProject", "args": {}},
                                   actor_id=ACTOR, now=at(5))
    b = created_b.project_id
    estimate_b = svc.artifacts.get_artifact(b, "preliminary_estimate", now=at(6))
    with store.transaction() as tx:
        rows_a = tx.get_artifacts(svc.get_project(a)["head_revision_id"], "preliminary_estimate")
    assert estimate_b["input_fingerprint"] in {r.input_fingerprint for r in rows_a}  # the shared fingerprint
    assert (estimate_b["status"], estimate_b["generated_at"]) == ("UNAVAILABLE", "2026-11-19T12:05:00.000000Z")  # derived, not copied
    with store.transaction() as tx:
        for kind in TYPES:
            for row in tx.get_artifacts(svc.get_project(a)["head_revision_id"], kind):
                hit = tx.find_reusable_artifact(b, kind, row.input_fingerprint, row.generator_version)
                assert hit is None or hit.project_id == b, kind
                assert tx.find_reusable_artifact(a, kind, row.input_fingerprint, "other") is None
