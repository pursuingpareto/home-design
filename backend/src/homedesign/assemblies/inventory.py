"""Value types shared by wall rules and model validation, and the rule-independent conformance
comparison for walls and wall framing (MODEL-006 §6.5, §7; D046).

A wall rule supplies only what it generates. Comparing that with a snapshot's stored walls and
pieces is the same for every rule, so it lives here once, as ``timber/inventory.py`` does for
members and connections.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from homedesign.model import codes
from homedesign.timber.inventory import ConformanceIssue

if TYPE_CHECKING:
    from homedesign.model.schema import Snapshot

Point3 = tuple[float, float, float]
COORDINATE_EPSILON_M = 1e-6  # D026

# D076: the definition's framing field each piece kind takes its section from. A schema-level
# contract (MODEL-006 §4.3), used to name the definition field in conformance findings.
SECTION_FIELD = {
    "STUD": "stud_section_id",
    "KING": "stud_section_id",
    "JACK": "stud_section_id",
    "CRIPPLE": "stud_section_id",
    "ROUGH_SILL": "stud_section_id",
    "GIRT": "girt_section_id",
    "HEADER": "header_section_id",
    "BUCK_JAMB": "buck_section_id",
    "BUCK_HEAD": "buck_section_id",
    "BUCK_SILL": "buck_section_id",
}


def _utf16(text: str) -> bytes:
    return text.encode("utf-16-be")


@dataclass(frozen=True)
class GeneratedWall:
    """A wall as a rule defines it, without an ID (IDs are minted from the key, D041)."""

    generation_key: str
    level_id: str
    level_index: int
    axis: str  # "x" or "y": the axis the wall runs along
    start_m: Point3
    end_m: Point3
    height_m: float
    assembly_definition_id: str

    @property
    def length_m(self) -> float:
        """W, the wall's length from start post axis to end post axis (``B - A``)."""
        index = 0 if self.axis == "x" else 1
        return self.end_m[index] - self.start_m[index]

    def to_json(self, framing_ids: list[str]) -> dict[str, Any]:
        """Record fields, with ``framing_ids`` resolved by the caller."""
        return {
            "generation_key": self.generation_key,
            "level_id": self.level_id,
            "start_m": list(self.start_m),
            "end_m": list(self.end_m),
            "height_m": self.height_m,
            "assembly_definition_id": self.assembly_definition_id,
            "framing_ids": list(framing_ids),
        }


@dataclass(frozen=True)
class GeneratedFramingPiece:
    """A wall framing piece as a rule defines it. Its wall is named by key, its opening by ID."""

    generation_key: str
    wall_key: str
    piece_kind: str
    opening_id: str | None
    start_m: Point3
    end_m: Point3
    section_id: str
    material_id: str

    def to_json(self) -> dict[str, Any]:
        return {
            "generation_key": self.generation_key,
            "piece_kind": self.piece_kind,
            "opening_id": self.opening_id,
            "start_m": list(self.start_m),
            "end_m": list(self.end_m),
            "section_id": self.section_id,
            "material_id": self.material_id,
        }


@dataclass(frozen=True)
class FramedOpening:
    """An opening's framed rectangle ``[u0, u1] × [v0, v1]`` in its wall's (u, v) (MODEL-006 §5.1; D076)."""

    opening_id: str
    wall_key: str
    u0: float
    u1: float
    v0: float
    v1: float


@dataclass(frozen=True)
class WallInventory:
    """Everything a wall rule generates for one snapshot, built in one pass (ASM-001 §12)."""

    walls: tuple[GeneratedWall, ...]
    framing: tuple[GeneratedFramingPiece, ...]
    # Openings whose wall the rule generates, by opening ID.
    framed_openings: Mapping[str, FramedOpening] = field(default_factory=dict)
    # Girt axis heights v_i per wall key; empty for walls without girts.
    girt_heights: Mapping[str, tuple[float, ...]] = field(default_factory=dict)


def _differs(a: Iterable[float], b: Iterable[float]) -> bool:
    return any(abs(u - v) > COORDINATE_EPSILON_M for u, v in zip(a, b))


def _by_id(snapshot: "Snapshot") -> dict[str, Any]:
    by_id: dict[str, Any] = {}
    for entity in snapshot.entities:
        by_id.setdefault(entity.id, entity)
    return by_id


def _framing_layer(definition: Any) -> tuple[int, Any] | None:
    for k, layer in enumerate(definition.layers):
        if layer.framing is not None:
            return k, layer
    return None


