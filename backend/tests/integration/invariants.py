"""Whole-house invariants checked over HTTP after every step (TEST-001 §5).

`check_revision` reads one revision and its five artifacts through the API (every response is also
validated against the committed OpenAPI by `api_support.Api`) and asserts that the model, plan, mesh,
schedule, and estimate agree. `check_transition` compares consecutive revisions, and
`assert_unchanged` proves a rejected command left the project as it was.
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from homedesign.assemblies.schedule import build_assembly_schedule, select_assembly_schedule
from homedesign.dependencies import Outcome
from homedesign.estimating import build_estimate, select_estimate
from homedesign.geometry import build_mesh3d, build_plan2d, select_mesh3d, select_plan2d
from homedesign.model import canonical_json, canonical_snapshot, validate_bytes
from homedesign.model.schema import Snapshot
from homedesign.timber.schedule import build_schedule, select_schedule

EPS = 1e-6
ARTIFACTS = ("plan2d", "mesh3d", "timber_schedule", "assembly_schedule", "preliminary_estimate")
PLAN_ARRAYS = ("posts", "beams", "sills", "joists", "braces", "rafters", "purlins")


@dataclass
class RevisionView:
    revision_id: str
    snapshot: dict[str, Any]
    raw: bytes
    envelopes: dict[str, dict[str, Any]]

    def entities(self, kind: str) -> list[dict[str, Any]]:
        return [e for e in self.snapshot["entities"] if e["kind"] == kind]

    def one(self, kind: str) -> dict[str, Any]:
        (entity,) = self.entities(kind)
        return entity

    def members(self) -> dict[str, dict[str, Any]]:
        return {m["id"]: m for m in self.entities("TimberMember")}

    def connections(self) -> dict[str, dict[str, Any]]:
        return {c["id"]: c for c in self.entities("Connection")}


def read_revision(api, pid: str, rev: str) -> RevisionView:
    response = api.get(f"/api/v1/projects/{pid}/revisions/{rev}")
    assert response.status_code == 200, response.text
    envelopes = {}
    for kind in ARTIFACTS:
        r = api.get(f"/api/v1/projects/{pid}/artifacts/{kind}?revision_id={rev}")
        assert r.status_code == 200, (kind, r.status_code, r.text)
        envelopes[kind] = r.json()
    return RevisionView(rev, response.json(), response.content, envelopes)


def close(a: float, b: float, eps: float = EPS) -> bool:
    return abs(a - b) <= eps


def check_revision(api, pid: str, rev: str) -> RevisionView:
    view = read_revision(api, pid, rev)
    snap = view.snapshot

    # Snapshot: validates, and the served bytes are its canonical form (building-model §9.1, D029).
    assert validate_bytes(view.raw).valid, "served snapshot does not validate"
    assert canonical_snapshot(Snapshot.model_validate(json.loads(view.raw))) == view.raw
    assert snap["revision_id"] == rev

    # Envelopes: same revision, preliminary, no claims (AC-07, AC-08, artifacts §10.7).
    for kind, env in view.envelopes.items():
        assert env["source_revision_id"] == rev, kind
        assert env["suitability"] == "preliminary", kind
        assert not any(env["claims"].values()), (kind, env["claims"])
        assert "PRELIMINARY_UNVERIFIED" in [w["code"] for w in env["warnings"]], kind
    for kind in ("plan2d", "mesh3d", "timber_schedule", "assembly_schedule"):
        assert view.envelopes[kind]["status"] == "CURRENT", (kind, view.envelopes[kind]["status"])
    assert [w["code"] for w in view.envelopes["assembly_schedule"]["warnings"]][:2] == ["PRELIMINARY_UNVERIFIED", "CLIMATE_DETAILS_UNVERIFIED"]
    assert view.envelopes["preliminary_estimate"]["status"] in ("CURRENT", "UNAVAILABLE")

    members = view.members()
    plan = view.envelopes["plan2d"]["payload"]
    mesh = view.envelopes["mesh3d"]["payload"]
    schedule = view.envelopes["timber_schedule"]["payload"]

    # One inventory: plan, mesh, and schedule list exactly the snapshot's members (AC-03, AC2-02, artifacts §10.3).
    plan_ids = [m["member_id"] for p in plan["planes"] for array in PLAN_ARRAYS for m in p[array]]
    mesh_ids = [m["member_id"] for m in mesh["members"]]
    schedule_ids = [m["member_id"] for m in schedule["members"]]
    for name, ids in (("plan", plan_ids), ("mesh", mesh_ids), ("schedule", schedule_ids)):
        assert sorted(ids) == sorted(members), f"{name} member IDs differ from the snapshot inventory"
    assert len(set(schedule_ids)) == len(schedule_ids)

    # Dimensions agree with the semantic records (AC-01, artifacts §10.2).
    footprint = view.one("Footprint")
    dims = {d["id"]: d["value_m"] for d in plan["dimensions"]}
    assert close(dims["footprint-width"], footprint["width_m"]) and close(dims["footprint-depth"], footprint["depth_m"])
    xs = [p[0] for p in mesh["envelope"]["footprint_ring_m"]]
    ys = [p[1] for p in mesh["envelope"]["footprint_ring_m"]]
    assert close(max(xs) - min(xs), footprint["width_m"]) and close(max(ys) - min(ys), footprint["depth_m"])
    levels = sorted(view.entities("Level"), key=lambda lv: lv["index"])
    assert [round(z, 9) for z in mesh["envelope"]["level_z_m"]] == [round(lv["elevation_m"], 9) for lv in levels]
    assert close(mesh["envelope"]["z_eave_m"], levels[-1]["elevation_m"] + levels[-1]["story_height_m"])
    roof = view.one("GableRoof")
    assert close(mesh["envelope"]["roof"]["pitch_rad"], roof["pitch_rad"], 1e-12)

    # The schedule reconciles with the inventory (AC-04).
    sections = {s["id"]: s["nominal_label"] for s in view.entities("Section")}
    totals: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in schedule["members"]:
        member = members[row["member_id"]]
        d = [e - s for s, e in zip(member["start_m"], member["end_m"], strict=True)]
        assert close(row["length_m"], math.sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2]))
        assert row["quantity"] == 1 and row["role"] == member["member_role"]
        assert row["nominal_section"] == sections[member["section_id"]]
        totals[(row["role"], row["nominal_section"])].append(row["length_m"])
    aggregates = {(a["role"], a["nominal_section"]): a for a in schedule["aggregates"]}
    assert set(aggregates) == set(totals)
    for key, lengths in totals.items():
        assert aggregates[key]["count"] == len(lengths)
        assert close(aggregates[key]["total_length_m"], sum(lengths), EPS * len(lengths))
    assert sum(a["count"] for a in schedule["aggregates"]) == len(members)

    # Connections reconcile with the frame (CONN-001 §6) and lie on both members' axes (§4.2, D058).
    check_connections(view)

    # Plan, mesh, and schedule carry exactly the snapshot's connections, and the counts reconcile (ART-002 §11).
    check_artifact_connections(view, plan, mesh, schedule)

    # Walls, openings, and wall framing reconcile across the views, the assembly schedule, and the model (ART-003 §11).
    assemblies = view.envelopes["assembly_schedule"]["payload"]
    check_walls(view, plan, mesh, assemblies)

    # The estimate follows the schedules and never invents a total (artifacts §8.1, §10.4, §10.8; ART-002 §7; ART-003 §7).
    estimate_env = view.envelopes["preliminary_estimate"]
    estimate = estimate_env["payload"]
    by_key = {f"timber.{role}.{label}": a for (role, label), a in aggregates.items()}
    per_type: Counter = Counter()
    for a in schedule["connection_aggregates"]:
        per_type[a["connection_type"]] += a["count"]
    expected_lines = {**{k: a["total_length_m"] for k, a in by_key.items()}, **{f"connection.{t}": n for t, n in per_type.items()},
                      **{f"assembly.{a['assembly_label']}.{a['layer']}": a["area_m2"] for a in assemblies["layer_aggregates"]},
                      **{f"wallframing.{a['piece_kind']}.{a['nominal_section']}": a["total_length_m"] for a in assemblies["framing_aggregates"]}}
    counts = {f"wallframing.{a['piece_kind']}.{a['nominal_section']}": a["count"] for a in assemblies["framing_aggregates"]}
    assert {li["key"]: li["count"] for li in estimate["line_items"] if li["kind"] == "wallframing"} == counts
    assert {li["key"]: li["quantity_value"] for li in estimate["line_items"]} == expected_lines
    keys = [li["key"] for li in estimate["line_items"]]
    assert keys == sorted(keys, key=lambda k: k.encode("utf-16-be")) and len(set(keys)) == len(keys)
    for li in estimate["line_items"]:
        assert li["quantity_unit"] == {"connection": "each", "assembly": "m2"}.get(li["kind"], "m")
        assert (li["amount_minor"] is None) == (li["unit_price_minor"] is None) == (not li["priced"])
    assert estimate["assumptions"] == schedule["assumptions"] + assemblies["assumptions"]
    priced = [li for li in estimate["line_items"] if li["priced"]]
    coverage = "none" if not priced else "complete" if len(priced) == len(estimate["line_items"]) else "partial"
    assert estimate["coverage"] == coverage
    assert (estimate_env["status"] == "UNAVAILABLE") == (coverage == "none")
    if coverage == "complete":
        assert estimate["totals"]["grand_total_minor"] == sum(li["amount_minor"] for li in priced)
    else:
        assert estimate["totals"]["grand_total_minor"] is None  # never 0 for missing prices
        assert "COST_INPUTS_MISSING" in [w["code"] for w in estimate_env["warnings"]]

    check_fresh_build(api, pid, view)
    return view


def check_fresh_build(api, pid: str, view: RevisionView) -> None:
    """D056 item 5, DEP-001 §10: every served payload, reused or derived, equals a fresh build, byte for byte.

    The plan, mesh, and schedule are built from the revision's snapshot; the estimate from that schedule
    and the project's current price book.
    """
    snapshot = Snapshot.model_validate(view.snapshot)
    schedule = build_schedule(select_schedule(snapshot))
    assemblies = build_assembly_schedule(select_assembly_schedule(snapshot))
    with api.service.store.transaction() as tx:
        book = tx.get_price_book(pid)
    selection = select_estimate({"timber_schedule": Outcome("CURRENT", schedule), "assembly_schedule": Outcome("CURRENT", assemblies)})
    status, estimate, warnings = build_estimate(selection["timber_schedule"], selection["assembly_schedule"], book)
    fresh = {
        "plan2d": build_plan2d(select_plan2d(snapshot)),
        "mesh3d": build_mesh3d(select_mesh3d(snapshot)),
        "timber_schedule": schedule,
        "assembly_schedule": assemblies,
        "preliminary_estimate": estimate,
    }
    for kind, payload in fresh.items():
        assert canonical_json(view.envelopes[kind]["payload"]) == canonical_json(payload), f"{kind} differs from a fresh build"
    estimate_env = view.envelopes["preliminary_estimate"]
    assert estimate_env["status"] == status
    assert estimate_env["warnings"][1:] == list(warnings)  # after PRELIMINARY_UNVERIFIED


def check_walls(view: RevisionView, plan, mesh, assemblies) -> None:
    """ART-003 §11 and §13 tests 1-3: the views' and the schedule's walls, openings, and pieces are the snapshot's,
    by ID and on their level's plane; areas and aggregates reconcile with the rows."""
    walls = {w["id"]: w for w in view.entities("Wall")}
    openings = {o["id"]: o for o in view.entities("Opening")}
    pieces = {p["id"]: p for p in view.entities("WallFramingPiece")}
    plane_of_level = {lv["id"]: "level-0" if lv["index"] == 0 else "level-1" for lv in view.entities("Level")}
    plan_walls = {w["wall_id"]: (p["plane_id"], w) for p in plan["planes"] for w in p["walls"]}
    plan_pieces = {f["piece_id"]: p["plane_id"] for p in plan["planes"] for f in p["wall_framing"]}
    assert set(plan_walls) == {w["wall_id"] for w in mesh["walls"]} == {w["wall_id"] for w in assemblies["walls"]} == set(walls)
    assert set(plan_pieces) == {f["piece_id"] for f in mesh["wall_framing"]} == {r["piece_id"] for r in assemblies["wall_framing"]} == set(pieces)
    assert len(plan_pieces) == sum(len(p["wall_framing"]) for p in plan["planes"])
    plan_openings = {o["opening_id"] for _, w in plan_walls.values() for o in w["openings"]}
    assert plan_openings == {v["opening_id"] for w in mesh["walls"] for v in w["voids"]} == {o["opening_id"] for o in assemblies["openings"]} == set(openings)
    owner = {pid: w for w in walls.values() for pid in w["framing_ids"]}
    for wid, (plane, w) in plan_walls.items():
        assert plane == plane_of_level[walls[wid]["level_id"]] and w["generation_key"] == walls[wid]["generation_key"]
        assert {o["opening_id"] for o in w["openings"]} == {o["id"] for o in openings.values() if o["wall_id"] == wid}
    for pid, plane in plan_pieces.items():
        assert plane == plane_of_level[owner[pid]["level_id"]]
    for f in mesh["wall_framing"]:
        assert f["wall_id"] == owner[f["piece_id"]]["id"]
        assert (f["axis_start_m"], f["axis_end_m"]) == (pieces[f["piece_id"]]["start_m"], pieces[f["piece_id"]]["end_m"])
    # Areas and aggregates reconcile with the rows (AC2b-05).
    rows = assemblies["walls"]
    for w in rows:
        record = walls[w["wall_id"]]
        d = [e - s for s, e in zip(record["start_m"], record["end_m"], strict=True)]
        assert close(w["length_m"], math.sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2])) and w["height_m"] == record["height_m"]
        own = [o for o in openings.values() if o["wall_id"] == w["wall_id"]]
        assert close(w["opening_area_m2"], sum(o["width_m"] * o["height_m"] for o in own))
        assert close(w["net_area_m2"], w["gross_area_m2"] - w["opening_area_m2"]) and w["net_area_m2"] > 0
        assert 0 <= w["framing_fraction"] < 1
    totals = assemblies["totals"]
    assert (totals["wall_count"], totals["opening_count"]) == (len(walls), len(openings))
    n = len(rows)
    for name in ("gross_area_m2", "opening_area_m2", "net_area_m2", "framing_face_area_m2"):
        assert close(totals[name], sum(w[name] for w in rows), EPS * n)
    net = sum(w["net_area_m2"] for w in rows)
    fill = sum(w["net_area_m2"] - w["framing_face_area_m2"] for w in rows)
    for layer in assemblies["layer_aggregates"]:
        assert close(layer["area_m2"], fill if layer["function"] == "FRAMING" else net, EPS * n)
        assert layer["volume_m3"] == layer["area_m2"] * layer["thickness_m"]
    lengths: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in assemblies["wall_framing"]:
        lengths[(r["piece_kind"], r["nominal_section"])].append(r["length_m"])
    assert {(a["piece_kind"], a["nominal_section"]) for a in assemblies["framing_aggregates"]} == set(lengths)
    for a in assemblies["framing_aggregates"]:
        group = lengths[(a["piece_kind"], a["nominal_section"])]
        assert a["count"] == len(group) and close(a["total_length_m"], sum(group), EPS * len(group))
    jacked = {r["opening_id"] for r in assemblies["wall_framing"] if r["piece_kind"] == "JACK"}
    assert all(o["has_jacks"] == (o["opening_id"] in jacked) for o in assemblies["openings"])


