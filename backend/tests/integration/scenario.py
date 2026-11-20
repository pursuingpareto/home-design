"""The Reference House 001 scenario (TEST-001 §5) and its golden record (§6).

One project goes through every D043 command over HTTP, including rejections, a retry, a conflict,
undo, and a replay of the operation log. `check_revision` runs after every step. Everything is
deterministic (fixed project ID, actor, clock, command IDs, and UUIDv4 sequence), so the run produces
the same golden record on every machine and on both stores.
"""

from __future__ import annotations

import json
import math
import uuid
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from typing import Any, Iterator
from unittest.mock import patch

from homedesign.model.canonical import fingerprint, snapshot_fingerprint
from homedesign.project import MemoryStore, ProjectService

from integration.invariants import RevisionView, assert_unchanged, check_revision, check_transition, project_state

REPO_ROOT = Path(__file__).resolve().parents[3]
GOLDEN_PATH = REPO_ROOT / "tests" / "vectors" / "scenarios" / "reference-house-001.json"
PROJECT_ID = "5c3a9e1f-7b2d-4c8e-9f01-2a3b4c5d6e7f"
_NS = uuid.UUID("0d5c6a2e-91b4-4f3a-8e27-6b1f0c9d4a83")
FT = 0.3048
BOOK = {
    "currency": "USD", "as_of": "2026-11-01", "source": "Scenario supplier quote", "geography": "Chittenden County, VT",
    # One row per timber line of Reference House 001 v2 (D053), so the estimate is complete.
    "rows": [
        {"key": key, "unit": "m", "unit_price_minor": price}
        for key, price in (
            ("timber.BEAM.8x12", 4725), ("timber.FLOOR_JOIST.4x8", 1200), ("timber.KNEE_BRACE.4x6", 900), ("timber.POST.8x8", 3150),
            ("timber.PRINCIPAL_RAFTER.8x10", 3900), ("timber.PURLIN.6x8", 2350), ("timber.SILL.8x8", 3150),
        )
    ],
}


@contextmanager
def deterministic_uuid4() -> Iterator[None]:
    """Server-generated random UUIDs (request IDs, the price-book ID) come from a fixed sequence."""
    counter = iter(range(1, 1_000_000))
    with patch("uuid.uuid4", side_effect=lambda: uuid.UUID(int=next(counter), version=4)):
        yield


