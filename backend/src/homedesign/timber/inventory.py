"""Value types shared by generation rules and model validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

Point3 = tuple[float, float, float]


@dataclass(frozen=True)
class GeneratedMember:
    """A member as a rule defines it, without an ID (IDs are assigned by MODEL-003, D041)."""

    generation_key: str
    member_role: str
    start_m: Point3
    end_m: Point3
    section_id: str
    material_id: str

    def to_json(self) -> dict[str, Any]:
        return {
            "generation_key": self.generation_key,
            "member_role": self.member_role,
            "start_m": list(self.start_m),
            "end_m": list(self.end_m),
            "section_id": self.section_id,
            "material_id": self.material_id,
        }


@dataclass(frozen=True)
class ConformanceIssue:
    """A stage-5 finding, addressed by entity ID and field steps (D046).

    Model validation renders these into D036 paths; the timber module does not
    depend on how paths are written.
    """

    code: str
    entity_id: str
    field: tuple[str | int, ...]
    message: str
    value: Any = None
    related: tuple[tuple[str, tuple[str | int, ...]], ...] = ()
