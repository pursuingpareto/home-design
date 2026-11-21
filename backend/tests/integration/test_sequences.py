"""TEST-001 §7: Hypothesis-generated command sequences, with whole-house invariants after every step.

Arguments are drawn inside and just outside the D032/D034 bounds, so both acceptance and rejection
are exercised. Accepted commands must keep every invariant; rejected ones must change nothing.
Every accepted step also checks AC2-04: the preview's `impacted_artifacts` lists exactly the artifacts
whose outcome changes (DEP-001 §10). The draw includes the edits whose impact is narrow: pitch-only and
overhang-only roof edits, joist-spacing-only frame edits, sections with an existing section's
dimensions, and grid lines re-identified at the same fraction. So that the `ci` run reaches these narrow
outcomes (TEST-002 §7): half the joist-spacing draws stay within 10% above the stored spacing, which usually
keeps the joist count; half the section swaps pick a section with the role's current dimensions when one
exists, and the step right after an AddSection makes such a swap; half the connection-type draws pick the
class's other allowed type; a draw of its own re-identifies one grid line; and half of all steps are a
targeted edit, one per outcome the gate requires (`draw_targeted`).
Profiles (conftest.py): `ci` (default, derandomized, 40 sequences) and `thorough` (500). Under `ci`, an
outcome gate checks that the sequences still reach every VS-02 outcome (TEST-002 §7).
"""

from __future__ import annotations

import math
import uuid
from datetime import timedelta
from typing import Any

import pytest
from hypothesis import HealthCheck, event, given, settings
from hypothesis import strategies as st

from api_support import make_api
from homedesign.model.connections import ALTERNATIVES, CONNECTION_TYPES, DEFAULTS, JUNCTION_CLASSES
from homedesign.project import MemoryStore
from integration.invariants import RevisionView, assert_unchanged, check_impact, check_revision, check_transition, project_state

FT = 0.3048
PROJECT_ID = "3e1d2c4b-5a69-4f78-8b9a-0c1d2e3f4a5b"
_NS = uuid.UUID("7f6e5d4c-3b2a-4190-8a7b-6c5d4e3f2a1b")
LABELS = ["8x8", "8x12", "10x10", "10x12", "6x8"]


def _grid_lines(view: RevisionView, axis: str) -> list[dict[str, Any]]:
    return [dict(line) for line in view.one("TimberGrid")[f"{axis}_lines"]]


def same_dimension_swaps(view: RevisionView) -> list[tuple[str, str]]:
    """(role, section ID) for every other section with the dimensions of a role's current one, in a fixed order."""
    sections = {s["id"]: s for s in view.entities("Section")}
    dims = lambda section: (section["actual_width_m"], section["actual_depth_m"])  # noqa: E731
    return [
        (role, section_id)
        for role, default in sorted(view.one("FrameSystem")["member_defaults"].items())
        for section_id in sorted(sections)
        if section_id != default["section_id"] and dims(sections[section_id]) == dims(sections[default["section_id"]])
    ]


KINDS = [
    "footprint", "stories", "roof", "roof_pitch", "roof_overhang", "grid", "grid_reidentify", "frame", "joist_spacing", "add_section",
    "member_section", "connection_type", "undo",
]
# One edit per outcome the gate requires (TEST-002 §7), each of which reaches it from the created house and,
# usually, from the houses the sequences reach. A run has few steps (Hypothesis favors short sequences), so an
# outcome that only one branch of one kind reaches is missed by many seeds; half of all steps are one of these.
TARGETS = [
    "footprint accepted", "footprint rejected", "stories accepted", "stories rejected", "roof pitch only", "roof overhang only",
    "roof rejected", "grid line re-identified", "grid rejected", "joist spacing keeping the count", "frame rejected",
    "section with existing dimensions", "section rejected", "connection type allowed", "connection type disallowed",
    "undo to an earlier revision",
]


