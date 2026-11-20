"""Value types shared by generation rules and model validation, and the rule-independent
conformance comparison (D046; TIMBER-002 §6).

A rule supplies only what it generates. Comparing that with a snapshot's stored members and
connections is the same for every rule, so it lives here once.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Iterable

from homedesign.model import codes

if TYPE_CHECKING:
    from homedesign.model.schema import Snapshot

Point3 = tuple[float, float, float]
COORDINATE_EPSILON_M = 1e-6  # D026


def _utf16(text: str) -> bytes:
    return text.encode("utf-16-be")


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
class GeneratedConnection:
    """A connection as a rule defines it (D054). Members are named by generation key, not ID."""

    generation_key: str
    junction_class: str
    connection_type: str
    member_keys: tuple[str, str]  # (receiving, entering)
    location_m: Point3

    def to_json(self, member_ids: tuple[str, str] | list[str]) -> dict[str, Any]:
        """Record fields, with ``member_ids`` resolved from ``member_keys`` by the caller."""
        return {
            "generation_key": self.generation_key,
            "junction_class": self.junction_class,
            "connection_type": self.connection_type,
            "member_ids": list(member_ids),
            "location_m": list(self.location_m),
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


def _differs(a: Iterable[float], b: Iterable[float]) -> bool:
    return any(abs(u - v) > COORDINATE_EPSILON_M for u, v in zip(a, b))


def _frame(snapshot: "Snapshot") -> Any:
    return next(e for e in snapshot.entities if e.id == snapshot.building.frame_system_id)


def member_conformance(snapshot: "Snapshot", generated: Iterable[GeneratedMember]) -> list[ConformanceIssue]:
    """Compare the snapshot's members with a rule's output (D046)."""
    frame = _frame(snapshot)
    expected = {m.generation_key: m for m in generated}
    actual = {e.generation_key: e for e in snapshot.entities if e.kind == "TimberMember"}
    issues: list[ConformanceIssue] = []

    for key in sorted(expected.keys() - actual.keys(), key=_utf16):
        issues.append(ConformanceIssue(codes.MISSING_GENERATED_MEMBER, frame.id, ("member_ids",), f"The rule generates {key}, but no member has that key.", key))
    for key in sorted(actual.keys() - expected.keys(), key=_utf16):
        issues.append(ConformanceIssue(codes.UNEXPECTED_MEMBER, actual[key].id, ("generation_key",), f"The rule does not generate {key}.", key))
    for key in sorted(expected.keys() & actual.keys(), key=_utf16):
        want, have = expected[key], actual[key]
        if have.member_role != want.member_role:
            issues.append(ConformanceIssue(codes.MEMBER_ASSIGNMENT_MISMATCH, have.id, ("member_role",), f"The rule assigns role {want.member_role} to {key}.", have.member_role))
        for field in ("section_id", "material_id"):
            if getattr(have, field) != getattr(want, field):
                issues.append(ConformanceIssue(
                    codes.MEMBER_ASSIGNMENT_MISMATCH, have.id, (field,),
                    f"{field} must equal member_defaults.{want.member_role}.{field} (D039).",
                    getattr(have, field),
                    ((frame.id, ("member_defaults", want.member_role, field)),),
                ))
        for field, point in (("start_m", want.start_m), ("end_m", want.end_m)):
            if _differs(getattr(have, field), point):
                issues.append(ConformanceIssue(codes.MEMBER_GEOMETRY_MISMATCH, have.id, (field,), f"{field} differs from the rule by more than 1e-6 m."))
    return issues


def connection_conformance(snapshot: "Snapshot", generated: Iterable[GeneratedConnection]) -> list[ConformanceIssue]:
    """Compare the snapshot's connections with a rule's output (MODEL-005 §6.5)."""
    frame = _frame(snapshot)
    member_ids = {e.generation_key: e.id for e in snapshot.entities if e.kind == "TimberMember"}
    expected = {c.generation_key: c for c in generated}
    actual = {e.generation_key: e for e in snapshot.entities if e.kind == "Connection"}
    issues: list[ConformanceIssue] = []

    for key in sorted(expected.keys() - actual.keys(), key=_utf16):
        issues.append(ConformanceIssue(codes.MISSING_GENERATED_CONNECTION, frame.id, ("connection_ids",), f"The rule generates connection {key}, but no connection has that key.", key))
    for key in sorted(actual.keys() - expected.keys(), key=_utf16):
        issues.append(ConformanceIssue(codes.UNEXPECTED_CONNECTION, actual[key].id, ("generation_key",), f"The rule does not generate connection {key}.", key))
    for key in sorted(expected.keys() & actual.keys(), key=_utf16):
        want, have = expected[key], actual[key]
        if have.junction_class != want.junction_class:
            issues.append(ConformanceIssue(codes.CONNECTION_ASSIGNMENT_MISMATCH, have.id, ("junction_class",), f"The rule assigns junction class {want.junction_class} to {key}.", have.junction_class))
        want_ids = [member_ids.get(k) for k in want.member_keys]
        if list(have.member_ids) != want_ids:
            issues.append(ConformanceIssue(codes.CONNECTION_ASSIGNMENT_MISMATCH, have.id, ("member_ids",), f"The rule joins {want.member_keys[0]} (receiving) and {want.member_keys[1]} (entering)."))
        if have.connection_type != want.connection_type:
            issues.append(ConformanceIssue(
                codes.CONNECTION_ASSIGNMENT_MISMATCH, have.id, ("connection_type",),
                f"connection_type must equal connection_defaults.{want.junction_class} (D054).",
                have.connection_type,
                ((frame.id, ("connection_defaults", want.junction_class)),),
            ))
        if _differs(have.location_m, want.location_m):
            issues.append(ConformanceIssue(codes.CONNECTION_GEOMETRY_MISMATCH, have.id, ("location_m",), "location_m differs from the rule by more than 1e-6 m."))
    return issues