def outcome_key(envelope: dict[str, Any]) -> bytes:
    """What AC2-04 compares: the artifact's status, payload, and error, canonically (DEP-001 §10)."""
    return canonical_json({"status": envelope["status"], "payload": envelope["payload"], "error": envelope["error"]})


def check_impact(before: RevisionView, after: RevisionView, impacted: list[str]) -> None:
    """AC2-04: `impacted_artifacts` lists an artifact if and only if its outcome changes, and only listed
    artifacts change fingerprint; the others are reused with the base's fingerprint (D056 item 3)."""
    changed = sorted(kind for kind in ARTIFACTS if outcome_key(before.envelopes[kind]) != outcome_key(after.envelopes[kind]))
    assert sorted(impacted) == changed, f"impacted {sorted(impacted)} but outcomes changed for {changed}"
    assert impacted == sorted(impacted) and len(set(impacted)) == len(impacted)
    for kind in ARTIFACTS:
        same = before.envelopes[kind]["input_fingerprint"] == after.envelopes[kind]["input_fingerprint"]
        assert same == (kind not in impacted), f"{kind}: fingerprint {'unchanged' if same else 'changed'}, impacted={kind in impacted}"


# Receiving and entering roles per junction class (D054, CONN-001 §4.2).
JUNCTION_ROLES = {
    "post-beam": ("POST", "BEAM"),
    "post-sill": ("SILL", "POST"),
    "brace": (("POST", "BEAM"), "KNEE_BRACE"),
    "joist-beam": ("BEAM", "FLOOR_JOIST"),
    "rafter-peak": ("PRINCIPAL_RAFTER", "PRINCIPAL_RAFTER"),
    "rafter-foot": ("BEAM", "PRINCIPAL_RAFTER"),
    "purlin-rafter": ("PRINCIPAL_RAFTER", "PURLIN"),
}


