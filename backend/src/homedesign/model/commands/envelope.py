"""Typed command envelopes and arguments (D043, D044; interfaces.md §2, §2.1).

Arguments are strict: every listed key is required, unknown keys are rejected, and
values are canonical units (meters, radians; D026).
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, model_validator
from pydantic_core import PydanticCustomError

from .. import codes
from ..paths import render
from ..schema import MemberRole, Uuid
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


class GridLineArg(_Strict):
    """Either ``{"id", "fraction"}`` (keep an existing line) or ``{"fraction"}`` (new line)."""

    id: str | None = None
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
    "SetFootprintDimensions",
    "SetGableRoofParameters",
    "SetMemberSection",
    "SetStoryHeights",
    "SetTimberGrid",
    "UndoToRevision",
    "parse_command",
    "reject",
]
