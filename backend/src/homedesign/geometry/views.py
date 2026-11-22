"""`plan2d` and `mesh3d` selectors and builders (GEOM-001; ART-002 §4–5; DEP-001 §4; ART-003 §5–6).

Each builder reads only its selection (D061 item 9), which its selector extracts from the stored
snapshot: exactly the values the builder reads, after the projections it applies (DEP-001 §4.1).
All values are IEEE-754 doubles evaluated exactly as written; only values derived from tan(pitch)
may differ across implementations, within 1e-12 m (geometry.md "Numeric evaluation"). Roof planes
follow D048. Walls, openings, and wall framing (VS-02b) read no roof value, so they are bit-identical.
"""

from __future__ import annotations

import math
from typing import Any

from homedesign.assemblies.schedule import WallRecords
from homedesign.assemblies.walls import VERTICAL_KINDS, along_index, build_up_extents, in_plane_m, layer_spans, outward_xy, through_wall_m
from homedesign.model.schema import Snapshot

from .payloads import Mesh3dPayload, Plan2dPayload


def _utf16(text: str) -> bytes:
    return text.encode("utf-16-be")


class _Records:
    """The records the selectors resolve, from a snapshot that passed validation."""

    def __init__(self, snapshot: Snapshot) -> None:
        by_id: dict[str, Any] = {e.id: e for e in snapshot.entities}
        building = snapshot.building
        self.by_id = by_id
        self.footprint = by_id[building.footprint_id]
        self.level0, self.level1 = (by_id[i] for i in building.level_ids)
        self.roof = by_id[building.roof_id]
        self.members = sorted((e for e in snapshot.entities if e.kind == "TimberMember"), key=lambda m: _utf16(m.generation_key))
        self.connections = sorted((e for e in snapshot.entities if e.kind == "Connection"), key=lambda c: _utf16(c.generation_key))


def _framing_index(definition: Any) -> int:
    return next(k for k, layer in enumerate(definition.layers) if layer.framing is not None)


def _select_plan_walls(snapshot: Snapshot) -> dict[str, Any]:
    """ART-003 §8.1: per wall its plan line, outward normal, and build-up extents (§5.1, computed here);
    per opening its kind and extent along the wall; per piece its kind and plan projection."""
    w = WallRecords(snapshot)
    walls = []
    for wall in w.walls:
        definition = w.definition(wall)
        exterior, interior = build_up_extents([layer.thickness_m for layer in definition.layers], _framing_index(definition))
        walls.append({"id": wall.id, "generation_key": wall.generation_key, "level_id": wall.level_id, "start_xy_m": list(wall.start_m[:2]),
                      "end_xy_m": list(wall.end_m[:2]), "outward_xy": outward_xy(w.side(wall)), "exterior_m": exterior, "interior_m": interior})
    openings = [{"id": o.id, "wall_id": o.wall_id, "opening_kind": o.opening_kind, "offset_m": o.offset_m, "width_m": o.width_m} for o in w.openings]
    pieces = []
    for piece in w.pieces:
        item: dict[str, Any] = {"id": piece.id, "generation_key": piece.generation_key, "wall_id": w.wall_of_piece[piece.id].id, "piece_kind": piece.piece_kind}
        if piece.piece_kind in VERTICAL_KINDS:
            item["xy_m"] = list(piece.start_m[:2])
        else:
            item["start_xy_m"], item["end_xy_m"] = list(piece.start_m[:2]), list(piece.end_m[:2])
        pieces.append(item)
    return {"walls": walls, "openings": openings, "wall_framing": pieces}