def _on_axis(point, start, end, eps: float = 1e-9) -> bool:
    ab = [e - s for s, e in zip(start, end, strict=True)]
    ap = [p - s for s, p in zip(start, point, strict=True)]
    t = sum(a * b for a, b in zip(ap, ab, strict=True)) / sum(c * c for c in ab)
    closest = [s + t * c for s, c in zip(start, ab, strict=True)]
    return -eps <= t <= 1 + eps and math.dist(point, closest) <= eps


def check_connections(view: RevisionView) -> None:
    members = view.members()
    connections = list(view.connections().values())
    roles = Counter(m["member_role"] for m in members.values())
    grid = view.one("TimberGrid")
    nx, ny = len(grid["x_lines"]), len(grid["y_lines"])
    expected = Counter({
        "post-beam": 2 * roles["BEAM"],
        "post-sill": nx * ny,
        "brace": 2 * roles["KNEE_BRACE"],
        "joist-beam": 2 * roles["FLOOR_JOIST"],
        "rafter-peak": nx,
        "rafter-foot": 2 * nx,
        "purlin-rafter": 2 * roles["PURLIN"],
    })
    assert Counter(c["junction_class"] for c in connections) == +expected, "connection counts differ from CONN-001 §6"
    defaults = view.one("FrameSystem")["connection_defaults"]
    for c in connections:
        receiving, entering = (members[i] for i in c["member_ids"])
        want_receiving, want_entering = JUNCTION_ROLES[c["junction_class"]]
        assert receiving["member_role"] in (want_receiving if isinstance(want_receiving, tuple) else (want_receiving,)), c["generation_key"]
        assert entering["member_role"] == want_entering, c["generation_key"]
        assert c["location_m"] in (entering["start_m"], entering["end_m"]), c["generation_key"]  # copied, bit for bit
        assert _on_axis(c["location_m"], receiving["start_m"], receiving["end_m"]), c["generation_key"]
        assert c["connection_type"] == defaults[c["junction_class"]]
        assert c["generation_key"] == f"connection/{c['junction_class']}/{receiving['generation_key']}/{entering['generation_key']}"


