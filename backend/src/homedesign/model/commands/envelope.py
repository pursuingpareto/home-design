"""Typed command envelopes and arguments (D043, D044; interfaces.md §2, §2.1).

Arguments are strict: every listed key is required, unknown keys are rejected, and
values are canonical units (meters, radians; D026).
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, model_validator
from pydantic.json_schema import SkipJsonSchema
from pydantic_core import PydanticCustomError

from .. import codes
from ..connections import ConnectionType, JunctionClass
from ..paths import render
from ..schema import MemberRole, SafeInt, Uuid
from ..validation import Issue, ValidationResult, _Collector, code_for_pydantic_error, message_for


class _Strict(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", allow_inf_nan=False, frozen=True)


# --- arguments ---------------------------------------------------------------


class NoArgs(_Strict):
    pass


class FootprintArgs(_Strict):
    width_m: float
    depth_m: float


class StoryHeightsArgs(_Strict):
    story_heights_m: Annotated[list[float], Field(min_length=2, max_length=2)]


class GableRoofArgs(_Strict):
    pitch_rad: float
    eave_overhang_m: float


def _drop_default(schema: dict[str, Any]) -> None:
    schema.pop("default", None)


class GridLineArg(_Strict):
    """Either ``{"id", "fraction"}`` (keep an existing line) or ``{"fraction"}`` (new line)."""

    # Optional and never null in the published schema, matching the validator below (UI-002).
    id: Annotated[str | SkipJsonSchema[None], Field(default=None, json_schema_extra=_drop_default)]
    fraction: float

    @model_validator(mode="before")
    @classmethod
    def _no_explicit_null_id(cls, data: Any) -> Any:
        if isinstance(data, dict) and "id" in data and data["id"] is None:
            raise PydanticCustomError("id_null", "Omit `id` for a new line instead of sending null.")
        return data


class TimberGridArgs(_Strict):
    x_lines: list[GridLineArg]
    y_lines: list[GridLineArg]


class MemberSectionArgs(_Strict):
    role: MemberRole
    section_id: Uuid


class ConnectionTypeArgs(_Strict):
    """D054, D059: a type per junction class, never per connection (CONN-001 §8.1)."""

    junction_class: JunctionClass
    connection_type: ConnectionType


class FrameParametersArgs(_Strict):
    """D057: every frame parameter, all required (MODEL-005 §7.1)."""

    joist_spacing_m: float
    purlins_per_slope: SafeInt
    knee_brace_leg_m: float
    knee_braces_level_1: bool
    knee_braces_eave: bool


class AddSectionArgs(_Strict):
    nominal_label: str
    actual_width_m: float
    actual_depth_m: float


class UndoArgs(_Strict):
    target_revision_id: Uuid


# --- envelopes ---------------------------------------------------------------


class _Command(_Strict):
    command_id: Uuid
    project_id: Uuid
    base_revision_id: Uuid


class CreateReferenceProject(_Strict):
    """Creation envelope: no project or base revision exists yet (interfaces.md §2)."""

    command_id: Uuid
    type: Literal["CreateReferenceProject"]
    args: NoArgs


class SetFootprintDimensions(_Command):
    type: Literal["SetFootprintDimensions"]
    args: FootprintArgs


class SetStoryHeights(_Command):
    type: Literal["SetStoryHeights"]
    args: StoryHeightsArgs


class SetGableRoofParameters(_Command):
    type: Literal["SetGableRoofParameters"]
    args: GableRoofArgs


class SetTimberGrid(_Command):
    type: Literal["SetTimberGrid"]
    args: TimberGridArgs


class SetMemberSection(_Command):
    type: Literal["SetMemberSection"]
    args: MemberSectionArgs


class SetFrameParameters(_Command):
    type: Literal["SetFrameParameters"]
    args: FrameParametersArgs


class SetConnectionType(_Command):
    type: Literal["SetConnectionType"]
    args: ConnectionTypeArgs


class AddSection(_Command):
    type: Literal["AddSection"]
    args: AddSectionArgs


class UndoToRevision(_Command):
    type: Literal["UndoToRevision"]
    args: UndoArgs


AnyCommand = Annotated[
    Union[
        CreateReferenceProject,
        SetFootprintDimensions,
        SetStoryHeights,
        SetGableRoofParameters,
        SetTimberGrid,
        SetMemberSection,
        SetFrameParameters,
        SetConnectionType,
        AddSection,
        UndoToRevision,
    ],
    Field(discriminator="type"),
]
COMMAND_ADAPTER: TypeAdapter = TypeAdapter(AnyCommand)
COMMAND_TYPES = frozenset(
    {
        "CreateReferenceProject",
        "SetFootprintDimensions",
        "SetStoryHeights",
        "SetGableRoofParameters",
        "SetTimberGrid",
        "SetMemberSection",
        "SetFrameParameters",
        "SetConnectionType",
        "AddSection",
        "UndoToRevision",
    }
)


def parse_command(raw: Any) -> tuple[Any | None, ValidationResult | None]:
    """Parse an envelope (stage 1, interfaces.md §7.1). Paths are under the envelope."""
    try:
        return COMMAND_ADAPTER.validate_python(raw), None
    except ValidationError as exc:
        out = _Collector()
        seen: set[tuple[str, str]] = set()
        for error in exc.errors(include_url=False):
            loc = list(error["loc"])
            if loc and loc[0] in COMMAND_TYPES:
                del loc[0]  # discriminator tag inserted by Pydantic
            raw_input = error.get("input")
            if error["type"] in ("union_tag_invalid", "union_tag_not_found"):
                loc = ["type"]
                code = codes.INVALID_ENUM if error["type"] == "union_tag_invalid" else codes.MISSING_FIELD
                raw_input = raw_input.get("type") if isinstance(raw_input, dict) else None
            elif error["type"] == "model_type" and not loc:
                code = codes.WRONG_TYPE
            else:
                code = code_for_pydantic_error(error)
            if error["type"] == "missing":
                raw_input = None
            path = render(loc)
            if (path, code) in seen:
                continue
            seen.add((path, code))
            out.add(path, code, message_for(code), raw_input)
        from ..codes import Stage

        return None, out.result(Stage.SYNTACTIC)


def reject(path: str, code: str, message: str, value: Any = None) -> ValidationResult:
    """A single-issue rejection whose top-level code follows the detail code's stage."""
    out = _Collector()
    out.add(path, code, message, value)
    return out.result(codes.CATALOG[code])


__all__ = [
    "AddSection",
    "COMMAND_ADAPTER",
    "COMMAND_TYPES",
    "CreateReferenceProject",
    "Issue",
    "SetConnectionType",
    "SetFootprintDimensions",
    "SetGableRoofParameters",
    "SetFrameParameters",
    "SetMemberSection",
    "SetStoryHeights",
    "SetTimberGrid",
    "UndoToRevision",
    "parse_command",
    "reject",
]