def draw_targeted(data: st.DataObject, view: RevisionView, history: list[str]) -> tuple[str, dict[str, Any]]:
    target = data.draw(st.sampled_from(TARGETS), label="target")
    event(f"draw: {target} (targeted)")
    length = lambda lo, hi: data.draw(st.floats(lo, hi, allow_nan=False, allow_infinity=False))  # noqa: E731
    footprint, roof = view.one("Footprint"), view.one("GableRoof")
    frame = view.one("FrameSystem")
    if target == "footprint accepted":  # within 3% of the current width: the bays usually stay supported
        width = min(max(footprint["width_m"] * length(0.97, 1.03), 12 * FT), 80 * FT)
        return "SetFootprintDimensions", {"width_m": width, "depth_m": footprint["depth_m"]}
    if target == "footprint rejected":
        return "SetFootprintDimensions", {"width_m": length(81 * FT, 100 * FT), "depth_m": footprint["depth_m"]}
    if target == "stories accepted":  # D034: 8'–14'
        return "SetStoryHeights", {"story_heights_m": [length(8.5 * FT, 13.5 * FT), length(8.5 * FT, 13.5 * FT)]}
    if target == "stories rejected":
        return "SetStoryHeights", {"story_heights_m": [length(5 * FT, 7.5 * FT), length(8.5 * FT, 13.5 * FT)]}
    if target == "roof pitch only":  # 3/12–12/12; impacts all but the plan (DEP-001 §8)
        return "SetGableRoofParameters", {"pitch_rad": length(math.atan(3.5 / 12), math.atan(11.5 / 12)), "eave_overhang_m": roof["eave_overhang_m"]}
    if target == "roof overhang only":  # 0–3'; impacts the plan and the mesh only
        return "SetGableRoofParameters", {"pitch_rad": roof["pitch_rad"], "eave_overhang_m": length(0.0, 2.9 * FT)}
    if target == "roof rejected":
        return "SetGableRoofParameters", {"pitch_rad": length(math.atan(13 / 12), math.atan(16 / 12)), "eave_overhang_m": roof["eave_overhang_m"]}
    if target in ("grid line re-identified", "grid rejected"):
        lines = _grid_lines(view, "y")
        if target == "grid line re-identified" and len(lines) > 2:  # a y line: the estimate is kept (impact 3)
            k = data.draw(st.integers(1, len(lines) - 2))
            lines[k] = {"fraction": lines[k]["fraction"]}
        elif target == "grid rejected":  # 8 stations: more than D032 supports
            lines = [lines[0], *({"fraction": k / 7} for k in range(1, 7)), lines[-1]]
        return "SetTimberGrid", {"x_lines": _grid_lines(view, "x"), "y_lines": lines}
    if target == "joist spacing keeping the count":  # within 10% above the stored spacing
        stored = frame["parameters"]["joist_spacing_m"]
        spacing = data.draw(st.floats(stored, max(stored, min(stored * 1.1, 48 / 12 * FT)), exclude_min=stored < 48 / 12 * FT))
        return "SetFrameParameters", {**frame["parameters"], "joist_spacing_m": spacing}
    if target == "frame rejected":
        return "SetFrameParameters", {**frame["parameters"], "purlins_per_slope": data.draw(st.sampled_from([-1, 5]))}
    if target == "section with existing dimensions":  # the step after it swaps a role to it (impact 2)
        existing = data.draw(st.sampled_from(sorted(view.entities("Section"), key=lambda s: s["id"])))
        label = data.draw(st.sampled_from(LABELS)) + data.draw(st.sampled_from(["b", "c", "d"]))
        return "AddSection", {"nominal_label": label, "actual_width_m": existing["actual_width_m"], "actual_depth_m": existing["actual_depth_m"]}
    if target == "section rejected":
        return "AddSection", {"nominal_label": data.draw(st.sampled_from(LABELS)), "actual_width_m": 0.0, "actual_depth_m": length(0.0, 0.4)}
    if target in ("connection type allowed", "connection type disallowed"):
        junction_class = data.draw(st.sampled_from(JUNCTION_CLASSES))
        allowed = (DEFAULTS[junction_class], ALTERNATIVES[junction_class])  # D054
        if target == "connection type allowed":
            current = frame["connection_defaults"][junction_class]
            return "SetConnectionType", {"junction_class": junction_class, "connection_type": allowed[current == allowed[0]]}
        disallowed = [t for t in CONNECTION_TYPES if t not in allowed]
        return "SetConnectionType", {"junction_class": junction_class, "connection_type": data.draw(st.sampled_from(disallowed))}
    return "UndoToRevision", {"target_revision_id": data.draw(st.sampled_from(history[:-1] or history))}