def _select_mesh_walls(snapshot: Snapshot) -> dict[str, Any]:
    """ART-003 §8.1: per wall its base line, height, outward normal, and layers (thicknesses and the framing
    layer's index); per opening its rectangle; per piece its axis and section dimensions (not its section_id)."""
    w = WallRecords(snapshot)
    walls = []
    for wall in w.walls:
        definition = w.definition(wall)
        walls.append({
            "id": wall.id, "generation_key": wall.generation_key, "start_m": list(wall.start_m), "end_m": list(wall.end_m),
            "height_m": wall.height_m, "outward_xy": outward_xy(w.side(wall)),
            "layers": [{"name": layer.name, "function": layer.function, "thickness_m": layer.thickness_m} for layer in definition.layers],
            "framing_index": _framing_index(definition),
        })
    openings = [
        {"id": o.id, "wall_id": o.wall_id, "opening_kind": o.opening_kind, "offset_m": o.offset_m, "width_m": o.width_m,
         "sill_height_m": o.sill_height_m, "height_m": o.height_m}
        for o in w.openings
    ]
    pieces = []
    for piece in w.pieces:
        section = w.by_id[piece.section_id]
        pieces.append({
            "id": piece.id, "generation_key": piece.generation_key, "wall_id": w.wall_of_piece[piece.id].id, "piece_kind": piece.piece_kind,
            "start_m": list(piece.start_m), "end_m": list(piece.end_m),
            "section_in_plane_m": in_plane_m(piece.piece_kind, section.actual_width_m, section.actual_depth_m),
            "section_through_wall_m": through_wall_m(piece.piece_kind, section.actual_width_m, section.actual_depth_m),
        })
    return {"walls": walls, "openings": openings, "wall_framing": pieces}


def select_plan2d(snapshot: Snapshot) -> dict[str, Any]:
    """DEP-001 §4.2: plan positions in x, y, plane heights, level IDs, and the overhang; ART-003 §8.1: walls."""
    r = _Records(snapshot)
    fp = r.footprint
    members = []
    for m in r.members:  # generation_key order
        item: dict[str, Any] = {"id": m.id, "generation_key": m.generation_key, "role": m.member_role, "start_xy_m": list(m.start_m[:2])}
        if m.member_role != "POST":  # the plan reads only a post's start point
            item["end_xy_m"] = list(m.end_m[:2])
        members.append(item)
    return {
        "footprint": {"origin_m": list(fp.origin_m), "width_m": fp.width_m, "depth_m": fp.depth_m, "rotation_rad": fp.rotation_rad},
        "levels": [
            {"id": r.level0.id, "elevation_m": r.level0.elevation_m},
            {"id": r.level1.id, "elevation_m": r.level1.elevation_m, "story_height_m": r.level1.story_height_m},
        ],
        "roof": {"eave_overhang_m": r.roof.eave_overhang_m},
        "members": members,
        "connections": [
            {"id": c.id, "generation_key": c.generation_key, "junction_class": c.junction_class, "connection_type": c.connection_type,
             "xy_m": list(c.location_m[:2]), "entering_member_id": c.member_ids[1]}
            for c in r.connections
        ],
        **_select_plan_walls(snapshot),
    }


def select_mesh3d(snapshot: Snapshot) -> dict[str, Any]:
    """DEP-001 §4.2: 3D axes, section dimensions (not section IDs), connection locations, the roof; ART-003 §8.1: walls."""
    r = _Records(snapshot)
    fp = r.footprint
    members = []
    for m in r.members:
        section = r.by_id[m.section_id]
        members.append({"id": m.id, "generation_key": m.generation_key, "role": m.member_role, "start_m": list(m.start_m), "end_m": list(m.end_m),
                        "actual_width_m": section.actual_width_m, "actual_depth_m": section.actual_depth_m})
    return {
        "footprint": {"origin_m": list(fp.origin_m), "width_m": fp.width_m, "depth_m": fp.depth_m},
        "levels": [{"elevation_m": r.level0.elevation_m}, {"elevation_m": r.level1.elevation_m, "story_height_m": r.level1.story_height_m}],
        "roof": {"ridge_axis": r.roof.ridge_axis, "pitch_rad": r.roof.pitch_rad, "eave_overhang_m": r.roof.eave_overhang_m},
        "members": members,
        "connections": [
            {"id": c.id, "generation_key": c.generation_key, "junction_class": c.junction_class, "connection_type": c.connection_type,
             "location_m": list(c.location_m)}
            for c in r.connections
        ],
        **_select_mesh_walls(snapshot),
    }


