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
from collections import Counter
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from typing import Any, Iterator
from unittest.mock import patch

from homedesign.model.canonical import fingerprint, snapshot_fingerprint
from homedesign.project import MemoryStore, ProjectService

from integration.invariants import RevisionView, assert_unchanged, check_impact, check_revision, check_transition, project_state

REPO_ROOT = Path(__file__).resolve().parents[3]
GOLDEN_PATH = REPO_ROOT / "tests" / "vectors" / "scenarios" / "reference-house-001.json"
PROJECT_ID = "5c3a9e1f-7b2d-4c8e-9f01-2a3b4c5d6e7f"
_NS = uuid.UUID("0d5c6a2e-91b4-4f3a-8e27-6b1f0c9d4a83")
FT = 0.3048
BOOK = {
    "currency": "USD", "as_of": "2026-11-01", "source": "Scenario supplier quote", "geography": "Chittenden County, VT",
    # One row per timber line (D053), connection type (ART-002 §7), and straw bale wall line (ART-003 §7) of Reference
    # House 001 v3, so the estimate is complete. Assembly rows are per square meter.
    "rows": [
        {"key": key, "unit": "each" if key.startswith("connection.") else "m2" if key.startswith("assembly.") else "m", "unit_price_minor": price}
        for key, price in (
            ("assembly.straw-bale.bales", 2200), ("assembly.straw-bale.clay-plaster", 3500), ("assembly.straw-bale.lime-plaster", 4200),
            ("connection.BRIDLE", 6500), ("connection.HOUSED_DOVETAIL", 3800), ("connection.PEGGED_MORTISE_TENON", 4500),
            ("timber.BEAM.8x12", 4725), ("timber.FLOOR_JOIST.4x8", 1200), ("timber.KNEE_BRACE.4x6", 900), ("timber.POST.8x8", 3150),
            ("timber.PRINCIPAL_RAFTER.8x10", 3900), ("timber.PURLIN.6x8", 2350), ("timber.SILL.8x8", 3150),
            ("wallframing.BUCK_HEAD.1.5x18", 1900), ("wallframing.BUCK_JAMB.1.5x18", 1900), ("wallframing.BUCK_SILL.1.5x18", 1900),
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
        self.impacts: list[tuple[str, str, list[str]]] = []  # (base, new revision, impacted_artifacts) per previewed commit
        self.last_preview: dict[str, Any] | None = None  # the last committed step's preview body

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

    def record(self, name: str, response, impacted: list[str] | None = None) -> None:
        body = response.json()
        step = {"step": name, "status": response.status_code, "code": body.get("error", {}).get("code"), "replayed": body.get("replayed", False)}
        if impacted is not None:
            step["impacted_artifacts"] = impacted  # from the step's preview (DEP-001 §10)
        self.steps.append(step)

    def accepted(self, name: str, response, impacted: list[str] | None = None, *, preserve_ids: bool = True, command: dict[str, Any] | None = None) -> RevisionView:
        assert response.status_code == 201, (name, response.status_code, response.text)
        self.record(name, response, impacted)
        view = check_revision(self.api, self.pid, response.json()["revision_id"])
        if self.head_view is not None:
            check_transition(self.head_view, view, preserve_ids=preserve_ids, command=command)
            if impacted is not None:
                check_impact(self.head_view, view, impacted)  # AC2-04
                self.impacts.append((self.head_view.revision_id, view.revision_id, impacted))
        self.views[view.revision_id] = self.head_view = view
        return view

    def consequential(self, name: str, type_: str, args: dict[str, Any], **kw) -> RevisionView:
        self.tick()
        command = self.commands[name] = self.command(name, type_, args)
        preview = self.api.preview(self.pid, command)
        assert preview.status_code == 200 and preview.json()["confirmation_required"], (name, preview.text)
        impacted = preview.json()["impacted_artifacts"]
        self.last_preview = preview.json()
        return self.accepted(name, self.api.commit(self.pid, command, preview.json()["preview_token"]), impacted, command=command, **kw)

    def routine(self, name: str, type_: str, args: dict[str, Any]) -> RevisionView:
        self.tick()
        command = self.command(name, type_, args)
        preview = self.api.preview(self.pid, command)  # previewed for its impact; committed without a token (dependencies §4.1)
        assert preview.status_code == 200 and not preview.json()["confirmation_required"], (name, preview.text)
        self.last_preview = preview.json()
        return self.accepted(name, self.api.commit(self.pid, command), preview.json()["impacted_artifacts"], command=command)

    def rejected(self, name: str, type_: str, args: dict[str, Any], code: str) -> dict[str, Any]:
        self.tick()
        before = project_state(self.api, self.pid)
        command = self.command(name, type_, args)
        preview = self.api.preview(self.pid, command)
        commit = self.api.commit(self.pid, command)
        for response in (preview, commit):
            assert (response.status_code, response.json()["error"]["code"]) == (422, code), (name, response.text)
        self.record(name, commit)
        assert_unchanged(before, project_state(self.api, self.pid))
        return commit.json()["error"]

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
        view = self.views[view.revision_id] = self.head_view = check_revision(api, pid, self.head_view.revision_id)  # the base of step 2
        assert view.envelopes["preliminary_estimate"]["payload"]["coverage"] == "complete"

        # 2. Width 40'.
        footprint = self.head_view.one("Footprint")
        rev2_target = self.consequential("width-40", "SetFootprintDimensions", {"width_m": 40 * FT, "depth_m": footprint["depth_m"]}).revision_id

        # 3. X into four bays, keeping x1 and x2 (D042).
        grid = self.head_view.one("TimberGrid")
        x_lines = [{"id": "x0", "fraction": 0}, {"id": "x1", "fraction": 0.25}, {"id": "x2", "fraction": 0.5}, {"fraction": 0.75}, {"id": "x3", "fraction": 1}]
        view = self.consequential("grid-x-4", "SetTimberGrid", {"x_lines": x_lines, "y_lines": grid["y_lines"]})
        assert [line["id"] for line in view.one("TimberGrid")["x_lines"]] == ["x0", "x1", "x2", "x4", "x3"]
        # The x2-x3 bay's 4 walls are replaced, and their 4 openings are removed with them; the preview lists them (D069, AC2b-04).
        walls = self.last_preview["walls"]
        assert (len(walls["added"]), len(walls["removed"]), len(walls["updated"])) == (8, 4, 8)
        removed = [c for c in self.last_preview["changes"] if c["entity_kind"] == "Opening" and c["after"] is None and c["field"] == ""]
        assert len(removed) == 4 and len(view.entities("Opening")) == 16

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

        # 7a. Joist spacing 0.62 m keeps the joist count at these 19' bays: member and connection IDs are
        # kept, and the schedule and the estimate are reused (DEP-001 §8, TEST-002 §6).
        # A frame edit on the straw bale house moves no wall piece, so the assembly schedule is reused (ART-003 §8.3).
        frame_edit = sorted(kind for kind in view.envelopes if kind != "assembly_schedule")
        parameters = view.one("FrameSystem")["parameters"]
        view = self.consequential("frame-joists-0.62", "SetFrameParameters", {**parameters, "joist_spacing_m": 0.62})
        assert sorted(self.impacts[-1][2]) == ["mesh3d", "plan2d"]

        # 7b. Eave braces off: their members and connections are retired; survivors keep their IDs (check_transition).
        view = self.consequential("frame-eave-braces-off", "SetFrameParameters", {**parameters, "joist_spacing_m": 0.62, "knee_braces_eave": False})
        assert sorted(self.impacts[-1][2]) == frame_edit
        assert (len(view.members()), len(view.connections())) == (238, 382)

        # 7c. Joist hangers on the joist-beam class: a new, unpriced line, so the estimate stays partial with no total, never 0 (AC2-06).
        view = self.consequential("joist-beam-hanger", "SetConnectionType", {"junction_class": "joist-beam", "connection_type": "JOIST_HANGER"})
        assert sorted(self.impacts[-1][2]) == frame_edit
        estimate = view.envelopes["preliminary_estimate"]["payload"]
        hanger = next(line for line in estimate["line_items"] if line["key"] == "connection.JOIST_HANGER")
        assert (hanger["quantity_value"], hanger["quantity_unit"], hanger["priced"], hanger["amount_minor"]) == (144, "each", False, None)
        assert estimate["coverage"] == "partial" and estimate["totals"]["grand_total_minor"] is None

        # 7d–7e. A disallowed connection type and an out-of-range frame parameter change nothing (AC2-03, AC-06).
        error = self.rejected("joist-beam-bridle", "SetConnectionType", {"junction_class": "joist-beam", "connection_type": "BRIDLE"}, "UNSUPPORTED_CONFIGURATION")
        assert [(d["code"], d["path"].endswith('.connection_defaults["joist-beam"]')) for d in error["details"]] == [("UNSUPPORTED_VALUE", True)], error
        frame = {**view.one("FrameSystem")["parameters"], "purlins_per_slope": -1}
        error = self.rejected("frame-purlins-minus-1", "SetFrameParameters", frame, "VALIDATION_FAILED")
        assert [(d["code"], d["path"].endswith(".parameters.purlins_per_slope")) for d in error["details"]] == [("OUT_OF_RANGE", True)], error

        # 7f–7m. The four wall commands (TEST-003 §6), on the 76' × 24' straw bale house with 16 openings, Level 0 braces only.
        self.wall_steps()

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
        # Every payload of the target is reused, with its fingerprint (DEP-001 §7.2).
        for kind, envelope in view.envelopes.items():
            assert envelope["input_fingerprint"] == self.views[rev2_target].envelopes[kind]["input_fingerprint"], kind
        # Straw bale and revision 2's 20 openings are back, with their IDs: 7l's removed window returns, 7f's is gone (D044).
        assert sorted(o["id"] for o in view.entities("Opening")) == sorted(o["id"] for o in self.views[rev2_target].entities("Opening"))
        assert len(view.entities("Opening")) == 20 and view.one("WallSystem") == self.views[rev2_target].one("WallSystem")

        # 10. Replaying the operation log in a fresh store reproduces every revision (AC-09).
        self.replay()
        return self.golden()

    def wall_steps(self) -> None:
        """Steps 7f–7m (TEST-003 §6.1): each wall command committed, and a rejection of each."""
        view = self.head_view
        wall = lambda key: next(w for w in self.head_view.entities("Wall") if w["generation_key"] == key)  # noqa: E731
        opening_in = lambda key: next(o for o in self.head_view.entities("Opening") if o["wall_id"] == wall(key)["id"])  # noqa: E731
        stud_infill = next(d["id"] for d in view.entities("AssemblyDefinition") if d["label"] == "stud-infill")
        not_timber = sorted(kind for kind in view.envelopes if kind != "timber_schedule")
        counts = lambda v: Counter(p["piece_kind"] for p in v.entities("WallFramingPiece"))  # noqa: E731

        def single_detail(error: dict[str, Any], code: str, path_end: str, related_first: str | None = None) -> dict[str, Any]:
            (detail,) = error["details"]
            assert (detail["code"], detail["path"].endswith(path_end)) == (code, True), error
            if related_first is not None:
                assert detail["related_paths"][0] == related_first, error
            return detail

        # 7f. A routine AddOpening: a 3' × 4' window 6" from the start post, under the Level 0 brace. Bucks fit there.
        near_brace = "wall/axis-x/y0/x4-x3/level-0"
        window = {"wall_id": wall(near_brace)["id"], "opening_kind": "WINDOW", "width_m": 3 * FT, "height_m": 4 * FT, "sill_height_m": 3 * FT, "offset_m": 0.5 * FT}
        view = self.routine("add-window-near-brace", "AddOpening", window)
        assert sorted(self.impacts[-1][2]) == not_timber
        added = next(o for o in view.entities("Opening") if o["wall_id"] == window["wall_id"])
        assert (len(view.entities("Opening")), len(view.entities("WallFramingPiece"))) == (17, 67)

        # 7g. Stud infill's kings and header would meet the brace: rejected through SetWallAssembly, naming the window and the argument.
        error = self.rejected("assembly-stud-infill-crosses-brace", "SetWallAssembly", {"assembly_definition_id": stud_infill}, "UNSUPPORTED_CONFIGURATION")
        single_detail(error, "OPENING_CROSSES_BRACE", f"entities[{added['id']}].offset_m", "args.assembly_definition_id")

        # 7h. Centering it moves it along its wall. A buck sill total changes in its last bit (15.240000000000004 -> 15.24 m),
        # so the estimate is impacted too: exact under D056 (DEP2b-3).
        view = self.routine("center-window", "SetOpening", {"opening_id": added["id"], **{k: window[k] for k in ("width_m", "height_m", "sill_height_m")}, "offset_m": 8 * FT})
        assert sorted(self.impacts[-1][2]) == not_timber

        # 7i. SetWallAssembly to stud infill: every wall and its framing, never a member or connection (D068, AC2b-03).
        view = self.consequential("assembly-stud-infill", "SetWallAssembly", {"assembly_definition_id": stud_infill})
        assert sorted(self.impacts[-1][2]) == not_timber
        framing = self.last_preview["wall_framing"]
        assert (len(self.last_preview["walls"]["updated"]), len(framing["added"]), len(framing["removed"])) == (24, 311, 67)
        assert counts(view) == {"STUD": 164, "GIRT": 41, "KING": 34, "JACK": 2, "HEADER": 17, "ROUGH_SILL": 16, "CRIPPLE": 37}
        assert (len(view.members()), len(view.connections())) == (238, 382)
        estimate = view.envelopes["preliminary_estimate"]
        assert (estimate["payload"]["coverage"], estimate["payload"]["totals"]["grand_total_minor"]) == ("partial", None)
        assert "PRICE_ROWS_UNUSED" in [w["code"] for w in estimate["warnings"]]  # the buck rows; the stud infill lines are unpriced, never 0
        assert all(not line["priced"] and line["amount_minor"] is None for line in estimate["payload"]["line_items"] if line["key"].startswith(("wallframing.STUD", "assembly.stud-infill")))

        # 7j–7k. An opening command's fit rejections: a head above the wall (Level 1 has no braces now), and an overlap.
        tall = opening_in("wall/axis-x/y0/x0-x1/level-1")
        error = self.rejected("window-level-1-8ft", "SetOpening", {"opening_id": tall["id"], "width_m": tall["width_m"], "height_m": 8 * FT, "sill_height_m": tall["sill_height_m"], "offset_m": tall["offset_m"]}, "UNSUPPORTED_CONFIGURATION")
        single_detail(error, "OPENING_OUTSIDE_WALL", f"entities[{tall['id']}].height_m", "args.height_m")
        error = self.rejected("overlapping-window", "AddOpening", {**window, "offset_m": 9 * FT}, "UNSUPPORTED_CONFIGURATION")
        detail = single_detail(error, "OPENINGS_OVERLAP", ".offset_m", "args.offset_m")
        named = [detail["path"], *detail["related_paths"]]  # one opening carries the detail, the other is related: both are named
        assert f"entities[{added['id']}].offset_m" in named and sum(p.endswith(".offset_m") and p.startswith("entities[") for p in named) == 2, error

        # 7l–7m. A routine RemoveOpening of a fixture window (the undo restores it), then the same ID again.
        north = opening_in("wall/axis-x/y2/x0-x1/level-1")["id"]
        view = self.routine("remove-north-window", "RemoveOpening", {"opening_id": north})
        assert sorted(self.impacts[-1][2]) == not_timber
        framing = self.last_preview["wall_framing"]
        assert (len(framing["added"]), len(framing["removed"]), len(framing["updated"])) == (1, 7, 1)
        assert (len(view.entities("Opening")), len(view.entities("WallFramingPiece"))) == (16, 305)
        error = self.rejected("remove-north-window-again", "RemoveOpening", {"opening_id": north}, "VALIDATION_FAILED")
        single_detail(error, "DANGLING_REFERENCE", "args.opening_id")

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
        check_recorded_impact(revisions, self.impacts)
        return {
            "_note": "Generated by `uv run python tests/integration/golden.py` (TEST-001 §6). Do not edit by hand; regenerate and review the diff.",
            "project_id": self.pid,
            "steps": self.steps,
            "revisions": revisions,
        }


def check_recorded_impact(revisions: list[dict[str, Any]], impacts: list[tuple[str, str, list[str]]]) -> None:
    """AC2-04 on the record itself: between a step's base and its new revision, exactly the impacted
    artifacts change status or payload fingerprint, and only they change input fingerprint."""
    by_id = {r["revision_id"]: r["artifacts"] for r in revisions}
    assert len(impacts) == len(revisions) - 1  # every revision after the first comes from a previewed commit
    for base, new, impacted in impacts:
        for kind, after in by_id[new].items():
            before = by_id[base][kind]
            changed = (before["status"], before["payload_fingerprint"]) != (after["status"], after["payload_fingerprint"])
            assert changed == (kind in impacted), (new, kind, impacted)
            assert (before["input_fingerprint"] != after["input_fingerprint"]) == (kind in impacted), (new, kind, impacted)


def api_revisions(api, pid: str) -> list[dict[str, Any]]:
    return api.get(f"/api/v1/projects/{pid}/revisions").json()["revisions"]


def run_scenario(store) -> dict[str, Any]:
    from api_support import make_api

    with deterministic_uuid4():
        api = make_api(store, project_id_factory=lambda: PROJECT_ID)
        return Scenario(api).run()


def render(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