def check_artifact_connections(view: RevisionView, plan, mesh, schedule) -> None:
    records = view.connections()
    members = view.members()
    plan_markers = {c["connection_id"]: (p["plane_id"], c) for p in plan["planes"] for c in p["connections"]}
    plane_of = {m["member_id"]: p["plane_id"] for p in plan["planes"] for array in PLAN_ARRAYS for m in p[array]}
    mesh_markers = {c["connection_id"]: c for c in mesh["connections"]}
    rows = {c["connection_id"]: c for c in schedule["connections"]}
    for name, ids in (("plan", plan_markers), ("mesh", mesh_markers), ("schedule", rows)):
        assert set(ids) == set(records), f"{name} connections differ from the snapshot's"
    assert len(plan_markers) == sum(len(p["connections"]) for p in plan["planes"]) and len(rows) == len(schedule["connections"])
    for cid, record in records.items():
        fields = (record["generation_key"], record["junction_class"], record["connection_type"])
        plane, marker = plan_markers[cid]
        for item in (marker, mesh_markers[cid], rows[cid]):
            assert (item["generation_key"], item["junction_class"], item["connection_type"]) == fields, record["generation_key"]
        assert plane == plane_of[record["member_ids"][1]] and marker["xy_m"] == record["location_m"][:2]
        assert mesh_markers[cid]["location_m"] == record["location_m"]
        assert rows[cid]["member_ids"] == record["member_ids"] and all(m in members for m in record["member_ids"])
    counts = Counter((r["junction_class"], r["connection_type"]) for r in schedule["connections"])
    assert {(a["junction_class"], a["connection_type"]): a["count"] for a in schedule["connection_aggregates"]} == counts
    assert sum(a["count"] for a in schedule["connection_aggregates"]) == len(records)
    assert [t["connection_type"] for t in schedule["connection_catalog"]["types"]] == sorted({t for _, t in counts})


