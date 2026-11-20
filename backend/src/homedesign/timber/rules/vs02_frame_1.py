"""Rule ``vs02-frame-1`` (generation-rules.md; TIMBER-002 §5; D052, D058).

Generates posts, beams, sills, floor joists, principal rafters, purlins, and knee braces.
Every reference axis lies on a datum (D058). Not a structural design procedure.

Numeric evaluation (generation-rules.md "Numeric evaluation"): coordinates are IEEE-754
doubles evaluated exactly as written, left to right, with no rounding or snapping. Only
values derived from tan(pitch_rad) may differ across implementations, within 1e-12 m.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from homedesign.model.connections import JUNCTION_CLASSES

from ..inventory import GeneratedConnection, GeneratedMember

if TYPE_CHECKING:
    from homedesign.model.schema import Snapshot

VERSION = "vs02-frame-1"
GENERATED_ROLES = frozenset({"POST", "BEAM", "SILL", "FLOOR_JOIST", "PRINCIPAL_RAFTER", "PURLIN", "KNEE_BRACE"})
# Declared from the start so projects carry the D054 defaults; connections arrive with CONN-001.
GENERATED_JUNCTION_CLASSES = frozenset(JUNCTION_CLASSES)
EPSILON_M = 1e-6  # D026; also the joist "not on a line" test (TIMBER-002 §5.2)


def _utf16(text: str) -> bytes:
    return text.encode("utf-16-be")


class _Inputs:
    """The inputs the rule reads, resolved from a snapshot that passed stages 1–4."""

    def __init__(self, snapshot: "Snapshot") -> None:
        by_id: dict[str, Any] = {}
        for entity in snapshot.entities:
            by_id.setdefault(entity.id, entity)
        building = snapshot.building
        self.footprint = by_id[building.footprint_id]
        self.levels = [by_id[level_id] for level_id in building.level_ids]
        self.roof = by_id[building.roof_id]
        self.frame = by_id[building.frame_system_id]
        self.grid = by_id[self.frame.grid_id]
        self.defaults = self.frame.member_defaults
        self.parameters = self.frame.parameters


def generate(snapshot: "Snapshot") -> tuple[GeneratedMember, ...]:
    """All members the rule defines, sorted by generation_key (code-unit order).

    Defined only for snapshots that pass validation stages 1–4.
    """
    p = _Inputs(snapshot)
    fp = p.footprint
    params = p.parameters
    # Evaluated exactly as written: origin + (length * fraction).
    xs = [(line.id, fp.origin_m[0] + fp.width_m * line.fraction) for line in p.grid.x_lines]
    ys = [(line.id, fp.origin_m[1] + fp.depth_m * line.fraction) for line in p.grid.y_lines]
    level0, level1 = p.levels
    z0 = level0.elevation_m
    z1 = level1.elevation_m
    z_eave = level1.elevation_m + level1.story_height_m
    y_s = fp.origin_m[1]
    y_n = fp.origin_m[1] + fp.depth_m
    y_ridge = fp.origin_m[1] + fp.depth_m / 2
    t = math.tan(p.roof.pitch_rad)  # once per snapshot
    z_ridge = z_eave + (fp.depth_m / 2) * t  # D048

    members: list[GeneratedMember] = []

    def add(key: str, role: str, start: tuple[float, float, float], end: tuple[float, float, float]) -> None:
        default = p.defaults[role]
        members.append(GeneratedMember(key, role, start, end, default.section_id, default.material_id))

    # Posts at every station, both stories.
    for x_id, x in xs:
        for y_id, y in ys:
            add(f"frame/{x_id}/{y_id}/level-0/post", "POST", (x, y, z0), (x, y, z1))
            add(f"frame/{x_id}/{y_id}/level-1/post", "POST", (x, y, z1), (x, y, z_eave))

    # Bay-lines on a plane: (key prefix, start, end), the same for sills, beams, and braces.
    def bay_lines(plane: str, z: float) -> list[tuple[str, str, str, tuple[float, float, float], tuple[float, float, float], str]]:
        lines = []
        for y_id, y in ys:
            for (xa_id, xa), (xb_id, xb) in zip(xs, xs[1:]):
                lines.append((f"frame/axis-x/{y_id}/{xa_id}-{xb_id}/{plane}", xa_id, xb_id, (xa, y, z), (xb, y, z), "x"))
        for x_id, x in xs:
            for (ya_id, ya), (yb_id, yb) in zip(ys, ys[1:]):
                lines.append((f"frame/axis-y/{x_id}/{ya_id}-{yb_id}/{plane}", ya_id, yb_id, (x, ya, z), (x, yb, z), "y"))
        return lines

    for prefix, _, _, start, end, _ in bay_lines("plane-L0", z0):
        add(f"{prefix}/sill", "SILL", start, end)

    braced = {"plane-L1": params.knee_braces_level_1, "plane-eave": params.knee_braces_eave}
    leg = params.knee_brace_leg_m
    for plane, z in (("plane-L1", z1), ("plane-eave", z_eave)):
        for prefix, a_id, b_id, start, end, axis in bay_lines(plane, z):
            add(f"{prefix}/beam", "BEAM", start, end)
            if not braced[plane]:
                continue
            # From the post (one leg below the plane) to the beam (one leg along it), at 45°.
            if axis == "x":
                (xa, y, _), (xb, _, _) = start, end
                add(f"{prefix}/brace/{a_id}", "KNEE_BRACE", (xa, y, z - leg), (xa + leg, y, z))
                add(f"{prefix}/brace/{b_id}", "KNEE_BRACE", (xb, y, z - leg), (xb - leg, y, z))
            else:
                (x, ya, _), (_, yb, _) = start, end
                add(f"{prefix}/brace/{a_id}", "KNEE_BRACE", (x, ya, z - leg), (x, ya + leg, z))
                add(f"{prefix}/brace/{b_id}", "KNEE_BRACE", (x, yb, z - leg), (x, yb - leg, z))

    # Floor joists: Level 1 only, spanning Y within each X bay, never on a beam line.
    spacing = params.joist_spacing_m
    for (xa_id, xa), (xb_id, xb) in zip(xs, xs[1:]):
        positions = []
        k = 1
        while xa + k * spacing < xb - EPSILON_M:
            positions.append((k, xa + k * spacing))
            k += 1
        for (ya_id, ya), (yb_id, yb) in zip(ys, ys[1:]):
            for k, xk in positions:
                add(f"frame/axis-y/{xa_id}-{xb_id}/j{k}/{ya_id}-{yb_id}/plane-L1/joist", "FLOOR_JOIST", (xk, ya, z1), (xk, yb, z1))

    # Principal rafters: a pair per X line, from the wall line at the eave plate to the ridge.
    for x_id, x in xs:
        add(f"frame/roof/{x_id}/south/principal-rafter", "PRINCIPAL_RAFTER", (x, y_s, z_eave), (x, y_ridge, z_ridge))
        add(f"frame/roof/{x_id}/north/principal-rafter", "PRINCIPAL_RAFTER", (x, y_n, z_eave), (x, y_ridge, z_ridge))

    # Purlins: n per slope in each X bay, at i / (n + 1) of the rafter from the eave.
    n = params.purlins_per_slope
    for slope, y_e in (("south", y_s), ("north", y_n)):
        for i in range(1, n + 1):
            f = i / (n + 1)
            yi = y_e + (y_ridge - y_e) * f
            zi = z_eave + (z_ridge - z_eave) * f
            for (xa_id, xa), (xb_id, xb) in zip(xs, xs[1:]):
                add(f"frame/roof/{xa_id}-{xb_id}/{slope}/p{i}/purlin", "PURLIN", (xa, yi, zi), (xb, yi, zi))

    return tuple(sorted(members, key=lambda m: _utf16(m.generation_key)))


def generate_connections(snapshot: "Snapshot") -> tuple[GeneratedConnection, ...]:
    """No connections until CONN-001 (MODEL-005 §6.5)."""
    return ()


from . import Rule, register  # noqa: E402

register(Rule(VERSION, GENERATED_ROLES, GENERATED_JUNCTION_CLASSES, generate, generate_connections))
