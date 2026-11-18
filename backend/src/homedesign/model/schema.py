"""Authoritative Pydantic schema for the VS-01 semantic snapshot (D028).

Covers syntactic validation only (stage 1, D035). Referential, geometric, and
domain rules live in ``validation.py``. Records keep their wire representation
(UUIDs and timestamps as strings) so that canonical bytes round-trip exactly.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated, Any, Literal, Union

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    WithJsonSchema,
)
from pydantic_core import PydanticCustomError

from .paths import UUID_PATTERN
from .vs01 import MAX_SAFE_INTEGER, MODEL_SCHEMA_VERSION, RECORD_SCHEMA_VERSION

TIMESTAMP_PATTERN = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$"
# D042: stable grid-line IDs, x<n> / y<n> without leading zeros.
X_LINE_ID_PATTERN = r"^x(0|[1-9][0-9]{0,8})$"
Y_LINE_ID_PATTERN = r"^y(0|[1-9][0-9]{0,8})$"
_TIMESTAMP_RE = re.compile(TIMESTAMP_PATTERN)


def _integral(value: Any) -> Any:
    """Accept 1.0 as 1 (same canonical form, D029); reject fractional floats."""
    if isinstance(value, float):
        if not value.is_integer():
            raise PydanticCustomError("integer_out_of_range", "Value must be an integer.")
        if abs(value) > MAX_SAFE_INTEGER:
            raise PydanticCustomError(
                "integer_out_of_range", "Integer must be within ±(2^53 − 1)."
            )
        return int(value)
    return value


def _supported_version(expected: int):
    def check(value: int) -> int:
        if value != expected:
            raise PydanticCustomError(
                "unsupported_schema_version",
                "Schema version {value} is not supported (expected {expected}).",
                {"value": value, "expected": expected},
            )
        return value

    return check


def _calendar_timestamp(value: str) -> str:
    try:
        datetime.fromisoformat(value)
    except ValueError as exc:
        raise PydanticCustomError("invalid_timestamp", "Timestamp is not a valid date and time.") from exc
    return value


SafeInt = Annotated[
    int,
    BeforeValidator(_integral),
    Field(ge=-MAX_SAFE_INTEGER, le=MAX_SAFE_INTEGER),
]
ModelSchemaVersion = Annotated[
    SafeInt,
    AfterValidator(_supported_version(MODEL_SCHEMA_VERSION)),
    WithJsonSchema({"type": "integer", "const": MODEL_SCHEMA_VERSION}),
]
RecordSchemaVersion = Annotated[
    SafeInt,
    AfterValidator(_supported_version(RECORD_SCHEMA_VERSION)),
    WithJsonSchema({"type": "integer", "const": RECORD_SCHEMA_VERSION}),
]
Uuid = Annotated[str, StringConstraints(pattern=UUID_PATTERN)]
Timestamp = Annotated[
    str, StringConstraints(pattern=TIMESTAMP_PATTERN), AfterValidator(_calendar_timestamp)
]
Point2 = Annotated[list[float], Field(min_length=2, max_length=2)]
Point3 = Annotated[list[float], Field(min_length=3, max_length=3)]
MemberRole = Literal["POST", "BEAM", "FLOOR_JOIST", "RAFTER"]


class _Strict(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", allow_inf_nan=False, frozen=True)


class _Record(_Strict):
    id: Uuid
    schema_version: RecordSchemaVersion


class Building(_Record):
    kind: Literal["Building"]
    name: str
    footprint_id: Uuid
    level_ids: list[Uuid]
    roof_id: Uuid
    frame_system_id: Uuid


class Footprint(_Record):
    kind: Literal["Footprint"]
    origin_m: Point2
    width_m: float
    depth_m: float
    rotation_rad: float


class Level(_Record):
    kind: Literal["Level"]
    index: SafeInt
    elevation_m: float
    story_height_m: float


class GableRoof(_Record):
    kind: Literal["GableRoof"]
    ridge_axis: Literal["X", "Y"]
    pitch_rad: float
    eave_overhang_m: float
    ridge_offset_m: float


class XGridLine(_Strict):
    """A grid line across X with a stable identity (D042)."""

    id: Annotated[str, StringConstraints(pattern=X_LINE_ID_PATTERN)]
    fraction: float


class YGridLine(_Strict):
    """A grid line across Y with a stable identity (D042)."""

    id: Annotated[str, StringConstraints(pattern=Y_LINE_ID_PATTERN)]
    fraction: float


class TimberGrid(_Record):
    kind: Literal["TimberGrid"]
    x_lines: list[XGridLine]
    y_lines: list[YGridLine]
    generation_rule_version: str


class RoleDefault(_Strict):
    """Section and material assigned to every generated member of one role (D039)."""

    section_id: Uuid
    material_id: Uuid


class FrameSystem(_Record):
    kind: Literal["FrameSystem"]
    grid_id: Uuid
    member_ids: list[Uuid]
    generation_mode: str
    member_defaults: dict[MemberRole, RoleDefault]


class TimberMember(_Record):
    kind: Literal["TimberMember"]
    member_role: MemberRole
    start_m: Point3
    end_m: Point3
    section_id: Uuid
    material_id: Uuid
    generation_key: str


class Section(_Record):
    kind: Literal["Section"]
    shape: Literal["rectangular"]
    actual_width_m: float
    actual_depth_m: float
    nominal_label: str


class Material(_Record):
    # D038: nullable properties are required keys; unknown is explicit null.
    kind: Literal["Material"]
    name: str
    species: str | None
    grade: str | None
    density_kg_m3: float | None
    provenance: str | None


# Building is accepted here at the type level so that stage 2 can report
# BUILDING_IN_ENTITIES (building-model.md §3) instead of an unknown kind.
Entity = Annotated[
    Union[
        Building,
        Footprint,
        Level,
        GableRoof,
        TimberGrid,
        FrameSystem,
        TimberMember,
        Section,
        Material,
    ],
    Field(discriminator="kind"),
]

ENTITY_KINDS = frozenset(
    {
        "Building",
        "Footprint",
        "Level",
        "GableRoof",
        "TimberGrid",
        "FrameSystem",
        "TimberMember",
        "Section",
        "Material",
    }
)


class Snapshot(_Strict):
    """A VS-01 semantic snapshot (building-model.md §3)."""

    model_config = ConfigDict(
        title="VS-01 semantic building snapshot (model schema version 1)",
    )

    model_schema_version: ModelSchemaVersion
    project_id: Uuid
    revision_id: Uuid
    parent_revision_id: Uuid | None
    created_at: Timestamp
    building: Building
    entities: list[Entity]
