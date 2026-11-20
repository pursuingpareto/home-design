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


Point = tuple[float, float, float]


def _post_key(x_id: str, y_id: str, level: str) -> str:
    return f"frame/{x_id}/{y_id}/{level}/post"


def _bay_key(axis: str, line_id: str, a_id: str, b_id: str, plane: str) -> str:
    """Key prefix of the sill, beam, or brace in one bay of one grid line on a plane."""
    return f"frame/axis-{axis}/{line_id}/{a_id}-{b_id}/{plane}"


def _rafter_key(x_id: str, slope: str) -> str:
    return f"frame/roof/{x_id}/{slope}/principal-rafter"


# "The post below" a plane (CONN-001 §4.2, D059).
_POST_BELOW = {"plane-L1": "level-0", "plane-eave": "level-1"}


def _build(snapshot: "Snapshot") -> tuple[tuple[GeneratedMember, ...], tuple[GeneratedConnection, ...]]:
    """Members and connections in one pass (CONN-001 §9).

    A receiving member's key is built from the same variables as that member's own key, so
    no key is ever parsed. A connection's ``location_m`` is the entering member's endpoint,
    the same tuple object, so it is bit-identical by construction (CONN-001 §4.2).
    """
    p = _Inputs(snapshot)
    fp = p.footprint
    params = p.parameters
    types = p.frame.connection_defaults
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
    connections: list[GeneratedConnection] = []

    def add(key: str, role: str, start: Point, end: Point) -> None:
        default = p.defaults[role]
        members.append(GeneratedMember(key, role, start, end, default.section_id, default.material_id))

    def join(junction_class: str, receiving: str, entering: str, location: Point) -> None:
        connections.append(GeneratedConnection(
            f"connection/{junction_class}/{receiving}/{entering}", junction_class, types[junction_class], (receiving, entering), location,
        ))

    # Posts at every station, both stories. A Level 0 post's foot enters the Y sill in its
    # bent: the bay that starts at its Y line, or, on the last line, the bay that ends there.
    y_bays = list(zip(ys, ys[1:]))
    for x_id, x in xs:
        for j, (y_id, y) in enumerate(ys):
            foot = (x, y, z0)
            add(_post_key(x_id, y_id, "level-0"), "POST", foot, (x, y, z1))
            add(_post_key(x_id, y_id, "level-1"), "POST", (x, y, z1), (x, y, z_eave))
            (ya_id, _), (yb_id, _) = y_bays[min(j, len(y_bays) - 1)]
            join("post-sill", _bay_key("y", x_id, ya_id, yb_id, "plane-L0") + "/sill", _post_key(x_id, y_id, "level-0"), foot)

    # Bay-lines on a plane, the same for sills, beams, and braces: (key prefix, start line,
    # end line, start, end, axis, start station, end station). Stations are (x id, y id).
    def bay_lines(plane: str, z: float) -> list[tuple[str, str, str, Point, Point, str, tuple[str, str], tuple[str, str]]]:
        lines = []
        for y_id, y in ys:
            for (xa_id, xa), (xb_id, xb) in zip(xs, xs[1:]):
                lines.append((_bay_key("x", y_id, xa_id, xb_id, plane), xa_id, xb_id, (xa, y, z), (xb, y, z), "x", (xa_id, y_id), (xb_id, y_id)))
        for x_id, x in xs:
            for (ya_id, ya), (yb_id, yb) in y_bays:
                lines.append((_bay_key("y", x_id, ya_id, yb_id, plane), ya_id, yb_id, (x, ya, z), (x, yb, z), "y", (x_id, ya_id), (x_id, yb_id)))
        return lines

    for prefix, _, _, start, end, _, _, _ in bay_lines("plane-L0", z0):
        add(f"{prefix}/sill", "SILL", start, end)

    braced = {"plane-L1": params.knee_braces_level_1, "plane-eave": params.knee_braces_eave}
    leg = params.knee_brace_leg_m
    for plane, z in (("plane-L1", z1), ("plane-eave", z_eave)):
        below = _POST_BELOW[plane]
        for prefix, a_id, b_id, start, end, axis, a_station, b_station in bay_lines(plane, z):
            beam = f"{prefix}/beam"
            add(beam, "BEAM", start, end)
            post_a, post_b = _post_key(*a_station, below), _post_key(*b_station, below)
            join("post-beam", post_a, beam, start)
            join("post-beam", post_b, beam, end)
            if not braced[plane]:
                continue
            # From the post (one leg below the plane) to the beam (one leg along it), at 45°.
            if axis == "x":
                (xa, y, _), (xb, _, _) = start, end
                braces = (((xa, y, z - leg), (xa + leg, y, z), a_id, post_a), ((xb, y, z - leg), (xb - leg, y, z), b_id, post_b))
            else:
                (x, ya, _), (_, yb, _) = start, end
                braces = (((x, ya, z - leg), (x, ya + leg, z), a_id, post_a), ((x, yb, z - leg), (x, yb - leg, z), b_id, post_b))
            for lower, upper, line_id, post in braces:
                brace = f"{prefix}/brace/{line_id}"
                add(brace, "KNEE_BRACE", lower, upper)
                join("brace", post, brace, lower)
                join("brace", beam, brace, upper)

    # Floor joists: Level 1 only, spanning Y within each X bay, never on a beam line. Each end
    # enters the X-direction Level 1 beam on its Y line, in the joist's X bay.
    spacing = params.joist_spacing_m
    for (xa_id, xa), (xb_id, xb) in zip(xs, xs[1:]):
        positions = []
        k = 1
        while xa + k * spacing < xb - EPSILON_M:
            positions.append((k, xa + k * spacing))
            k += 1
        for (ya_id, ya), (yb_id, yb) in y_bays:
            for k, xk in positions:
                joist = f"frame/axis-y/{xa_id}-{xb_id}/j{k}/{ya_id}-{yb_id}/plane-L1/joist"
                start, end = (xk, ya, z1), (xk, yb, z1)
                add(joist, "FLOOR_JOIST", start, end)
                join("joist-beam", _bay_key("x", ya_id, xa_id, xb_id, "plane-L1") + "/beam", joist, start)
                join("joist-beam", _bay_key("x", yb_id, xa_id, xb_id, "plane-L1") + "/beam", joist, end)

    # Principal rafters: a pair per X line, from the wall line at the eave plate to the ridge.
    # Each foot enters its bent's tie beam; at the peak the north rafter enters the south.
    (y0_id, _), (y1_id, _) = y_bays[0]
    (ym_id, _), (yn_id, _) = y_bays[-1]
    for x_id, x in xs:
        south, north = _rafter_key(x_id, "south"), _rafter_key(x_id, "north")
        south_foot, north_foot, north_top = (x, y_s, z_eave), (x, y_n, z_eave), (x, y_ridge, z_ridge)
        add(south, "PRINCIPAL_RAFTER", south_foot, (x, y_ridge, z_ridge))
        add(north, "PRINCIPAL_RAFTER", north_foot, north_top)
        join("rafter-peak", south, north, north_top)
        join("rafter-foot", _bay_key("y", x_id, y0_id, y1_id, "plane-eave") + "/beam", south, south_foot)
        join("rafter-foot", _bay_key("y", x_id, ym_id, yn_id, "plane-eave") + "/beam", north, north_foot)

    # Purlins: n per slope in each X bay, at i / (n + 1) of the rafter from the eave. Each end
    # enters the principal rafter on its X line and slope.
    n = params.purlins_per_slope
    for slope, y_e in (("south", y_s), ("north", y_n)):
        for i in range(1, n + 1):
            f = i / (n + 1)
            yi = y_e + (y_ridge - y_e) * f
            zi = z_eave + (z_ridge - z_eave) * f
            for (xa_id, xa), (xb_id, xb) in zip(xs, xs[1:]):
                purlin = f"frame/roof/{xa_id}-{xb_id}/{slope}/p{i}/purlin"
                start, end = (xa, yi, zi), (xb, yi, zi)
                add(purlin, "PURLIN", start, end)
                join("purlin-rafter", _rafter_key(xa_id, slope), purlin, start)
                join("purlin-rafter", _rafter_key(xb_id, slope), purlin, end)

    return (
        tuple(sorted(members, key=lambda m: _utf16(m.generation_key))),
        tuple(sorted(connections, key=lambda c: _utf16(c.generation_key))),
    )


def generate(snapshot: "Snapshot") -> tuple[GeneratedMember, ...]:
    """All members the rule defines, sorted by generation_key (code-unit order).

    Defined only for snapshots that pass validation stages 1–4.
    """
    return _build(snapshot)[0]


def generate_connections(snapshot: "Snapshot") -> tuple[GeneratedConnection, ...]:
    """All connections the rule defines (CONN-001 §4–6), sorted by generation_key.

    Members are named by generation key. Defined only for snapshots that pass stages 1–4.
    """
    return _build(snapshot)[1]


from . import Rule, register  # noqa: E402

register(Rule(VERSION, GENERATED_ROLES, GENERATED_JUNCTION_CLASSES, generate, generate_connections))
