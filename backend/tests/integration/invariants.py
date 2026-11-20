"""Whole-house invariants checked over HTTP after every step (TEST-001 §5).

`check_revision` reads one revision and its four artifacts through the API (every response is also
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

from homedesign.model import canonical_snapshot, validate_bytes
from homedesign.model.schema import Snapshot

EPS = 1e-6
ARTIFACTS = ("plan2d", "mesh3d", "timber_schedule", "preliminary_estimate")


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
    for kind in ("plan2d", "mesh3d", "timber_schedule"):
        assert view.envelopes[kind]["status"] == "CURRENT", (kind, view.envelopes[kind]["status"])
    assert view.envelopes["preliminary_estimate"]["status"] in ("CURRENT", "UNAVAILABLE")

    members = view.members()
    plan = view.envelopes["plan2d"]["payload"]
    mesh = view.envelopes["mesh3d"]["payload"]
    schedule = view.envelopes["timber_schedule"]["payload"]

    # One inventory: mesh and schedule list exactly the snapshot's members (AC-03, artifacts §10.3).
    # The plan lists the posts and beams only, until ART-002 (MODEL-005 §9, artifacts.md §5 interim note).
    plan_ids = [m["member_id"] for p in plan["planes"] for m in (*p["posts"], *p["beams"])]
    mesh_ids = [m["member_id"] for m in mesh["members"]]
    schedule_ids = [m["member_id"] for m in schedule["members"]]
    plan_members = [i for i, m in members.items() if m["member_role"] in ("POST", "BEAM")]
    for name, ids, expected in (("plan", plan_ids, plan_members), ("mesh", mesh_ids, members), ("schedule", schedule_ids, members)):
        assert sorted(ids) == sorted(expected), f"{name} member IDs differ from the snapshot inventory"
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

    # The estimate follows the schedule and never invents a total (artifacts §8.1, §10.4, §10.8).
    estimate_env = view.envelopes["preliminary_estimate"]
    estimate = estimate_env["payload"]
    by_key = {f"timber.{role}.{label}": a for (role, label), a in aggregates.items()}
    assert sorted(li["key"] for li in estimate["line_items"]) == sorted(by_key)
    for li in estimate["line_items"]:
        assert li["quantity_value"] == by_key[li["key"]]["total_length_m"]
        assert (li["amount_minor"] is None) == (li["unit_price_minor"] is None) == (not li["priced"])
    priced = [li for li in estimate["line_items"] if li["priced"]]
    coverage = "none" if not priced else "complete" if len(priced) == len(estimate["line_items"]) else "partial"
    assert estimate["coverage"] == coverage
    assert (estimate_env["status"] == "UNAVAILABLE") == (coverage == "none")
    if coverage == "complete":
        assert estimate["totals"]["grand_total_minor"] == sum(li["amount_minor"] for li in priced)
    else:
        assert estimate["totals"]["grand_total_minor"] is None  # never 0 for missing prices
        assert "COST_INPUTS_MISSING" in [w["code"] for w in estimate_env["warnings"]]
    return view


def check_transition(before: RevisionView, after: RevisionView, *, preserve_ids: bool = True) -> None:
    """Surviving generation keys keep their member IDs (building-model §9.4, D042). Not for undo (D044)."""
    if not preserve_ids:
        return
    old = {m["generation_key"]: m["id"] for m in before.entities("TimberMember")}
    new = {m["generation_key"]: m["id"] for m in after.entities("TimberMember")}
    changed = {k for k in old.keys() & new.keys() if old[k] != new[k]}
    assert not changed, f"member IDs changed for surviving keys: {sorted(changed)[:5]}"


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