class _Frame:
    """Envelope coordinates both views compute from a selection."""

    def __init__(self, selection: dict[str, Any]) -> None:
        fp = selection["footprint"]
        self.width_m, self.depth_m = fp["width_m"], fp["depth_m"]
        self.x0, self.y0 = fp["origin_m"]
        self.x1 = self.x0 + fp["width_m"]
        self.y1 = self.y0 + fp["depth_m"]
        level1 = selection["levels"][1]
        self.z_eave = level1["elevation_m"] + level1["story_height_m"]
        overhang = selection["roof"]["eave_overhang_m"]
        self.y_ridge = self.y0 + fp["depth_m"] / 2
        self.y_south = self.y0 - overhang
        self.y_north = self.y0 + fp["depth_m"] + overhang

    def ring(self) -> list[list[float]]:
        """Wall rectangle, counterclockwise from the origin (artifacts.md §5)."""
        return [[self.x0, self.y0], [self.x1, self.y0], [self.x1, self.y1], [self.x0, self.y1]]


PLANES = ("level-0", "level-1", "eave", "roof")
ARRAYS = ("posts", "beams", "sills", "joists", "braces", "rafters", "purlins")

# ART-002 §4.1: (role, key segment) -> (plane, array). The role is matched first, because a joist's
# or brace's key also contains its beam plane's segment.
PLAN_ASSIGNMENT: tuple[tuple[str, str, str, str], ...] = (
    ("POST", "/level-0/post", "level-0", "posts"),
    ("SILL", "/plane-L0/sill", "level-0", "sills"),
    ("POST", "/level-1/post", "level-1", "posts"),
    ("BEAM", "/plane-L1/beam", "level-1", "beams"),
    ("FLOOR_JOIST", "/plane-L1/joist", "level-1", "joists"),
    ("KNEE_BRACE", "/plane-L1/brace/", "level-1", "braces"),
    ("BEAM", "/plane-eave/beam", "eave", "beams"),
    ("KNEE_BRACE", "/plane-eave/brace/", "eave", "braces"),
    ("PRINCIPAL_RAFTER", "/principal-rafter", "roof", "rafters"),
    ("PURLIN", "/purlin", "roof", "purlins"),
)


def plan_slot(role: str, generation_key: str) -> tuple[str, str]:
    """(plane_id, array) for a member; raises when no row matches, so the derivation fails."""
    for want_role, segment, plane, array in PLAN_ASSIGNMENT:
        if role == want_role and segment in generation_key:
            return plane, array
    raise ValueError(f"member {role} {generation_key!r} matches no plan plane")