def draw_command(data: st.DataObject, view: RevisionView, history: list[str], last: str | None = None) -> tuple[str, dict[str, Any]]:
    """One command for the step after `view`. `last` is the type of the previous accepted command."""
    # The fixture has no two sections with equal dimensions, so a swap that leaves the mesh unchanged needs an
    # AddSection first: the step right after one makes the swap.
    if last == "AddSection" and same_dimension_swaps(view):
        role, section_id = data.draw(st.sampled_from(same_dimension_swaps(view)))
        return "SetMemberSection", {"role": role, "section_id": section_id}
    if data.draw(st.booleans(), label="targeted"):
        return draw_targeted(data, view, history)
    kind = data.draw(st.sampled_from(KINDS), label="kind")
    event(f"draw: {kind}")
    branch = lambda label: data.draw(st.booleans(), label=label)  # noqa: E731
    length = lambda lo, hi: data.draw(st.floats(lo, hi, allow_nan=False, allow_infinity=False))  # noqa: E731
    if kind == "footprint":
        if data.draw(st.booleans(), label="inside"):  # half within what a 3 × 2 bay grid supports
            return "SetFootprintDimensions", {"width_m": length(12 * FT, 70 * FT), "depth_m": length(12 * FT, 46 * FT)}
        return "SetFootprintDimensions", {"width_m": length(10 * FT, 85 * FT), "depth_m": length(10 * FT, 85 * FT)}
    if kind == "stories":
        return "SetStoryHeights", {"story_heights_m": [length(7 * FT, 15 * FT), length(7 * FT, 15 * FT)]}
    if kind == "roof":
        return "SetGableRoofParameters", {"pitch_rad": length(math.atan(2 / 12), math.atan(13 / 12)), "eave_overhang_m": length(0.0, 3.5 * FT)}
    roof = view.one("GableRoof")
    if kind == "roof_pitch":  # leaves the plan unchanged (DEP-001 §8)
        return "SetGableRoofParameters", {"pitch_rad": length(math.atan(2 / 12), math.atan(13 / 12)), "eave_overhang_m": roof["eave_overhang_m"]}
    if kind == "roof_overhang":  # leaves the schedule and the estimate unchanged
        return "SetGableRoofParameters", {"pitch_rad": roof["pitch_rad"], "eave_overhang_m": length(0.0, 3.5 * FT)}
    if kind == "joist_spacing":  # may keep the joist count, and then the schedule (DEP-001 §8)
        parameters = view.one("FrameSystem")["parameters"]
        if branch("near the stored spacing"):  # within 10% above it: usually the same count
            stored = parameters["joist_spacing_m"]
            spacing = data.draw(st.floats(stored, max(stored, min(stored * 1.1, 50 / 12 * FT)), exclude_min=stored < 50 / 12 * FT))
            return "SetFrameParameters", {**parameters, "joist_spacing_m": spacing}
        return "SetFrameParameters", {**parameters, "joist_spacing_m": length(10 / 12 * FT, 50 / 12 * FT)}
    if kind == "frame":  # MODEL-005 §5, §7.1: drawn inside and just outside the bounds
        args = {
            "joist_spacing_m": length(10 / 12 * FT, 50 / 12 * FT),
            "purlins_per_slope": data.draw(st.integers(-1, 5)),
            "knee_brace_leg_m": length(1.25 * FT, 4.25 * FT),
            "knee_braces_level_1": data.draw(st.booleans()),
            "knee_braces_eave": data.draw(st.booleans()),
        }
        # Draws tend to stay inside the bounds, so half put one parameter just outside (MODEL-005 §5: joists
        # 12"–48", 0–4 purlins, legs 1'-6"–4'-0"), and the rejections are reached too (TEST-002 §7).
        if data.draw(st.booleans(), label="one parameter out of bounds"):
            field, value = data.draw(st.sampled_from([
                ("joist_spacing_m", 11 / 12 * FT), ("joist_spacing_m", 49 / 12 * FT), ("purlins_per_slope", -1), ("purlins_per_slope", 5),
                ("knee_brace_leg_m", 1.25 * FT), ("knee_brace_leg_m", 4.25 * FT),
            ]))
            args[field] = value
        return "SetFrameParameters", args
    if kind == "grid_reidentify":  # a new ID at a line's fraction: re-identifying a y line keeps the estimate (DEP-001 §8)
        axis = data.draw(st.sampled_from(["y", "x"]))
        lines = _grid_lines(view, axis)
        if len(lines) > 2:
            k = data.draw(st.integers(1, len(lines) - 2))
            lines[k] = {"fraction": lines[k]["fraction"]}
        other = "y" if axis == "x" else "x"
        return "SetTimberGrid", {f"{axis}_lines": lines, f"{other}_lines": _grid_lines(view, other)}
    if kind == "grid":
        axis = data.draw(st.sampled_from(["x", "y"]))
        lines = _grid_lines(view, axis)
        op = data.draw(st.sampled_from(["equal", "move", "remove", "add", "reidentify"]))
        if op == "equal":
            bays = data.draw(st.integers(1, 7))  # 7 bays = 8 stations: unsupported
            interior = [line["id"] for line in lines[1:-1]]
            new = [{"id": interior[k - 1], "fraction": k / bays} if k - 1 < len(interior) else {"fraction": k / bays} for k in range(1, bays)]
            lines = [lines[0], *new, lines[-1]]
        elif op == "move" and len(lines) > 2:
            k = data.draw(st.integers(1, len(lines) - 2))
            lines[k]["fraction"] = data.draw(st.floats(0.01, 0.99))
            lines.sort(key=lambda line: line["fraction"])  # may still collide; the server decides
        elif op == "reidentify" and len(lines) > 2:  # a new line ID at the same fraction: may leave the estimate
            k = data.draw(st.integers(1, len(lines) - 2))
            lines[k] = {"fraction": lines[k]["fraction"]}
        elif op == "remove" and len(lines) > 2:
            del lines[data.draw(st.integers(1, len(lines) - 2))]
        else:
            lines.append({"fraction": data.draw(st.floats(0.01, 0.99))})
            lines.sort(key=lambda line: line["fraction"])
        other = "y" if axis == "x" else "x"
        return "SetTimberGrid", {f"{axis}_lines": lines, f"{other}_lines": _grid_lines(view, other)}
    if kind == "add_section":
        if branch("same dimensions"):  # the swap to it, in the next step, leaves the mesh unchanged
            existing = data.draw(st.sampled_from(sorted(view.entities("Section"), key=lambda s: s["id"])))
            label = data.draw(st.sampled_from(LABELS)) + data.draw(st.sampled_from(["", "b", "c"]))
            return "AddSection", {"nominal_label": label, "actual_width_m": existing["actual_width_m"], "actual_depth_m": existing["actual_depth_m"]}
        return "AddSection", {"nominal_label": data.draw(st.sampled_from(LABELS)), "actual_width_m": length(0.0, 0.4), "actual_depth_m": length(0.0, 0.4)}
    if kind == "member_section":
        swaps = same_dimension_swaps(view)
        if swaps and data.draw(st.booleans(), label="same dimensions"):  # the mesh is unchanged (DEP-001 §8)
            role, section_id = data.draw(st.sampled_from(swaps))
            return "SetMemberSection", {"role": role, "section_id": section_id}
        ordered = sorted(view.entities("Section"), key=lambda s: (s["nominal_label"], s["actual_width_m"], s["actual_depth_m"], s["id"]))
        role = data.draw(st.sampled_from(["POST", "BEAM", "SILL", "FLOOR_JOIST", "PRINCIPAL_RAFTER", "PURLIN", "KNEE_BRACE"]))
        return "SetMemberSection", {"role": role, "section_id": data.draw(st.sampled_from([s["id"] for s in ordered]))}
    if kind == "connection_type":  # CONN-001 §8: any class and type, so disallowed pairs are drawn too
        if branch("the class's other allowed type"):  # D054: each class allows its default and one alternative
            junction_class = data.draw(st.sampled_from(JUNCTION_CLASSES))
            current = view.one("FrameSystem")["connection_defaults"][junction_class]
            other = ALTERNATIVES[junction_class] if current == DEFAULTS[junction_class] else DEFAULTS[junction_class]
            return "SetConnectionType", {"junction_class": junction_class, "connection_type": other}
        return "SetConnectionType", {
            "junction_class": data.draw(st.sampled_from(JUNCTION_CLASSES)),
            "connection_type": data.draw(st.sampled_from(CONNECTION_TYPES)),
        }
    return "UndoToRevision", {"target_revision_id": data.draw(st.sampled_from(history))}