class Scenario:
    def __init__(self, api) -> None:
        self.api = api
        self.pid = PROJECT_ID
        self.steps: list[dict[str, Any]] = []
        self.views: dict[str, RevisionView] = {}
        self.commands: dict[str, dict[str, Any]] = {}  # committed commands by step name, for an exact retry
        self.head_view: RevisionView | None = None

    # --- plumbing -------------------------------------------------------------------------------

    def tick(self) -> None:
        self.api.clock.now += timedelta(minutes=1)

    def command(self, name: str, type_: str, args: dict[str, Any], base: str | None = None) -> dict[str, Any]:
        return {
            "command_id": str(uuid.uuid5(_NS, name)),
            "project_id": self.pid,
            "base_revision_id": base or self.head_view.revision_id,  # type: ignore[union-attr]
            "type": type_,
            "args": args,
        }

    def record(self, name: str, response) -> None:
        body = response.json()
        self.steps.append({"step": name, "status": response.status_code, "code": body.get("error", {}).get("code"), "replayed": body.get("replayed", False)})

    def accepted(self, name: str, response, *, preserve_ids: bool = True) -> RevisionView:
        assert response.status_code == 201, (name, response.status_code, response.text)
        self.record(name, response)
        view = check_revision(self.api, self.pid, response.json()["revision_id"])
        if self.head_view is not None:
            check_transition(self.head_view, view, preserve_ids=preserve_ids)
        self.views[view.revision_id] = self.head_view = view
        return view

    def consequential(self, name: str, type_: str, args: dict[str, Any], **kw) -> RevisionView:
        self.tick()
        command = self.commands[name] = self.command(name, type_, args)
        preview = self.api.preview(self.pid, command)
        assert preview.status_code == 200 and preview.json()["confirmation_required"], (name, preview.text)
        return self.accepted(name, self.api.commit(self.pid, command, preview.json()["preview_token"]), **kw)

    def routine(self, name: str, type_: str, args: dict[str, Any]) -> RevisionView:
        self.tick()
        return self.accepted(name, self.api.commit(self.pid, self.command(name, type_, args)))  # no preview (dependencies §4.1)

    def rejected(self, name: str, type_: str, args: dict[str, Any], code: str) -> None:
        self.tick()
        before = project_state(self.api, self.pid)
        command = self.command(name, type_, args)
        preview = self.api.preview(self.pid, command)
        commit = self.api.commit(self.pid, command)
        for response in (preview, commit):
            assert (response.status_code, response.json()["error"]["code"]) == (422, code), (name, response.text)
        self.record(name, commit)
        assert_unchanged(before, project_state(self.api, self.pid))

    # --- the scenario -----------------------------------------------------------------------------

    def run(self) -> dict[str, Any]:
        api, pid = self.api, self.pid
        created = api.post("/api/v1/projects", {"command_id": str(uuid.uuid5(_NS, "create")), "type": "CreateReferenceProject", "args": {}})
        assert created.json()["project_id"] == pid
        self.accepted("create", created)
        rev2_target = None

        # 1. A complete price book: the estimate becomes CURRENT, no revision is created.
        self.tick()
        put = api.put(f"/api/v1/projects/{pid}/price-book", BOOK)
        assert put.status_code == 201
        self.record("price-book", put)
        view = check_revision(api, pid, self.head_view.revision_id)
        assert view.envelopes["preliminary_estimate"]["payload"]["coverage"] == "complete"

        # 2. Width 40'.
        footprint = self.head_view.one("Footprint")
        rev2_target = self.consequential("width-40", "SetFootprintDimensions", {"width_m": 40 * FT, "depth_m": footprint["depth_m"]}).revision_id

        # 3. X into four bays, keeping x1 and x2 (D042).
        grid = self.head_view.one("TimberGrid")
        x_lines = [{"id": "x0", "fraction": 0}, {"id": "x1", "fraction": 0.25}, {"id": "x2", "fraction": 0.5}, {"fraction": 0.75}, {"id": "x3", "fraction": 1}]
        view = self.consequential("grid-x-4", "SetTimberGrid", {"x_lines": x_lines, "y_lines": grid["y_lines"]})
        assert [line["id"] for line in view.one("TimberGrid")["x_lines"]] == ["x0", "x1", "x2", "x4", "x3"]

        # 4. 76' now fits four bays; 100' is outside the supported range and changes nothing (AC-06).
        self.consequential("width-76", "SetFootprintDimensions", {"width_m": 76 * FT, "depth_m": footprint["depth_m"]})
        self.rejected("width-100", "SetFootprintDimensions", {"width_m": 100 * FT, "depth_m": footprint["depth_m"]}, "UNSUPPORTED_CONFIGURATION")

        # 5. Story heights 10' and 10'.
        view = self.consequential("stories-10-10", "SetStoryHeights", {"story_heights_m": [10 * FT, 10 * FT]})
        assert math.isclose(view.envelopes["mesh3d"]["payload"]["envelope"]["z_eave_m"], 20 * FT, abs_tol=1e-9)

        # 6. Roof 10/12: consequential since D057, because the pitch places rafters and purlins.
        self.consequential("roof-10-12", "SetGableRoofParameters", {"pitch_rad": math.atan(10 / 12), "eave_overhang_m": 2 * FT})

        # 7. A new section on the beams: the old price row becomes unused and the estimate partial.
        view = self.routine("add-section-10x12", "AddSection", {"nominal_label": "10x12", "actual_width_m": 0.2413, "actual_depth_m": 0.2921})
        section_id = next(s["id"] for s in view.entities("Section") if s["nominal_label"] == "10x12")
        view = self.consequential("beam-10x12", "SetMemberSection", {"role": "BEAM", "section_id": section_id})
        estimate = view.envelopes["preliminary_estimate"]
        assert estimate["payload"]["coverage"] == "partial"
        assert "PRICE_ROWS_UNUSED" in [w["code"] for w in estimate["warnings"]]

        # 8. A retry is replayed; a stale base conflicts. Neither changes anything (interfaces §9 tests 4–5).
        before = project_state(api, pid)
        retry = api.commit(pid, self.commands["beam-10x12"])  # same command_id and payload
        assert retry.status_code == 200 and retry.json()["replayed"] is True
        self.record("retry-beam-10x12", retry)
        stale = api.commit(pid, self.command("stale-roof", "SetGableRoofParameters", {"pitch_rad": 0.5, "eave_overhang_m": 0.0}, base=rev2_target))
        assert (stale.status_code, stale.json()["error"]["code"]) == (409, "REVISION_CONFLICT")
        self.record("stale-roof", stale)
        assert_unchanged(before, project_state(api, pid))

        # 9. Undo to revision 2: content equals that revision (D044).
        view = self.consequential("undo-to-2", "UndoToRevision", {"target_revision_id": rev2_target}, preserve_ids=False)
        target = self.views[rev2_target].snapshot
        assert (view.snapshot["building"], view.snapshot["entities"]) == (target["building"], target["entities"])

        # 10. Replaying the operation log in a fresh store reproduces every revision (AC-09).
        self.replay()
        return self.golden()

    def replay(self) -> None:
        service = self.api.service
        fresh = ProjectService(MemoryStore(), token_key=service._key, project_id_factory=lambda: self.pid)
        for op in service.list_operations(self.pid):
            if op.result == "rejected":
                continue
            if op.command_type == "CreateReferenceProject":
                fresh.create_project(op.command, actor_id=op.actor_id, now=op.created_at)
            else:
                token = fresh.preview(self.pid, op.command, actor_id=op.actor_id, now=op.created_at).preview_token
                fresh.commit(self.pid, op.command, token, actor_id=op.actor_id, now=op.created_at)
        original = [(r["revision_id"], snapshot_fingerprint(service.get_revision(self.pid, r["revision_id"]))) for r in service.list_revisions(self.pid)]
        replayed = [(r["revision_id"], snapshot_fingerprint(fresh.get_revision(self.pid, r["revision_id"]))) for r in fresh.list_revisions(self.pid)]
        assert replayed == original

    def golden(self) -> dict[str, Any]:
        """The deterministic record (TEST-001 §6): fingerprints per revision, read at the end of the run."""
        revisions = []
        for summary in api_revisions(self.api, self.pid):
            rev = summary["revision_id"]
            view = check_revision(self.api, self.pid, rev)
            revisions.append({
                "sequence": summary["sequence"],
                "revision_id": rev,
                "command_type": summary["command_type"],
                "snapshot_fingerprint": snapshot_fingerprint(self.api.service.get_revision(self.pid, rev)),
                "artifacts": {
                    kind: {
                        "status": env["status"],
                        "generator_version": env["generator_version"],
                        "input_fingerprint": env["input_fingerprint"],
                        "payload_fingerprint": None if env["payload"] is None else fingerprint(env["payload"]),
                    }
                    for kind, env in view.envelopes.items()
                },
            })
        return {
            "_note": "Generated by `uv run python tests/integration/golden.py` (TEST-001 §6). Do not edit by hand; regenerate and review the diff.",
            "project_id": self.pid,
            "steps": self.steps,
            "revisions": revisions,
        }


def api_revisions(api, pid: str) -> list[dict[str, Any]]:
    return api.get(f"/api/v1/projects/{pid}/revisions").json()["revisions"]


def run_scenario(store) -> dict[str, Any]:
    from api_support import make_api

    with deterministic_uuid4():
        api = make_api(store, project_id_factory=lambda: PROJECT_ID)
        return Scenario(api).run()


def render(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
