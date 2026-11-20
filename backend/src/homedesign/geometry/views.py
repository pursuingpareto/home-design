"""`plan2d` and `mesh3d` builders (GEOM-001; ART-002 §4–5).

Pure functions of the stored snapshot (geometry.md "Member source"). All values are IEEE-754
doubles evaluated exactly as written; only values derived from tan(pitch) may differ across
implementations, within 1e-12 m (geometry.md "Numeric evaluation"). Roof planes follow D048.
"""

from __future__ import annotations

import math
from typing import Any

from homedesign.model.schema import Snapshot

from .payloads import Mesh3dPayload, Plan2dPayload


def _utf16(text: str) -> bytes:
    return text.encode("utf-16-be")


class _Model:
    """Records the views read, resolved from a snapshot that passed validation."""

    def __init__(self, snapshot: Snapshot) -> None:
        by_id: dict[str, Any] = {e.id: e for e in snapshot.entities}
        building = snapshot.building
        self.footprint = by_id[building.footprint_id]
        self.level0, self.level1 = (by_id[i] for i in building.level_ids)
        self.roof = by_id[building.roof_id]
        self.sections = {e.id: e for e in snapshot.entities if e.kind == "Section"}
        self.members = sorted((e for e in snapshot.entities if e.kind == "TimberMember"), key=lambda m: _utf16(m.generation_key))
        self.connections = sorted((e for e in snapshot.entities if e.kind == "Connection"), key=lambda c: _utf16(c.generation_key))
        fp = self.footprint
        self.x0, self.y0 = fp.origin_m
        self.x1 = self.x0 + fp.width_m
        self.y1 = self.y0 + fp.depth_m
        self.z_eave = self.level1.elevation_m + self.level1.story_height_m
        self.y_ridge = self.y0 + fp.depth_m / 2
        self.y_south = self.y0 - self.roof.eave_overhang_m
        self.y_north = self.y0 + fp.depth_m + self.roof.eave_overhang_m

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


def build_plan2d(snapshot: Snapshot) -> dict[str, Any]:
    m = _Model(snapshot)
    fp = m.footprint
    heights = {"level-0": (m.level0.id, m.level0.elevation_m), "level-1": (m.level1.id, m.level1.elevation_m),
               "eave": (None, m.z_eave), "roof": (None, m.z_eave)}  # the roof framing bears on the plate line (D058, D060)
    planes = {
        plane: {"plane_id": plane, "level_id": level_id, "z_m": z, **{array: [] for array in ARRAYS}, "connections": []}
        for plane, (level_id, z) in heights.items()
    }
    plane_of_member: dict[str, str] = {}
    for member in m.members:  # already in generation_key order
        plane, array = plan_slot(member.member_role, member.generation_key)
        plane_of_member[member.id] = plane
        item: dict[str, Any] = {"member_id": member.id, "generation_key": member.generation_key}
        if array == "posts":
            item["xy_m"] = member.start_m[:2]
        else:
            item["start_xy_m"], item["end_xy_m"] = member.start_m[:2], member.end_m[:2]
        planes[plane][array].append(item)
    for connection in m.connections:  # already in generation_key order
        planes[plane_of_member[connection.member_ids[1]]]["connections"].append({  # the entering member's plane
            "connection_id": connection.id,
            "generation_key": connection.generation_key,
            "junction_class": connection.junction_class,
            "connection_type": connection.connection_type,
            "xy_m": connection.location_m[:2],
        })
    payload = {
        "units": "m",
        "planes": [planes[p] for p in PLANES],
        "footprint": {
            "origin_m": [m.x0, m.y0],
            "width_m": fp.width_m,
            "depth_m": fp.depth_m,
            "rotation_rad": fp.rotation_rad,
            "ring_m": m.ring(),
        },
        "roof_plan": {
            "ridge_m": {"start_xy_m": [m.x0, m.y_ridge], "end_xy_m": [m.x1, m.y_ridge]},
            # North/south overhang only; no rake overhang in VS-01 (artifacts.md §5).
            "eave_ring_m": [[m.x0, m.y_south], [m.x1, m.y_south], [m.x1, m.y_north], [m.x0, m.y_north]],
        },
        "dimensions": [
            # value_m is copied from the footprint, never measured (AC-01).
            {"id": "footprint-width", "start_m": [m.x0, m.y0], "end_m": [m.x1, m.y0], "value_m": fp.width_m},
            {"id": "footprint-depth", "start_m": [m.x0, m.y0], "end_m": [m.x0, m.y1], "value_m": fp.depth_m},
        ],
    }
    return Plan2dPayload.model_validate(payload).model_dump(mode="json")


def build_mesh3d(snapshot: Snapshot) -> dict[str, Any]:
    m = _Model(snapshot)
    roof = m.roof
    t = math.tan(roof.pitch_rad)
    z_ridge = m.z_eave + (m.footprint.depth_m / 2) * t
    z_edge = m.z_eave - roof.eave_overhang_m * t  # D048: plane continues below z_eave over the overhang
    members = []
    for member in m.members:
        section = m.sections[member.section_id]
        members.append({
            "member_id": member.id,
            "generation_key": member.generation_key,
            "role": member.member_role,
            "primitive": "oriented_box",
            "axis_start_m": list(member.start_m),
            "axis_end_m": list(member.end_m),
            "section_width_m": section.actual_width_m,
            "section_depth_m": section.actual_depth_m,
        })
    connections = [
        {
            "connection_id": c.id,
            "generation_key": c.generation_key,
            "junction_class": c.junction_class,
            "connection_type": c.connection_type,
            "location_m": list(c.location_m),  # the record's, copied exactly
        }
        for c in m.connections
    ]
    payload = {
        "units": "m",
        "members": members,
        "connections": connections,
        "envelope": {
            "footprint_ring_m": m.ring(),
            "level_z_m": [m.level0.elevation_m, m.level1.elevation_m],
            "z_eave_m": m.z_eave,
            "roof": {
                "kind": "gable",
                "ridge_axis": roof.ridge_axis,
                "pitch_rad": roof.pitch_rad,
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
