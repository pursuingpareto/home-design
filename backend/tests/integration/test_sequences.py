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
class's other allowed type; a draw of its own re-identifies one grid line; and two steps in three are a
targeted edit, one per outcome the gate requires (`draw_targeted`), chosen from a hash of the current house
(`target_for`).
The four wall commands (TEST-003 §7) are drawn from the current walls and openings: AddOpening (a window that
fits, or anywhere), SetOpening (one field changed), RemoveOpening (sometimes an ID the house no longer holds), and
SetWallAssembly (sometimes a Section's ID). A per-sequence queue (`FOLLOW_UPS`) makes the edits that need a
particular house right after the command that makes it, for example a window in the wall an accepted
RemoveOpening emptied, or shorter braces after a switch to stud infill (impact 5). Every accepted step also checks
that walls and wall framing keep their IDs and that no opening moves silently (`check_transition` with the
command). The sequences draw without Hypothesis's local constants (`no_local_constants`), so they draw the same
inside the full suite as alone (TEST-003 §17).
Profiles (conftest.py): `ci` (default, derandomized, 40 sequences) and `thorough` (500). Under `ci`, an
outcome gate checks that the sequences still reach every VS-02 and VS-02b outcome (TEST-002 §7, TEST-003 §7.4).
"""

from __future__ import annotations

import hashlib
import json
import math
import uuid
from contextlib import contextmanager
from datetime import timedelta
from typing import Any, Iterator

import pytest
from hypothesis import HealthCheck, currently_in_test_context, event, given, settings
from hypothesis import strategies as st
from hypothesis.internal.floats import float_to_int
from sortedcontainers import SortedSet

from api_support import make_api
from homedesign.model.connections import ALTERNATIVES, CONNECTION_TYPES, DEFAULTS, JUNCTION_CLASSES
from homedesign.project import MemoryStore
from integration.invariants import RevisionView, assert_unchanged, check_impact, check_revision, check_transition, project_state
from conftest import FIXTURE

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
    "member_section", "connection_type", "undo", "add_opening", "set_opening", "remove_opening", "wall_assembly",
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
# TEST-003 §7.2: the wall commands' outcomes. Drawn uniformly per step, as before, 27 targets were not all reached by
# 40 short sequences; a per-sequence theme or offset was no better, because Hypothesis builds examples by mutating
# earlier ones, so their first choices repeat. The house does differ between sequences after their first steps, so a
# targeted step takes its target from a hash of the current house's entities plus a drawn integer. That is
# deterministic and replays exactly, since the house is a function of the drawn data.
WALL_TARGETS = [
    "opening added", "opening sill only", "opening overlapping", "opening height only", "opening too wide", "opening narrowed",
    "opening removed", "opening offset only", "opening already removed", "wall assembly switched", "wall assembly wrong kind",
    "brace leg on stud infill",
]
ALL_TARGETS = TARGETS + WALL_TARGETS


def _rounded(value: Any) -> Any:
    """Floats rounded to 1e-6, so the hash does not depend on last-bit differences between platforms' math libraries
    (TEST-003 §4: the largest frame's bytes differ between this machine and CI)."""
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, dict):
        return {k: _rounded(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_rounded(v) for v in value]
    return value


def target_for(data: st.DataObject, view: RevisionView) -> str:
    state = hashlib.sha256(json.dumps(_rounded(view.snapshot["entities"]), sort_keys=True).encode()).digest()
    return ALL_TARGETS[(int.from_bytes(state[:8], "big") + data.draw(st.integers(0, len(ALL_TARGETS) - 1), label="target")) % len(ALL_TARGETS)]


# --- the wall commands (TEST-003 §7.2) ---------------------------------------------------------

UNKNOWN_OPENING = "00000000-0000-4000-8000-00000000dead"


def _walls(view: RevisionView) -> list[dict[str, Any]]:
    return sorted(view.entities("Wall"), key=lambda w: w["generation_key"])


def _openings(view: RevisionView) -> list[dict[str, Any]]:
    return sorted(view.entities("Opening"), key=lambda o: o["id"])


def _wall_length(wall: dict[str, Any]) -> float:
    return math.dist(wall["start_m"][:2], wall["end_m"][:2])


def _opening_args(opening: dict[str, Any], **changes: float) -> dict[str, Any]:
    fields = ("width_m", "height_m", "sill_height_m", "offset_m")
    return {"opening_id": opening["id"], **{f: opening[f] for f in fields}, **changes}


def _centered_window(wall: dict[str, Any]) -> dict[str, Any]:
    """D072's 3' × 4' window, sill 3', centered: it fits every bay of 8'-9" or more (D076)."""
    return {"wall_id": wall["id"], "opening_kind": "WINDOW", "width_m": 3 * FT, "height_m": 4 * FT, "sill_height_m": 3 * FT,
            "offset_m": (_wall_length(wall) - 3 * FT) / 2}


def _new_window(view: RevisionView, wall: dict[str, Any] | None = None) -> dict[str, Any]:
    """A window that fits: centered in an empty wall, or, when every wall has an opening (the created house), a
    1' × 1' window low in the wall, 6" from its start post, clear of a centered window and of the braces."""
    occupied = {o["wall_id"] for o in view.entities("Opening")}
    if wall is None:
        empty = [w for w in _walls(view) if w["id"] not in occupied]
        wall = empty[0] if empty else _walls(view)[0]
    if wall["id"] not in occupied:
        return _centered_window(wall)
    return {"wall_id": wall["id"], "opening_kind": "WINDOW", "width_m": 1 * FT, "height_m": 1 * FT, "sill_height_m": 1 * FT, "offset_m": 0.5 * FT}


def _nudge(data: st.DataObject, lo: float, hi: float) -> float:
    """A change of size lo to hi, either way. Never 0: Hypothesis shrinks floats toward 0, which would be a no-op."""
    return data.draw(st.floats(lo, hi, allow_nan=False, allow_infinity=False)) * (1 if data.draw(st.booleans()) else -1)


def _other_definition(view: RevisionView) -> str:
    current = view.one("WallSystem")["default_assembly_definition_id"]
    return next(d["id"] for d in sorted(view.entities("AssemblyDefinition"), key=lambda d: d["label"]) if d["id"] != current)


def draw_wall_targeted(data: st.DataObject, view: RevisionView, target: str, stale: list[str]) -> tuple[str, dict[str, Any]]:
    small = lambda lo, hi: data.draw(st.floats(lo, hi, allow_nan=False, allow_infinity=False))  # noqa: E731
    openings, windows = _openings(view), [o for o in _openings(view) if o["opening_kind"] == "WINDOW"]
    if target == "opening added":
        return "AddOpening", _new_window(view, data.draw(st.sampled_from(_walls(view))))
    if target in ("opening added", "opening overlapping") or not openings:
        if target == "opening overlapping" and openings:  # the same rectangle as an existing opening: OPENINGS_OVERLAP
            existing = data.draw(st.sampled_from(openings))
            return "AddOpening", {"wall_id": existing["wall_id"], "opening_kind": "WINDOW", "width_m": existing["width_m"],
                                  "height_m": existing["height_m"], "sill_height_m": max(existing["sill_height_m"], 1 * FT), "offset_m": existing["offset_m"]}
        return "AddOpening", _new_window(view)
    opening = data.draw(st.sampled_from(openings))
    if target == "opening offset only":  # within 3": the view and schedule change, the estimate only if a sum's last bit does
        return "SetOpening", _opening_args(opening, offset_m=opening["offset_m"] + _nudge(data, 1 / 12 * FT, 0.25 * FT))
    if target == "opening sill only" and windows:  # the window moves up or down 3" at most: mesh and schedule (impact 2)
        window = data.draw(st.sampled_from(windows))
        return "SetOpening", _opening_args(window, sill_height_m=window["sill_height_m"] + _nudge(data, 1 / 12 * FT, 0.25 * FT))
    if target == "opening height only":  # shorter by up to 6": the plan is unchanged (impact 3)
        return "SetOpening", _opening_args(opening, height_m=opening["height_m"] - small(1 / 12 * FT, 0.5 * FT))
    if target == "opening narrowed":  # narrower by up to 6" (impact 4)
        return "SetOpening", _opening_args(opening, width_m=opening["width_m"] - small(1 / 12 * FT, 0.5 * FT))
    if target == "opening too wide":  # as wide as its wall: OPENING_OUTSIDE_WALL
        wall = next(w for w in view.entities("Wall") if w["id"] == opening["wall_id"])
        return "SetOpening", _opening_args(opening, width_m=_wall_length(wall), offset_m=0.0)
    if target == "opening removed":
        return "RemoveOpening", {"opening_id": opening["id"]}
    if target == "opening already removed":  # DANGLING_REFERENCE
        return "RemoveOpening", {"opening_id": data.draw(st.sampled_from(stale)) if stale else UNKNOWN_OPENING}
    if target == "brace leg on stud infill":  # impact 5 on stud infill; otherwise the switch, which queues it (FOLLOW_UPS)
        return shorter_braces(data, view) if _is_stud_infill(view) else ("SetWallAssembly", {"assembly_definition_id": _other_definition(view)})
    if target == "wall assembly wrong kind":  # WRONG_REFERENCE_KIND
        return "SetWallAssembly", {"assembly_definition_id": sorted(s["id"] for s in view.entities("Section"))[0]}
    return "SetWallAssembly", {"assembly_definition_id": _other_definition(view)}


def draw_wall_command(data: st.DataObject, view: RevisionView, kind: str, stale: list[str]) -> tuple[str, dict[str, Any]]:
    """The four wall commands, drawn inside and outside what fits (TEST-003 §7.2)."""
    length = lambda lo, hi: data.draw(st.floats(lo, hi, allow_nan=False, allow_infinity=False))  # noqa: E731
    branch = lambda label: data.draw(st.booleans(), label=label)  # noqa: E731
    if kind == "add_opening":
        wall = data.draw(st.sampled_from(_walls(view)))
        if branch("a window that fits"):
            return "AddOpening", _new_window(view, wall)
        opening_kind = data.draw(st.sampled_from(["WINDOW", "DOOR"]))
        sill = 0.0 if opening_kind == "DOOR" and branch("door at 0") else length(0.0, 6 * FT)
        return "AddOpening", {"wall_id": wall["id"], "opening_kind": opening_kind, "width_m": length(1 * FT, 8 * FT), "height_m": length(1 * FT, 8 * FT),
                              "sill_height_m": sill, "offset_m": length(-1 * FT, _wall_length(wall))}
    if kind == "set_opening" and _openings(view):
        opening = data.draw(st.sampled_from(_openings(view)))
        field = data.draw(st.sampled_from(["width_m", "height_m", "sill_height_m", "offset_m"]))
        value = opening[field] + length(-1 * FT, 1 * FT) if branch("within a foot") else length(-1 * FT, 9 * FT)
        return "SetOpening", _opening_args(opening, **{field: value})
    if kind == "remove_opening" and _openings(view) and not branch("a stale ID"):
        return "RemoveOpening", {"opening_id": data.draw(st.sampled_from(_openings(view)))["id"]}
    if kind == "remove_opening":
        return "RemoveOpening", {"opening_id": data.draw(st.sampled_from(stale)) if stale else UNKNOWN_OPENING}
    if kind == "wall_assembly" and data.draw(st.integers(0, 3)) == 0:
        return "SetWallAssembly", {"assembly_definition_id": sorted(s["id"] for s in view.entities("Section"))[0]}
    return "SetWallAssembly", {"assembly_definition_id": _other_definition(view)}


def draw_targeted(data: st.DataObject, view: RevisionView, history: list[str], stale: list[str] = (), target: str | None = None) -> tuple[str, dict[str, Any]]:
    target = target or target_for(data, view)
    event(f"draw: {target} (targeted)")
    if target.startswith(("opening", "wall assembly")):
        return draw_wall_targeted(data, view, target, list(stale))
    length = lambda lo, hi: data.draw(st.floats(lo, hi, allow_nan=False, allow_infinity=False))  # noqa: E731
    footprint, roof = view.one("Footprint"), view.one("GableRoof")
    frame = view.one("FrameSystem")
    if target == "footprint accepted":  # up to 3% wider: the bays stay supported, and every opening still fits (TEST-003 §7.2)
        width = min(footprint["width_m"] * length(1.001, 1.03), 80 * FT)
        return "SetFootprintDimensions", {"width_m": width, "depth_m": footprint["depth_m"]}
    if target == "footprint rejected":
        return "SetFootprintDimensions", {"width_m": length(81 * FT, 100 * FT), "depth_m": footprint["depth_m"]}
    if target == "stories accepted":  # D034: 8'–14'; taller only, so every opening and girt still fits (TEST-003 §7.2)
        current = [level["story_height_m"] for level in sorted(view.entities("Level"), key=lambda level: level["index"])][:2]
        return "SetStoryHeights", {"story_heights_m": [length(min(h + 0.01, 13.5 * FT), 13.5 * FT) for h in current]}
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


def _is_stud_infill(view: RevisionView) -> bool:
    current = view.one("WallSystem")["default_assembly_definition_id"]
    return next(d["family"] for d in view.entities("AssemblyDefinition") if d["id"] == current) == "STUD_INFILL"


# Follow-ups (TEST-003 §7.2): outcomes that need a particular house, queued after the accepted command that makes it.
# Queued steps run first, in order, so the most important come first when the sequence ends early.
FOLLOW_UPS = {
    # After a removal there is an empty wall, so a window fits there (AddOpening accepted, impact 4); then an opening
    # as wide as its wall (SetOpening rejected, fit), the removed opening's ID again (RemoveOpening rejected), an
    # overlap (AddOpening rejected, fit), a sill move (SetOpening impact 2), and a shorter opening (impact 3).
    "RemoveOpening": ["add to an empty wall", "opening too wide", "opening already removed", "opening overlapping", "opening sill only", "opening height only"],
    # An undo is accepted only with an earlier revision to return to, which a targeted draw early in a short sequence
    # often lacks.
    "SetGableRoofParameters": ["undo the last revision"],
    # On stud infill, studs and kings end on the braces (D066), so a brace-leg edit moves wall framing: impact 5
    # (ART-003 §8.3). Shorter legs only shrink the braces' reach, so the fit still holds.
    "SetWallAssembly": ["shorter braces on stud infill"],
    # A joist spacing within 10% above the stored one keeps the joist count (impact 2, DEP-001 §8); one target among
    # 28 was missed, so it also follows two frequent frame edits.
    "SetConnectionType": ["joist spacing keeping the count"],
    "SetMemberSection": ["joist spacing keeping the count"],
}


def shorter_braces(data: st.DataObject, view: RevisionView) -> tuple[str, dict[str, Any]]:
    parameters = view.one("FrameSystem")["parameters"]
    leg = parameters["knee_brace_leg_m"]
    shorter = data.draw(st.floats(max(1.5 * FT, leg - 0.5 * FT), max(1.5 * FT, leg - 1 / 12 * FT)))
    return "SetFrameParameters", {**parameters, "knee_brace_leg_m": shorter}


def draw_follow_up(data: st.DataObject, view: RevisionView, history: list[str], name: str, stale: list[str]) -> tuple[str, dict[str, Any]] | None:
    event(f"draw: {name} (follow-up)")
    if name == "add to an empty wall":
        return "AddOpening", _new_window(view)
    if name == "undo the last revision":
        return ("UndoToRevision", {"target_revision_id": history[-2]}) if len(history) > 1 else None
    if name == "shorter braces on stud infill":
        return shorter_braces(data, view) if _is_stud_infill(view) else None
    if name in TARGETS:
        return draw_targeted(data, view, history, stale, target=name)
    return draw_wall_targeted(data, view, name, stale)


def draw_command(data: st.DataObject, view: RevisionView, history: list[str], last: str | None = None, stale: list[str] = (),
                 follow_ups: list[str] | None = None) -> tuple[str, dict[str, Any]]:
    """One command for the step after `view`. `last` is the type of the previous accepted command; `stale` lists
    opening IDs earlier revisions held and this one does not; `follow_ups` is the sequence's queue of FOLLOW_UPS,
    consumed here."""
    while follow_ups:
        drawn = draw_follow_up(data, view, history, follow_ups.pop(0), list(stale))
        if drawn is not None:
            return drawn
    # The fixture has no two sections with equal dimensions, so a swap that leaves the mesh unchanged needs an
    # AddSection first: the step right after one makes the swap.
    if last == "AddSection" and same_dimension_swaps(view):
        role, section_id = data.draw(st.sampled_from(same_dimension_swaps(view)))
        return "SetMemberSection", {"role": role, "section_id": section_id}
    if data.draw(st.integers(0, 2), label="targeted") > 0:  # two steps in three (TEST-003 §7.2; TEST-002 §7 had one in two)
        return draw_targeted(data, view, history, stale)
    kind = data.draw(st.sampled_from(KINDS), label="kind")
    event(f"draw: {kind}")
    if kind in ("add_opening", "set_opening", "remove_opening", "wall_assembly"):
        return draw_wall_command(data, view, kind, list(stale))
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
    "SetMemberSection", "SetConnectionType", "UndoToRevision", "AddOpening", "SetOpening", "RemoveOpening", "SetWallAssembly",
}
NEVER_REJECTED = {"SetMemberSection", "UndoToRevision"}  # their draws pick only existing sections and revisions
# Since ART-003 every grid line names walls (D080), so an accepted grid change replaces walls and impacts all five
# artifacts; VS-02's "SetTimberGrid: impacts 3" (a re-identification only) is no longer reachable (ART-003 §8.3, §17).
# TEST-003 §7.4: SetOpening reaches 2 (sill only), 3 (height only, or offset only), and 4 (width); the brace edit after
# a switch to stud infill reaches SetFrameParameters 5.
REQUIRED_IMPACTS = {
    "SetFrameParameters": {2, 5}, "SetMemberSection": {2}, "SetGableRoofParameters": {2, 3}, "SetTimberGrid": {5}, "AddSection": {0},
    "AddOpening": {4}, "SetOpening": {2, 3, 4}, "RemoveOpening": {4}, "SetWallAssembly": {4},
}
# A rejection that names a fit code also records "rejected (fit)"; the gate requires one for the two opening commands
# and for at least one frame command (AC2b-04).
FIT_CODES = {"OPENING_OUTSIDE_WALL", "OPENING_CROSSES_BRACE", "OPENINGS_OVERLAP", "GIRT_CROSSES_BRACE"}
FRAME_COMMANDS = {"SetFootprintDimensions", "SetStoryHeights", "SetTimberGrid", "SetFrameParameters"}
REQUIRED_FIT_REJECTIONS = {"AddOpening", "SetOpening", "a frame command"}


def outcome(type_: str, result: str) -> None:
    event(f"{type_}: {result}")
    OUTCOMES.add((type_, result))


def missing_outcomes(outcomes: set[tuple[str, str]]) -> list[str]:
    required = {(t, "accepted") for t in COMMAND_TYPES}
    required |= {(t, "rejected") for t in COMMAND_TYPES - NEVER_REJECTED}
    required |= {(t, f"impacts {n}") for t, sizes in REQUIRED_IMPACTS.items() for n in sizes}
    required |= {(t, "rejected (fit)") for t in REQUIRED_FIT_REJECTIONS}
    return sorted(f"{t}: {r}" for t, r in required - outcomes)


def rejection(type_: str, error: dict[str, Any]) -> None:
    if currently_in_test_context():  # the gate's own test calls this outside a Hypothesis run
        event(f"{type_}: rejected ({error['code']})")
    OUTCOMES.add((type_, "rejected"))
    if FIT_CODES & {d["code"] for d in error.get("details", [])}:
        OUTCOMES.add((type_, "rejected (fit)"))
        if type_ in FRAME_COMMANDS:
            OUTCOMES.add(("a frame command", "rejected (fit)"))


def _is_ci_profile() -> bool:
    current, ci = settings(), settings.get_profile("ci")
    return (current.max_examples, current.derandomize) == (ci.max_examples, ci.derandomize)


@contextmanager
def no_local_constants() -> Iterator[None]:
    """Hypothesis also draws numeric literals it finds in every loaded local module (its "local constants"), so the
    same derandomized run draws differently alone and inside the full suite, which loads more modules (TEST-003 §17).
    For the gate, the sequences draw without them: what they reach then depends only on this file and the code."""
    from hypothesis.internal.conjecture import providers

    empty = providers.Constants(integers=SortedSet(), floats=SortedSet(key=float_to_int), bytes=SortedSet(), strings=SortedSet())
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(providers, "_get_local_constants", lambda: empty)
        patch.setattr(providers, "CONSTANTS_CACHE", {})  # keyed by choice type; the real one keeps constants found before
        yield


@pytest.fixture(scope="module")
def outcome_gate(request):
    """Under the derandomized `ci` profile, the 40 sequences must reach every outcome above. Deterministic:
    it fails only when a change to the draw or the code changes what they reach, which needs review."""
    OUTCOMES.clear()
    failed_before = request.session.testsfailed
    with no_local_constants():
        yield
    if not _is_ci_profile() or request.session.testsfailed > failed_before:  # a failed run reaches less, and says so already
        return
    missing = missing_outcomes(OUTCOMES)
    assert not missing, f"the `ci` sequences no longer reach: {missing}; review the draw (TEST-002 §7)"


def test_outcome_gate_names_every_missing_outcome():
    everything = {(t, r) for t in COMMAND_TYPES for r in ("accepted", "rejected")} | {
        (t, f"impacts {n}") for t, sizes in REQUIRED_IMPACTS.items() for n in sizes
    } | {(t, "rejected (fit)") for t in REQUIRED_FIT_REJECTIONS}
    assert missing_outcomes(everything) == []
    assert missing_outcomes(everything - {("SetFrameParameters", "impacts 2"), ("AddSection", "rejected")}) == [
        "AddSection: rejected", "SetFrameParameters: impacts 2",
    ]
    assert "UndoToRevision: rejected" not in missing_outcomes(set())
    # TEST-003 §7.4: the wall commands, their impacts, and the fit rejections are required.
    assert missing_outcomes(everything - {("SetWallAssembly", "rejected"), ("SetOpening", "impacts 2"), ("a frame command", "rejected (fit)")}) == [
        "SetOpening: impacts 2", "SetWallAssembly: rejected", "a frame command: rejected (fit)",
    ]
    OUTCOMES.clear()
    rejection("SetStoryHeights", {"code": "UNSUPPORTED_CONFIGURATION", "details": [{"code": "OPENING_OUTSIDE_WALL"}]})
    rejection("AddOpening", {"code": "VALIDATION_FAILED", "details": [{"code": "DANGLING_REFERENCE"}]})
    assert OUTCOMES == {("SetStoryHeights", "rejected"), ("SetStoryHeights", "rejected (fit)"), ("a frame command", "rejected (fit)"), ("AddOpening", "rejected")}
    OUTCOMES.clear()


def _view(doc: dict[str, Any]) -> RevisionView:
    return RevisionView("r", doc, b"", {})


def test_check_transition_catches_silent_wall_and_opening_changes():
    """TEST-003 §7.3: walls and wall framing keep their IDs, and no opening moves, appears, or disappears silently."""
    import copy

    before = _view(FIXTURE)
    opening = sorted(before.entities("Opening"), key=lambda o: o["id"])[0]

    def after(change) -> RevisionView:
        doc = copy.deepcopy(FIXTURE)
        change(doc)
        return _view(doc)

    def opening_of(doc):
        return next(e for e in doc["entities"] if e["id"] == opening["id"])

    command = lambda type_, **args: {"type": type_, "args": args}  # noqa: E731
    width = command("SetFootprintDimensions", width_m=1.0, depth_m=1.0)
    check_transition(before, after(lambda d: None), command=width)
    moved = after(lambda d: opening_of(d).update(offset_m=opening["offset_m"] + 0.01))
    with pytest.raises(AssertionError, match="changed silently"):
        check_transition(before, moved, command=width)
    check_transition(before, moved, command=command("SetOpening", opening_id=opening["id"]))
    rehomed = after(lambda d: opening_of(d).update(wall_id=next(e["id"] for e in d["entities"] if e["kind"] == "Wall" and e["id"] != opening["wall_id"])))
    with pytest.raises(AssertionError):
        check_transition(before, rehomed, command=command("SetOpening", opening_id=opening["id"]))
    gone = after(lambda d: d["entities"].remove(opening_of(d)))
    with pytest.raises(AssertionError, match="disappeared"):
        check_transition(before, gone, command=width)
    check_transition(before, gone, command=command("RemoveOpening", opening_id=opening["id"]))
    wall_gone = after(lambda d: [d["entities"].remove(e) for e in [opening_of(d), next(e for e in d["entities"] if e["id"] == opening["wall_id"])]])
    check_transition(before, wall_gone, command=width)  # removed with its wall (MODEL-006 §8.5)
    extra = after(lambda d: d["entities"].append({**opening_of(d), "id": "00000000-0000-4000-8000-0000000000aa"}))
    with pytest.raises(AssertionError, match="added openings"):
        check_transition(before, extra, command=width)
    check_transition(before, extra, command=command("AddOpening"))
    for kind in ("Wall", "WallFramingPiece"):
        reminted = after(lambda d: next(e for e in d["entities"] if e["kind"] == kind).update(id="00000000-0000-4000-8000-0000000000bb"))
        with pytest.raises(AssertionError, match=f"{kind} IDs changed"):
            check_transition(before, reminted)


@settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large], deadline=None)
@given(data=st.data(), steps=st.integers(4, 8))  # at least 4 steps, so each sequence reaches past its first, shared choices (TEST-003 §7.2)
def test_random_command_sequences_keep_every_invariant(outcome_gate, data, steps):
    # Fixed IDs: minted IDs (and so entity order) must not differ between runs of one example.
    api = make_api(MemoryStore(), project_id_factory=lambda: PROJECT_ID)
    created = api.post("/api/v1/projects", {"command_id": str(uuid.uuid5(_NS, "create")), "type": "CreateReferenceProject", "args": {}})
    pid = created.json()["project_id"]
    view = check_revision(api, pid, api.head(pid))
    history = [view.revision_id]
    last = None  # the previous accepted command's type
    seen_openings = {o["id"] for o in view.entities("Opening")}  # every opening ID a revision of this sequence held
    follow_ups: list[str] = []
    for step in range(steps):
        api.clock.now += timedelta(minutes=1)
        stale = sorted(seen_openings - {o["id"] for o in view.entities("Opening")})
        type_, args = draw_command(data, view, history, last, stale, follow_ups)
        command = {"command_id": str(uuid.uuid5(_NS, f"step-{step}")), "project_id": pid, "base_revision_id": view.revision_id, "type": type_, "args": args}
        before = project_state(api, pid)
        preview = api.preview(pid, command)
        if preview.status_code != 200:
            assert preview.status_code == 422, (type_, args, preview.text)
            rejection(type_, preview.json()["error"])
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
        check_transition(view, after, preserve_ids=type_ != "UndoToRevision", command=command)
        impacted = preview.json()["impacted_artifacts"]
        check_impact(view, after, impacted)  # AC2-04, DEP-001 §10
        outcome(type_, f"impacts {len(impacted)}")
        view = after
        history.append(view.revision_id)
        seen_openings |= {o["id"] for o in view.entities("Opening")}
        follow_ups[:0] = FOLLOW_UPS.get(type_, [])
        last = type_
