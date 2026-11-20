"""Authoritative Pydantic schema for the semantic snapshot, model schema version 2 (D028, MODEL-005).

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
from .connections import ConnectionType, JunctionClass
from .limits import MAX_SAFE_INTEGER, MODEL_SCHEMA_VERSION, RECORD_SCHEMA_VERSIONS

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


def RecordSchemaVersion(kind: str) -> Any:  # noqa: N802 (a type factory)
    """The record ``schema_version`` for one kind; versions are per kind (MODEL-005 §4.1)."""
    version = RECORD_SCHEMA_VERSIONS[kind]
    return Annotated[
        SafeInt,
        AfterValidator(_supported_version(version)),
        WithJsonSchema({"type": "integer", "const": version}),
    ]


Uuid = Annotated[str, StringConstraints(pattern=UUID_PATTERN)]
Timestamp = Annotated[
    str, StringConstraints(pattern=TIMESTAMP_PATTERN), AfterValidator(_calendar_timestamp)
]
Point2 = Annotated[list[float], Field(min_length=2, max_length=2)]
Point3 = Annotated[list[float], Field(min_length=3, max_length=3)]
# D052, MODEL-005 §4.2. RAFTER (reserved in VS-01, never generated) is removed.
MemberRole = Literal["POST", "BEAM", "SILL", "FLOOR_JOIST", "PRINCIPAL_RAFTER", "PURLIN", "KNEE_BRACE"]


class _Strict(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", allow_inf_nan=False, frozen=True)


class _Record(_Strict):
    id: Uuid


class Building(_Record):
    kind: Literal["Building"]
    schema_version: RecordSchemaVersion("Building")
    name: str
    footprint_id: Uuid
    level_ids: list[Uuid]
    roof_id: Uuid
    frame_system_id: Uuid


class Footprint(_Record):
    kind: Literal["Footprint"]
    schema_version: RecordSchemaVersion("Footprint")
    origin_m: Point2
    width_m: float
    depth_m: float
    rotation_rad: float


class Level(_Record):
    kind: Literal["Level"]
    schema_version: RecordSchemaVersion("Level")
    index: SafeInt
    elevation_m: float
    story_height_m: float


class GableRoof(_Record):
    kind: Literal["GableRoof"]
    schema_version: RecordSchemaVersion("GableRoof")
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
    schema_version: RecordSchemaVersion("TimberGrid")
    x_lines: list[XGridLine]
    y_lines: list[YGridLine]
    generation_rule_version: str


class RoleDefault(_Strict):
    """Section and material assigned to every generated member of one role (D039)."""

    section_id: Uuid
    material_id: Uuid


class FrameParameters(_Strict):
    """Inputs to the frame's generation rule (MODEL-005 §5). Bounds are checked in stages 3 and 4."""

    joist_spacing_m: float
    purlins_per_slope: SafeInt
    knee_brace_leg_m: float
    knee_braces_level_1: bool
    knee_braces_eave: bool


class FrameSystem(_Record):
    kind: Literal["FrameSystem"]
    schema_version: RecordSchemaVersion("FrameSystem")
    grid_id: Uuid
    member_ids: list[Uuid]
    generation_mode: str
    member_defaults: dict[MemberRole, RoleDefault]
    parameters: FrameParameters
    connection_ids: list[Uuid]
    connection_defaults: dict[JunctionClass, ConnectionType]


class TimberMember(_Record):
    kind: Literal["TimberMember"]
    schema_version: RecordSchemaVersion("TimberMember")
    member_role: MemberRole
    start_m: Point3
    end_m: Point3
    section_id: Uuid
    material_id: Uuid
    generation_key: str


class Section(_Record):
    kind: Literal["Section"]
    schema_version: RecordSchemaVersion("Section")
    shape: Literal["rectangular"]
    actual_width_m: float
    actual_depth_m: float
    nominal_label: str


class Material(_Record):
    # D038: nullable properties are required keys; unknown is explicit null.
    kind: Literal["Material"]
    schema_version: RecordSchemaVersion("Material")
    name: str
    species: str | None
    grade: str | None
    density_kg_m3: float | None
    provenance: str | None


class Connection(_Record):
    """A generated junction of exactly two members (D054, MODEL-005 §4.4). Makes no capacity claim."""

    kind: Literal["Connection"]
    schema_version: RecordSchemaVersion("Connection")
    junction_class: JunctionClass
    connection_type: ConnectionType
    member_ids: Annotated[list[Uuid], Field(min_length=2, max_length=2)]  # [receiving, entering]
    location_m: Point3
    generation_key: str


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
        Connection,
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
        "Connection",
        "Section",
        "Material",
    }
)


class Snapshot(_Strict):
    """A semantic snapshot, model schema version 2 (building-model.md §3, §3.3)."""

    model_config = ConfigDict(
        title="Semantic building snapshot (model schema version 2)",
    )

    model_schema_version: ModelSchemaVersion
    project_id: Uuid
    revision_id: Uuid
    parent_revision_id: Uuid | None
    created_at: Timestamp
    building: Building
    entities: list[Entity]
