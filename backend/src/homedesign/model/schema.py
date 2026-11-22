"""Authoritative Pydantic schema for the semantic snapshot, model schema version 3 (D028, MODEL-005, MODEL-006).

Covers syntactic validation only (stage 1, D035). Referential, geometric, and
domain rules live in ``validation.py``. Records keep their wire representation
(UUIDs and timestamps as strings) so that canonical bytes round-trip exactly.
"""

from __future__ import annotations

import re
from datetime import date, datetime
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
# MODEL-006 §4.3: definition labels and layer names are slugs (tokens of the estimate key, D070).
SLUG_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"
# MODEL-006 §6.1: a DeclaredValue date is an RFC 3339 full date.
DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"


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


def _calendar_date(value: str) -> str:
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise PydanticCustomError("invalid_date", "Date is not a valid calendar date.") from exc
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
Slug = Annotated[str, StringConstraints(pattern=SLUG_PATTERN)]
CalendarDate = Annotated[str, StringConstraints(pattern=DATE_PATTERN), AfterValidator(_calendar_date)]
Point2 = Annotated[list[float], Field(min_length=2, max_length=2)]
Point3 = Annotated[list[float], Field(min_length=3, max_length=3)]
# D052, MODEL-005 §4.2. RAFTER (reserved in VS-01, never generated) is removed.
MemberRole = Literal["POST", "BEAM", "SILL", "FLOOR_JOIST", "PRINCIPAL_RAFTER", "PURLIN", "KNEE_BRACE"]
# MODEL-006 §4 (D067, D069, D070). Exported so that payloads and the browser import one definition (§12).
AssemblyFamily = Literal["STRAW_BALE", "STUD_INFILL"]
LayerFunction = Literal["FINISH", "SHEATHING", "INSULATION", "FRAMING"]
PieceKind = Literal["STUD", "GIRT", "KING", "JACK", "HEADER", "ROUGH_SILL", "CRIPPLE", "BUCK_JAMB", "BUCK_HEAD", "BUCK_SILL"]
OpeningKind = Literal["WINDOW", "DOOR"]


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
    wall_system_id: Uuid  # MODEL-006 §4.2, D073


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


# --- Version 3: assemblies, walls, wall framing, openings (MODEL-006 §4) ---------


class WallSystem(_Record):
    """The wall rule version, D068's project-wide default definition, and the walls and openings (D073)."""

    kind: Literal["WallSystem"]
    schema_version: RecordSchemaVersion("WallSystem")
    generation_rule_version: str
    default_assembly_definition_id: Uuid
    wall_ids: list[Uuid]  # ascending generation_key (D030)
    opening_ids: list[Uuid]  # ascending ID


class DeclaredValue(_Strict):
    """A declared property value with its provenance (D071, D075). The unit is fixed by the field name, in SI."""

    value: float
    source: str
    date: CalendarDate
    note: str | None


class StudFraming(_Strict):
    """A stud infill framing layer (D066, D067; MODEL-006 §4.3). Kings, jacks, cripples, and rough sills take the stud section (D076)."""

    type: Literal["STUD"]
    framing_material_id: Uuid
    framing_thermal_conductivity_w_m_k: DeclaredValue | None
    stud_section_id: Uuid
    stud_spacing_m: float
    girt_count: SafeInt
    girt_section_id: Uuid | None
    header_section_id: Uuid
    jack_threshold_width_m: float


class BuckFraming(_Strict):
    """A straw bale framing layer: bucks at openings, no girts in VS-02b (D066, D067)."""

    type: Literal["BUCK"]
    framing_material_id: Uuid
    framing_thermal_conductivity_w_m_k: DeclaredValue | None
    buck_section_id: Uuid
    girt_count: SafeInt


Framing = Annotated[Union[StudFraming, BuckFraming], Field(discriminator="type")]


class Layer(_Strict):
    """One layer of an assembly definition, embedded in it (D074). Only the FRAMING layer has ``framing``."""

    name: Slug
    function: LayerFunction
    material_id: Uuid
    thickness_m: float
    thermal_conductivity_w_m_k: DeclaredValue | None
    thermal_resistance_m2_k_w: DeclaredValue | None
    vapor_permeance_kg_pa_s_m2: DeclaredValue | None
    framing: Framing | None


class AssemblyDefinition(_Record):
    """A fixed layered wall definition, a catalog record (D067; MODEL-006 §4.3)."""

    kind: Literal["AssemblyDefinition"]
    schema_version: RecordSchemaVersion("AssemblyDefinition")
    family: AssemblyFamily
    label: Slug
    installation_note: str
    unverified_climate_details: list[str]
    layers: Annotated[list[Layer], Field(min_length=1)]  # exterior to interior


class Wall(_Record):
    """A generated wall in one perimeter bay of one story (D065; MODEL-006 §4.4)."""

    kind: Literal["Wall"]
    schema_version: RecordSchemaVersion("Wall")
    generation_key: str
    level_id: Uuid
    start_m: Point3
    end_m: Point3
    height_m: float
    assembly_definition_id: Uuid
    framing_ids: list[Uuid]  # ascending generation_key


class WallFramingPiece(_Record):
    """One generated wall framing piece (D066; MODEL-006 §4.5). No connection records."""

    kind: Literal["WallFramingPiece"]
    schema_version: RecordSchemaVersion("WallFramingPiece")
    generation_key: str
    piece_kind: PieceKind
    opening_id: Uuid | None
    start_m: Point3
    end_m: Point3
    section_id: Uuid
    material_id: Uuid


class Opening(_Record):
    """A user-authored rough opening, a void, not a product (D069; MODEL-006 §4.6)."""

    kind: Literal["Opening"]
    schema_version: RecordSchemaVersion("Opening")
    opening_kind: OpeningKind
    wall_id: Uuid
    width_m: float
    height_m: float
    sill_height_m: float
    offset_m: float


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
        WallSystem,
        AssemblyDefinition,
        Wall,
        WallFramingPiece,
        Opening,
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
        "WallSystem",
        "AssemblyDefinition",
        "Wall",
        "WallFramingPiece",
        "Opening",
    }
)


class Snapshot(_Strict):
    """A semantic snapshot, model schema version 3 (building-model.md §3, §3.3, §3.4)."""

    model_config = ConfigDict(
        title="Semantic building snapshot (model schema version 3)",
    )

    model_schema_version: ModelSchemaVersion
    project_id: Uuid
    revision_id: Uuid
    parent_revision_id: Uuid | None
    created_at: Timestamp
    building: Building
    entities: list[Entity]
