"""`plan2d` and `mesh3d` payload DTOs (artifacts.md §5–6; Pydantic-authoritative per D028)."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from homedesign.model.schema import Uuid

XY = Annotated[list[float], Field(min_length=2, max_length=2)]
XYZ = Annotated[list[float], Field(min_length=3, max_length=3)]


class _Strict(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", allow_inf_nan=False, frozen=True)


# --- plan2d ------------------------------------------------------------------


class PlanPost(_Strict):
    member_id: Uuid
    generation_key: str
    xy_m: XY
    section_id: Uuid


class PlanBeam(_Strict):
    member_id: Uuid
    generation_key: str
    start_xy_m: XY
    end_xy_m: XY
    section_id: Uuid


class PlanPlane(_Strict):
    plane_id: Literal["level-0", "level-1", "eave"]
    level_id: Uuid | None
    z_m: float
    posts: list[PlanPost]
    beams: list[PlanBeam]


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
    planes: Annotated[list[PlanPlane], Field(min_length=3, max_length=3)]
    footprint: PlanFootprint
    roof_plan: RoofPlan
    dimensions: Annotated[list[Dimension], Field(min_length=2, max_length=2)]


# --- mesh3d ------------------------------------------------------------------


class MeshMember(_Strict):
    member_id: Uuid
    generation_key: str
    role: Literal["POST", "BEAM", "FLOOR_JOIST", "RAFTER"]
    primitive: Literal["oriented_box"] = "oriented_box"
    axis_start_m: XYZ
    axis_end_m: XYZ
    section_width_m: float
    section_depth_m: float


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
    envelope: Envelope3d