# --- the outcome gate (TEST-002 §7) ------------------------------------------------------------

OUTCOMES: set[tuple[str, str]] = set()  # (command type, "accepted" | "rejected" | "no-op" | "impacts N"), filled by the test body
COMMAND_TYPES = {
    "SetFootprintDimensions", "SetStoryHeights", "SetGableRoofParameters", "SetTimberGrid", "SetFrameParameters", "AddSection",
    "SetMemberSection", "SetConnectionType", "UndoToRevision",
}
NEVER_REJECTED = {"SetMemberSection", "UndoToRevision"}  # their draws pick only existing sections and revisions
REQUIRED_IMPACTS = {"SetFrameParameters": {2}, "SetMemberSection": {2}, "SetGableRoofParameters": {2, 3}, "SetTimberGrid": {3}, "AddSection": {0}}


def outcome(type_: str, result: str) -> None:
    event(f"{type_}: {result}")
    OUTCOMES.add((type_, result))


def missing_outcomes(outcomes: set[tuple[str, str]]) -> list[str]:
    required = {(t, "accepted") for t in COMMAND_TYPES}
    required |= {(t, "rejected") for t in COMMAND_TYPES - NEVER_REJECTED}
    required |= {(t, f"impacts {n}") for t, sizes in REQUIRED_IMPACTS.items() for n in sizes}
    return sorted(f"{t}: {r}" for t, r in required - outcomes)


