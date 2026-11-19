"""`timber_schedule` payload and builder (artifacts.md §7; EST-001 §3).

One row per stored member; lengths are reference-axis lengths computed as
sqrt(dx*dx + dy*dy + dz*dz) exactly as written (artifacts.md §7); one aggregate per
(role, nominal_section), unique by D049, summed in generation_key order (C6).
"""

from __future__ import annotations

import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from homedesign.dependencies.registry import Derivation, DerivationContext, Outcome
from homedesign.model.schema import Snapshot, Uuid

ASSUMPTIONS = (
    {"code": "REFERENCE_AXIS_LENGTH", "message": "Lengths are reference-axis distances, not fabrication cut lengths."},
    {"code": "NO_CONNECTIONS", "message": "Joinery and machining are not included."},
)


class _Strict(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", allow_inf_nan=False, frozen=True)


class ScheduleUnits(_Strict):
    length: Literal["m"] = "m"
    count: Literal["1"] = "1"


class Assumption(_Strict):
    code: str
    message: str


class ScheduleRow(_Strict):
    member_id: Uuid
    generation_key: str
    role: Literal["POST", "BEAM", "FLOOR_JOIST", "RAFTER"]
    nominal_section: str
    section_id: Uuid
    material_id: Uuid
    species: str | None
    grade: str | None
    length_m: float
    quantity: Literal[1] = 1


class ScheduleAggregate(_Strict):
    role: Literal["POST", "BEAM", "FLOOR_JOIST", "RAFTER"]
    nominal_section: str
    count: int
    total_length_m: float


class TimberSchedulePayload(_Strict):
    model_config = ConfigDict(title="timber_schedule payload (artifacts.md §7)")

    units: ScheduleUnits = ScheduleUnits()
    length_basis: Literal["reference_axis"] = "reference_axis"
    assumptions: list[Assumption]
    members: list[ScheduleRow]
    aggregates: list[ScheduleAggregate]


def _utf16(text: str) -> bytes:
    return text.encode("utf-16-be")


def reference_length(start: list[float], end: list[float]) -> float:
    """sqrt(dx*dx + dy*dy + dz*dz), evaluated exactly as written (no hypot/dist)."""
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    dz = end[2] - start[2]
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def build_schedule(snapshot: Snapshot) -> dict[str, Any]:
    by_id = {e.id: e for e in snapshot.entities}
    members = sorted((e for e in snapshot.entities if e.kind == "TimberMember"), key=lambda m: _utf16(m.generation_key))
    rows = []
    totals: dict[tuple[str, str], list] = {}
    for member in members:
        section, material = by_id[member.section_id], by_id[member.material_id]
        length = reference_length(member.start_m, member.end_m)
        rows.append({
            "member_id": member.id,
            "generation_key": member.generation_key,
            "role": member.member_role,
            "nominal_section": section.nominal_label,
            "section_id": section.id,
            "material_id": material.id,
            "species": material.species,
            "grade": material.grade,
            "length_m": length,
            "quantity": 1,
        })
        entry = totals.setdefault((member.member_role, section.nominal_label), [0, 0.0])
        entry[0] += 1
        entry[1] += length  # summed in generation_key order (C6)
    aggregates = [
        {"role": role, "nominal_section": label, "count": count, "total_length_m": total}
        for (role, label), (count, total) in sorted(totals.items(), key=lambda kv: (_utf16(kv[0][0]), _utf16(kv[0][1])))
    ]
    payload = {"assumptions": [dict(a) for a in ASSUMPTIONS], "members": rows, "aggregates": aggregates}
    return TimberSchedulePayload.model_validate(payload).model_dump(mode="json")


def _derive(context: DerivationContext) -> Outcome:
    return Outcome("CURRENT", build_schedule(context.snapshot))


SCHEDULE = Derivation("timber_schedule", "schedule-vs01", "1", _derive)