def wall_conformance(snapshot: "Snapshot", generated: Iterable[GeneratedWall]) -> list[ConformanceIssue]:
    """Compare the snapshot's walls with a rule's output (MODEL-006 §6.5)."""
    by_id = _by_id(snapshot)
    system = by_id[snapshot.building.wall_system_id]
    expected = {w.generation_key: w for w in generated}
    actual = {e.generation_key: e for e in snapshot.entities if e.kind == "Wall"}
    issues: list[ConformanceIssue] = []

    for key in sorted(expected.keys() - actual.keys(), key=_utf16):
        issues.append(ConformanceIssue(codes.MISSING_GENERATED_WALL, system.id, ("wall_ids",), f"The rule generates wall {key}, but no wall has that key.", key))
    for key in sorted(actual.keys() - expected.keys(), key=_utf16):
        issues.append(ConformanceIssue(codes.UNEXPECTED_WALL, actual[key].id, ("generation_key",), f"The rule does not generate wall {key}.", key))
    for key in sorted(expected.keys() & actual.keys(), key=_utf16):
        want, have = expected[key], actual[key]
        for name in ("start_m", "end_m"):
            if _differs(getattr(have, name), getattr(want, name)):
                issues.append(ConformanceIssue(codes.WALL_GEOMETRY_MISMATCH, have.id, (name,), f"{name} differs from the rule by more than 1e-6 m."))
        if abs(have.height_m - want.height_m) > COORDINATE_EPSILON_M:
            issues.append(ConformanceIssue(codes.WALL_GEOMETRY_MISMATCH, have.id, ("height_m",), "height_m differs from the rule by more than 1e-6 m.", have.height_m))
        if have.level_id != want.level_id:
            issues.append(ConformanceIssue(codes.WALL_ASSIGNMENT_MISMATCH, have.id, ("level_id",), f"The rule places {key} on level {want.level_index}.", have.level_id))
        if have.assembly_definition_id != want.assembly_definition_id:
            issues.append(ConformanceIssue(
                codes.WALL_ASSIGNMENT_MISMATCH, have.id, ("assembly_definition_id",),
                "assembly_definition_id must equal the wall system's default_assembly_definition_id (D068).",
                have.assembly_definition_id,
                ((system.id, ("default_assembly_definition_id",)),),
            ))
    return issues


def framing_conformance(snapshot: "Snapshot", generated: Iterable[GeneratedFramingPiece]) -> list[ConformanceIssue]:
    """Compare the snapshot's wall framing with a rule's output, once walls conform (MODEL-006 §6.5)."""
    by_id = _by_id(snapshot)
    walls = {e.generation_key: e for e in snapshot.entities if e.kind == "Wall"}
    owner: dict[str, Any] = {}  # piece ID -> the wall that lists it (the first by ID; stage 2 rejects two)
    for wall in sorted(walls.values(), key=lambda w: w.id):
        for piece_id in wall.framing_ids:
            owner.setdefault(piece_id, wall)
    expected = {p.generation_key: p for p in generated}
    actual = {e.generation_key: e for e in snapshot.entities if e.kind == "WallFramingPiece"}
    issues: list[ConformanceIssue] = []

    for key in sorted(expected.keys() - actual.keys(), key=_utf16):
        wall = walls[expected[key].wall_key]
        issues.append(ConformanceIssue(codes.MISSING_GENERATED_FRAMING, wall.id, ("framing_ids",), f"The rule generates piece {key}, but no piece has that key.", key))
    for key in sorted(actual.keys() - expected.keys(), key=_utf16):
        issues.append(ConformanceIssue(codes.UNEXPECTED_FRAMING, actual[key].id, ("generation_key",), f"The rule does not generate piece {key}.", key))
    for key in sorted(expected.keys() & actual.keys(), key=_utf16):
        want, have = expected[key], actual[key]
        wall = walls[want.wall_key]
        definition = by_id.get(wall.assembly_definition_id)
        located = _framing_layer(definition) if definition is not None else None
        for name, point in (("start_m", want.start_m), ("end_m", want.end_m)):
            if _differs(getattr(have, name), point):
                issues.append(ConformanceIssue(codes.FRAMING_GEOMETRY_MISMATCH, have.id, (name,), f"{name} differs from the rule by more than 1e-6 m."))
        if have.piece_kind != want.piece_kind:
            issues.append(ConformanceIssue(codes.FRAMING_ASSIGNMENT_MISMATCH, have.id, ("piece_kind",), f"The rule makes {key} a {want.piece_kind}.", have.piece_kind))
        if have.opening_id != want.opening_id:
            issues.append(ConformanceIssue(codes.FRAMING_ASSIGNMENT_MISMATCH, have.id, ("opening_id",), "opening_id differs from the opening the rule frames with this piece.", have.opening_id))
        for name, source in (("section_id", SECTION_FIELD.get(want.piece_kind)), ("material_id", "framing_material_id")):
            if getattr(have, name) != getattr(want, name):
                related = ((definition.id, ("layers", located[0], "framing", source)),) if located is not None and source else ()
                issues.append(ConformanceIssue(
                    codes.FRAMING_ASSIGNMENT_MISMATCH, have.id, (name,),
                    f"{name} must equal the wall definition's framing {source} (D066).",
                    getattr(have, name),
                    related,
                ))
        listed_by = owner.get(have.id)
        if listed_by is not None and listed_by.generation_key != want.wall_key:
            issues.append(ConformanceIssue(
                codes.FRAMING_ASSIGNMENT_MISMATCH, listed_by.id, ("framing_ids",),
                f"Piece {key} belongs to wall {want.wall_key}.",
                key,
                ((wall.id, ("framing_ids",)),),
            ))
    return issues