def _is_ci_profile() -> bool:
    current, ci = settings(), settings.get_profile("ci")
    return (current.max_examples, current.derandomize) == (ci.max_examples, ci.derandomize)


@pytest.fixture(scope="module")
def outcome_gate(request):
    """Under the derandomized `ci` profile, the 40 sequences must reach every outcome above. Deterministic:
    it fails only when a change to the draw or the code changes what they reach, which needs review."""
    OUTCOMES.clear()
    failed_before = request.session.testsfailed
    yield
    if not _is_ci_profile() or request.session.testsfailed > failed_before:  # a failed run reaches less, and says so already
        return
    missing = missing_outcomes(OUTCOMES)
    assert not missing, f"the `ci` sequences no longer reach: {missing}; review the draw (TEST-002 §7)"


def test_outcome_gate_names_every_missing_outcome():
    everything = {(t, r) for t in COMMAND_TYPES for r in ("accepted", "rejected")} | {
        (t, f"impacts {n}") for t, sizes in REQUIRED_IMPACTS.items() for n in sizes
    }
    assert missing_outcomes(everything) == []
    assert missing_outcomes(everything - {("SetFrameParameters", "impacts 2"), ("AddSection", "rejected")}) == [
        "AddSection: rejected", "SetFrameParameters: impacts 2",
    ]
    assert "UndoToRevision: rejected" not in missing_outcomes(set())


@settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large], deadline=None)
@given(data=st.data(), steps=st.integers(1, 8))
def test_random_command_sequences_keep_every_invariant(outcome_gate, data, steps):
    # Fixed IDs: minted IDs (and so entity order) must not differ between runs of one example.
    api = make_api(MemoryStore(), project_id_factory=lambda: PROJECT_ID)
    created = api.post("/api/v1/projects", {"command_id": str(uuid.uuid5(_NS, "create")), "type": "CreateReferenceProject", "args": {}})
    pid = created.json()["project_id"]
    view = check_revision(api, pid, api.head(pid))
    history = [view.revision_id]
    last = None  # the previous accepted command's type
    for step in range(steps):
        api.clock.now += timedelta(minutes=1)
        type_, args = draw_command(data, view, history, last)
        command = {"command_id": str(uuid.uuid5(_NS, f"step-{step}")), "project_id": pid, "base_revision_id": view.revision_id, "type": type_, "args": args}
        before = project_state(api, pid)
        preview = api.preview(pid, command)
        if preview.status_code != 200:
            assert preview.status_code == 422, (type_, args, preview.text)
            event(f"{type_}: rejected ({preview.json()['error']['code']})")
            OUTCOMES.add((type_, "rejected"))
            assert_unchanged(before, project_state(api, pid))
            continue
        commit = api.commit(pid, command, preview.json()["preview_token"])
        assert commit.status_code in (200, 201), (type_, args, commit.text)  # 200: a no-op (D045)
        body = commit.json()
        outcome(type_, "no-op" if body["is_noop"] else "accepted")
        if body["is_noop"]:
            assert preview.json()["impacted_artifacts"] == []  # D045: equal snapshots, equal fingerprints
            assert_unchanged(before, project_state(api, pid))
            continue
        after = check_revision(api, pid, body["revision_id"])
        check_transition(view, after, preserve_ids=type_ != "UndoToRevision")
        impacted = preview.json()["impacted_artifacts"]
        check_impact(view, after, impacted)  # AC2-04, DEP-001 §10
        outcome(type_, f"impacts {len(impacted)}")
        view = after
        history.append(view.revision_id)
        last = type_
