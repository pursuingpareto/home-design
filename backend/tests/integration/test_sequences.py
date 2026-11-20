"""TEST-001 §7: Hypothesis-generated command sequences, with whole-house invariants after every step.

Arguments are drawn inside and just outside the D032/D034 bounds, so both acceptance and rejection
are exercised. Accepted commands must keep every invariant; rejected ones must change nothing.
Profiles (conftest.py): `ci` (default, derandomized, 40 sequences) and `thorough` (500).
"""

from __future__ import annotations

import math
import uuid
from datetime import timedelta
from typing import Any

from hypothesis import HealthCheck, event, given, settings
from hypothesis import strategies as st

from api_support import make_api
from homedesign.model.connections import CONNECTION_TYPES, JUNCTION_CLASSES
from homedesign.project import MemoryStore
from integration.invariants import RevisionView, assert_unchanged, check_revision, check_transition, project_state

FT = 0.3048
PROJECT_ID = "3e1d2c4b-5a69-4f78-8b9a-0c1d2e3f4a5b"
_NS = uuid.UUID("7f6e5d4c-3b2a-4190-8a7b-6c5d4e3f2a1b")
LABELS = ["8x8", "8x12", "10x10", "10x12", "6x8"]


def _grid_lines(view: RevisionView, axis: str) -> list[dict[str, Any]]:
    return [dict(line) for line in view.one("TimberGrid")[f"{axis}_lines"]]


def draw_command(data: st.DataObject, view: RevisionView, history: list[str]) -> tuple[str, dict[str, Any]]:
    kind = data.draw(st.sampled_from(["footprint", "stories", "roof", "grid", "frame", "add_section", "member_section", "connection_type", "undo"]), label="kind")
    length = lambda lo, hi: data.draw(st.floats(lo, hi, allow_nan=False, allow_infinity=False))  # noqa: E731
    if kind == "footprint":
        if data.draw(st.booleans(), label="inside"):  # half within what a 3 × 2 bay grid supports
            return "SetFootprintDimensions", {"width_m": length(12 * FT, 70 * FT), "depth_m": length(12 * FT, 46 * FT)}
        return "SetFootprintDimensions", {"width_m": length(10 * FT, 85 * FT), "depth_m": length(10 * FT, 85 * FT)}
    if kind == "stories":
        return "SetStoryHeights", {"story_heights_m": [length(7 * FT, 15 * FT), length(7 * FT, 15 * FT)]}
    if kind == "roof":
        return "SetGableRoofParameters", {"pitch_rad": length(math.atan(2 / 12), math.atan(13 / 12)), "eave_overhang_m": length(0.0, 3.5 * FT)}
    if kind == "frame":  # MODEL-005 §5, §7.1: drawn inside and just outside the bounds
        return "SetFrameParameters", {
            "joist_spacing_m": length(10 / 12 * FT, 50 / 12 * FT),
            "purlins_per_slope": data.draw(st.integers(-1, 5)),
            "knee_brace_leg_m": length(1.25 * FT, 4.25 * FT),
            "knee_braces_level_1": data.draw(st.booleans()),
            "knee_braces_eave": data.draw(st.booleans()),
        }
    if kind == "grid":
        axis = data.draw(st.sampled_from(["x", "y"]))
        lines = _grid_lines(view, axis)
        op = data.draw(st.sampled_from(["equal", "move", "remove", "add"]))
        if op == "equal":
            bays = data.draw(st.integers(1, 7))  # 7 bays = 8 stations: unsupported
            interior = [line["id"] for line in lines[1:-1]]
            new = [{"id": interior[k - 1], "fraction": k / bays} if k - 1 < len(interior) else {"fraction": k / bays} for k in range(1, bays)]
            lines = [lines[0], *new, lines[-1]]
        elif op == "move" and len(lines) > 2:
            k = data.draw(st.integers(1, len(lines) - 2))
            lines[k]["fraction"] = data.draw(st.floats(0.01, 0.99))
            lines.sort(key=lambda line: line["fraction"])  # may still collide; the server decides
        elif op == "remove" and len(lines) > 2:
            del lines[data.draw(st.integers(1, len(lines) - 2))]
        else:
            lines.append({"fraction": data.draw(st.floats(0.01, 0.99))})
            lines.sort(key=lambda line: line["fraction"])
        other = "y" if axis == "x" else "x"
        return "SetTimberGrid", {f"{axis}_lines": lines, f"{other}_lines": _grid_lines(view, other)}
    if kind == "add_section":
        return "AddSection", {"nominal_label": data.draw(st.sampled_from(LABELS)), "actual_width_m": length(0.0, 0.4), "actual_depth_m": length(0.0, 0.4)}
    if kind == "member_section":
        sections = [s["id"] for s in sorted(view.entities("Section"), key=lambda s: (s["nominal_label"], s["actual_width_m"], s["actual_depth_m"]))]
        return "SetMemberSection", {"role": data.draw(st.sampled_from(["POST", "BEAM", "SILL", "FLOOR_JOIST", "PRINCIPAL_RAFTER", "PURLIN", "KNEE_BRACE"])), "section_id": data.draw(st.sampled_from(sections))}
    if kind == "connection_type":  # CONN-001 §8: any class and type, so disallowed pairs are drawn too
        return "SetConnectionType", {
            "junction_class": data.draw(st.sampled_from(JUNCTION_CLASSES)),
            "connection_type": data.draw(st.sampled_from(CONNECTION_TYPES)),
        }
    return "UndoToRevision", {"target_revision_id": data.draw(st.sampled_from(history))}


@settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large], deadline=None)
@given(data=st.data(), steps=st.integers(1, 8))
def test_random_command_sequences_keep_every_invariant(data, steps):
    # Fixed IDs: minted IDs (and so entity order) must not differ between runs of one example.
    api = make_api(MemoryStore(), project_id_factory=lambda: PROJECT_ID)
    created = api.post("/api/v1/projects", {"command_id": str(uuid.uuid5(_NS, "create")), "type": "CreateReferenceProject", "args": {}})
    pid = created.json()["project_id"]
    view = check_revision(api, pid, api.head(pid))
    history = [view.revision_id]
    for step in range(steps):
        api.clock.now += timedelta(minutes=1)
        type_, args = draw_command(data, view, history)
        command = {"command_id": str(uuid.uuid5(_NS, f"step-{step}")), "project_id": pid, "base_revision_id": view.revision_id, "type": type_, "args": args}
        before = project_state(api, pid)
        preview = api.preview(pid, command)
        if preview.status_code != 200:
            assert preview.status_code == 422, (type_, args, preview.text)
            event(f"{type_}: rejected ({preview.json()['error']['code']})")
            assert_unchanged(before, project_state(api, pid))
            continue
        commit = api.commit(pid, command, preview.json()["preview_token"])
        assert commit.status_code in (200, 201), (type_, args, commit.text)  # 200: a no-op (D045)
        body = commit.json()
        event(f"{type_}: {'no-op' if body['is_noop'] else 'accepted'}")
        if body["is_noop"]:
            assert_unchanged(before, project_state(api, pid))
            continue
        after = check_revision(api, pid, body["revision_id"])
        check_transition(view, after, preserve_ids=type_ != "UndoToRevision")
        view = after
        history.append(view.revision_id)