def check_transition(before: RevisionView, after: RevisionView, *, preserve_ids: bool = True) -> None:
    """Surviving generation keys keep their member and connection IDs (building-model §9.4, D042;
    CONN-001 §5.2), and a surviving connection keeps its members. Not for undo (D044)."""
    if not preserve_ids:
        return
    for kind in ("TimberMember", "Connection"):
        old = {m["generation_key"]: m["id"] for m in before.entities(kind)}
        new = {m["generation_key"]: m["id"] for m in after.entities(kind)}
        changed = {k for k in old.keys() & new.keys() if old[k] != new[k]}
        assert not changed, f"{kind} IDs changed for surviving keys: {sorted(changed)[:5]}"
    old_members = {c["generation_key"]: c["member_ids"] for c in before.entities("Connection")}
    for c in after.entities("Connection"):
        assert old_members.get(c["generation_key"], c["member_ids"]) == c["member_ids"], c["generation_key"]


@dataclass(frozen=True)
class ProjectState:
    head: str
    sequence: int
    snapshot: bytes
    manifest: dict[str, Any]
    revisions: int


def project_state(api, pid: str) -> ProjectState:
    project = api.get(f"/api/v1/projects/{pid}").json()
    snapshot = api.get(f"/api/v1/projects/{pid}/revisions/{project['head_revision_id']}").content
    manifest = api.get(f"/api/v1/projects/{pid}/artifacts").json()
    revisions = len(api.get(f"/api/v1/projects/{pid}/revisions").json()["revisions"])
    return ProjectState(project["head_revision_id"], project["head_sequence"], snapshot, manifest, revisions)


def assert_unchanged(before: ProjectState, after: ProjectState) -> None:
    """A rejected command leaves head, model, and artifact statuses unchanged (AC-06, building-model §9.7)."""
    assert after == before


def counts_by_role(view: RevisionView) -> Counter:
    return Counter(m["member_role"] for m in view.entities("TimberMember"))