def _openings_by_wall(selection: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Each wall's openings, sorted by offset along the wall, then ID (ART-003 §5.2, §6.1)."""
    by_wall: dict[str, list[dict[str, Any]]] = {}
    for opening in selection["openings"]:
        by_wall.setdefault(opening["wall_id"], []).append(opening)
    return {wall_id: sorted(items, key=lambda o: (o["offset_m"], o["id"])) for wall_id, items in by_wall.items()}


def _along(start: list[float], generation_key: str, distance: float) -> list[float]:
    """The point ``distance`` along an axis-aligned wall from ``start`` (``start + distance``, as written)."""
    point = list(start)
    i = along_index(generation_key)
    point[i] = start[i] + distance
    return point


def build_plan2d(selection: dict[str, Any]) -> dict[str, Any]:
    """The `plan2d` payload from `select_plan2d`'s selection (its only model input, D061)."""
    m = _Frame(selection)
    fp = selection["footprint"]
    level0, level1 = selection["levels"]
    heights = {"level-0": (level0["id"], level0["elevation_m"]), "level-1": (level1["id"], level1["elevation_m"]),
               "eave": (None, m.z_eave), "roof": (None, m.z_eave)}  # the roof framing bears on the plate line (D058, D060)
    planes = {
        plane: {"plane_id": plane, "level_id": level_id, "z_m": z, **{array: [] for array in ARRAYS}, "connections": []}
        for plane, (level_id, z) in heights.items()
    }
    plane_of_level = {level0["id"]: "level-0", level1["id"]: "level-1"}
    for plane in planes.values():
        plane["walls"], plane["wall_framing"] = [], []
    plane_of_wall: dict[str, str] = {}
    openings = _openings_by_wall(selection)
    for wall in selection["walls"]:  # already in generation_key order
        plane = plane_of_level[wall["level_id"]]
        plane_of_wall[wall["id"]] = plane
        key, start = wall["generation_key"], wall["start_xy_m"]
        planes[plane]["walls"].append({
            "wall_id": wall["id"],
            "generation_key": key,
            "start_xy_m": start,
            "end_xy_m": wall["end_xy_m"],
            "outward_xy": wall["outward_xy"],
            "exterior_m": wall["exterior_m"],
            "interior_m": wall["interior_m"],
            "openings": [  # gaps at the rough opening, along the reference line
                {"opening_id": o["id"], "opening_kind": o["opening_kind"], "start_xy_m": _along(start, key, o["offset_m"]),
                 "end_xy_m": _along(start, key, o["offset_m"] + o["width_m"])}
                for o in openings.get(wall["id"], [])
            ],
        })
    for piece in selection["wall_framing"]:  # already in generation_key order
        item = {"piece_id": piece["id"], "piece_kind": piece["piece_kind"]}
        if "xy_m" in piece:
            item["xy_m"] = piece["xy_m"]
        else:
            item["start_xy_m"], item["end_xy_m"] = piece["start_xy_m"], piece["end_xy_m"]
        planes[plane_of_wall[piece["wall_id"]]]["wall_framing"].append(item)
    plane_of_member: dict[str, str] = {}
    for member in selection["members"]:  # already in generation_key order
        plane, array = plan_slot(member["role"], member["generation_key"])
        plane_of_member[member["id"]] = plane
        item: dict[str, Any] = {"member_id": member["id"], "generation_key": member["generation_key"]}
        if array == "posts":
            item["xy_m"] = member["start_xy_m"]
        else:
            item["start_xy_m"], item["end_xy_m"] = member["start_xy_m"], member["end_xy_m"]
        planes[plane][array].append(item)
    for connection in selection["connections"]:  # already in generation_key order
        planes[plane_of_member[connection["entering_member_id"]]]["connections"].append({  # the entering member's plane
            "connection_id": connection["id"],
            "generation_key": connection["generation_key"],
            "junction_class": connection["junction_class"],
            "connection_type": connection["connection_type"],
            "xy_m": connection["xy_m"],
        })
    payload = {
        "units": "m",
        "planes": [planes[p] for p in PLANES],
        "footprint": {
            "origin_m": [m.x0, m.y0],
            "width_m": fp["width_m"],
            "depth_m": fp["depth_m"],
            "rotation_rad": fp["rotation_rad"],
            "ring_m": m.ring(),
        },
        "roof_plan": {
            "ridge_m": {"start_xy_m": [m.x0, m.y_ridge], "end_xy_m": [m.x1, m.y_ridge]},
            # North/south overhang only; no rake overhang in VS-01 (artifacts.md §5).
            "eave_ring_m": [[m.x0, m.y_south], [m.x1, m.y_south], [m.x1, m.y_north], [m.x0, m.y_north]],
        },
        "dimensions": [
            # value_m is copied from the footprint, never measured (AC-01).
            {"id": "footprint-width", "start_m": [m.x0, m.y0], "end_m": [m.x1, m.y0], "value_m": fp["width_m"]},
            {"id": "footprint-depth", "start_m": [m.x0, m.y0], "end_m": [m.x0, m.y1], "value_m": fp["depth_m"]},
        ],
    }
    return Plan2dPayload.model_validate(payload).model_dump(mode="json")


def build_mesh3d(selection: dict[str, Any]) -> dict[str, Any]:
    """The `mesh3d` payload from `select_mesh3d`'s selection (its only model input, D061)."""
    m = _Frame(selection)
    roof = selection["roof"]
    t = math.tan(roof["pitch_rad"])
    z_ridge = m.z_eave + (m.depth_m / 2) * t
    z_edge = m.z_eave - roof["eave_overhang_m"] * t  # D048: plane continues below z_eave over the overhang
    members = [
        {
            "member_id": member["id"],
            "generation_key": member["generation_key"],
            "role": member["role"],
            "primitive": "oriented_box",
            "axis_start_m": list(member["start_m"]),
            "axis_end_m": list(member["end_m"]),
            "section_width_m": member["actual_width_m"],
            "section_depth_m": member["actual_depth_m"],
        }
        for member in selection["members"]
    ]
    connections = [
        {
            "connection_id": c["id"],
            "generation_key": c["generation_key"],
            "junction_class": c["junction_class"],
            "connection_type": c["connection_type"],
            "location_m": list(c["location_m"]),  # the record's, copied exactly
        }
        for c in selection["connections"]
    ]
    openings = _openings_by_wall(selection)
    walls = []
    for wall in selection["walls"]:  # already in generation_key order
        spans = layer_spans([layer["thickness_m"] for layer in wall["layers"]], wall["framing_index"])
        walls.append({
            "wall_id": wall["id"],
            "generation_key": wall["generation_key"],
            "primitive": "layered_wall",
            "base_start_m": wall["start_m"],
            "base_end_m": wall["end_m"],
            "height_m": wall["height_m"],
            "outward_xy": wall["outward_xy"],
            "layers": [{"name": layer["name"], "function": layer["function"], "inner_m": span.inner_m, "outer_m": span.outer_m}
                       for layer, span in zip(wall["layers"], spans, strict=True)],
            "voids": sorted(
                ({"opening_id": o["id"], "opening_kind": o["opening_kind"], "u_m": [o["offset_m"], o["offset_m"] + o["width_m"]],
                  "v_m": [o["sill_height_m"], o["sill_height_m"] + o["height_m"]]} for o in openings.get(wall["id"], [])),
                key=lambda v: (v["u_m"][0], v["opening_id"]),
            ),
        })
    wall_framing = [
        {
            "piece_id": piece["id"],
            "piece_kind": piece["piece_kind"],
            "wall_id": piece["wall_id"],
            "axis_start_m": piece["start_m"],
            "axis_end_m": piece["end_m"],
            "section_in_plane_m": piece["section_in_plane_m"],
            "section_through_wall_m": piece["section_through_wall_m"],
        }
        for piece in selection["wall_framing"]  # already in generation_key order
    ]
    level0, level1 = selection["levels"]
    payload = {
        "units": "m",
        "members": members,
        "connections": connections,
        "walls": walls,
        "wall_framing": wall_framing,
        "envelope": {
            "footprint_ring_m": m.ring(),
            "level_z_m": [level0["elevation_m"], level1["elevation_m"]],
            "z_eave_m": m.z_eave,
            "roof": {
                "kind": "gable",
                "ridge_axis": roof["ridge_axis"],
                "pitch_rad": roof["pitch_rad"],
                "ridge_start_m": [m.x0, m.y_ridge, z_ridge],
                "ridge_end_m": [m.x1, m.y_ridge, z_ridge],
                "surfaces": [
                    {"id": "south", "ring_m": [[m.x0, m.y_south, z_edge], [m.x1, m.y_south, z_edge],
                                               [m.x1, m.y_ridge, z_ridge], [m.x0, m.y_ridge, z_ridge]]},
                    {"id": "north", "ring_m": [[m.x0, m.y_north, z_edge], [m.x0, m.y_ridge, z_ridge],
                                               [m.x1, m.y_ridge, z_ridge], [m.x1, m.y_north, z_edge]]},
                ],
            },
        },
    }
    return Mesh3dPayload.model_validate(payload).model_dump(mode="json")
