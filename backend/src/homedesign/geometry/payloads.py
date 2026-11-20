"""`plan2d` and `mesh3d` payload DTOs (artifacts.md §5–6; Pydantic-authoritative per D028)."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from homedesign.model.connections import ConnectionType, JunctionClass
from homedesign.model.schema import MemberRole, Uuid

XY = Annotated[list[float], Field(min_length=2, max_length=2)]
XYZ = Annotated[list[float], Field(min_length=3, max_length=3)]


class _Strict(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", allow_inf_nan=False, frozen=True)


# --- plan2d ------------------------------------------------------------------


# No section_id in the plan (ART-002 §4.3): D056's "changing a role's section leaves plan2d unaffected".


class PlanPost(_Strict):
    member_id: Uuid
    generation_key: str
    xy_m: XY


class PlanLinearMember(_Strict):
    """Every role but posts: the plan projection of the member's axis (ART-002 §4.1)."""

    member_id: Uuid
    generation_key: str
    start_xy_m: XY
    end_xy_m: XY


class PlanConnection(_Strict):
    """A connection marker on the entering member's plane (ART-002 §4.2). Members are listed by the schedule."""

    connection_id: Uuid
    generation_key: str
    junction_class: JunctionClass
    connection_type: ConnectionType
    xy_m: XY


class PlanPlane(_Strict):
    plane_id: Literal["level-0", "level-1", "eave", "roof"]
    level_id: Uuid | None
    z_m: float
    posts: list[PlanPost]
    beams: list[PlanLinearMember]
    sills: list[PlanLinearMember]
    joists: list[PlanLinearMember]
    braces: list[PlanLinearMember]
    rafters: list[PlanLinearMember]
    purlins: list[PlanLinearMember]
    connections: list[PlanConnection]


class PlanFootprint(_Strict):
    origin_m: XY
    width_m: float
    depth_m: float
    rotation_rad: float
    ring_m: Annotated[list[XY], Field(min_length=4, max_length=4)]


class PlanLine(_Strict):
    start_xy_m: XY
    end_xy_m: XY


class RoofPlan(_Strict):
    ridge_m: PlanLine
    eave_ring_m: Annotated[list[XY], Field(min_length=4, max_length=4)]


class Dimension(_Strict):
    id: Literal["footprint-width", "footprint-depth"]
    start_m: XY
    end_m: XY
    value_m: float


class Plan2dPayload(_Strict):
    model_config = ConfigDict(title="plan2d payload (artifacts.md §5)")

    units: Literal["m"] = "m"
    planes: Annotated[list[PlanPlane], Field(min_length=4, max_length=4)]
    footprint: PlanFootprint
    roof_plan: RoofPlan
    dimensions: Annotated[list[Dimension], Field(min_length=2, max_length=2)]


# --- mesh3d ------------------------------------------------------------------


class MeshMember(_Strict):
    member_id: Uuid
    generation_key: str
    role: MemberRole
    primitive: Literal["oriented_box"] = "oriented_box"
    axis_start_m: XYZ
    axis_end_m: XYZ
    section_width_m: float
    section_depth_m: float


class MeshConnection(_Strict):
    """A connection marker: where it is and what type it has, with no size or shape (ART-002 §5.2)."""

    connection_id: Uuid
    generation_key: str
    junction_class: JunctionClass
    connection_type: ConnectionType
    location_m: XYZ


class RoofSurface(_Strict):
    id: Literal["south", "north"]
    ring_m: Annotated[list[XYZ], Field(min_length=4, max_length=4)]


class GableRoofGeometry(_Strict):
    kind: Literal["gable"] = "gable"
    ridge_axis: Literal["X"]
    pitch_rad: float
    ridge_start_m: XYZ
    ridge_end_m: XYZ
    surfaces: Annotated[list[RoofSurface], Field(min_length=2, max_length=2)]


class Envelope3d(_Strict):
    footprint_ring_m: Annotated[list[XY], Field(min_length=4, max_length=4)]
    level_z_m: Annotated[list[float], Field(min_length=2, max_length=2)]
    z_eave_m: float
    roof: GableRoofGeometry


class Mesh3dPayload(_Strict):
    model_config = ConfigDict(title="mesh3d payload (artifacts.md §6)")

    units: Literal["m"] = "m"
    members: list[MeshMember]
    connections: list[MeshConnection]
    envelope: Envelope3d
