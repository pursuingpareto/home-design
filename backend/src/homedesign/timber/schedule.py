"""`timber_schedule` payload and builder (artifacts.md §7; EST-001 §3; ART-002 §6).

One row per stored member; lengths are reference-axis lengths computed as
sqrt(dx*dx + dy*dy + dz*dz) exactly as written (artifacts.md §7); one aggregate per
(role, nominal_section), unique by D049, summed in generation_key order (C6).
One row per stored connection, without its location; one count per (junction_class,
connection_type) pair in use; and the catalog entries of the types in use (D054).
"""

from __future__ import annotations

import math
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from homedesign.dependencies.registry import Derivation, DerivationContext, Outcome
from homedesign.model.connections import CATALOG_VERSION, DESCRIPTIONS, FAMILIES, ConnectionType, JunctionClass
from homedesign.model.schema import MemberRole, Snapshot, Uuid

# ART-002 §6.4, in this order. The third line is the one D059 requires.
ASSUMPTIONS = (
    {"code": "REFERENCE_AXIS_LENGTH", "message": "Lengths are reference-axis distances, not fabrication cut lengths."},
    {"code": "CONNECTIONS_REPRESENTATIONAL",
     "message": "Connections are listed by type and count only. Types are representational: no capacity, sizes, fasteners, or machining."},
    {"code": "UNCLASSED_JOINTS_NOT_COUNTED",
     "message": "Joints without a junction class, such as post splices and sill joints at grid stations, are not counted."},
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
    role: MemberRole
    nominal_section: str
    section_id: Uuid
    material_id: Uuid
    species: str | None
    grade: str | None
    length_m: float
    quantity: Literal[1] = 1


class ScheduleAggregate(_Strict):
    role: MemberRole
    nominal_section: str
    count: int
    total_length_m: float


class ScheduleConnectionRow(_Strict):
    connection_id: Uuid
    generation_key: str
    junction_class: JunctionClass
    connection_type: ConnectionType
    member_ids: Annotated[list[Uuid], Field(min_length=2, max_length=2)]  # [receiving, entering] (D059)
    quantity: Literal[1] = 1


class ConnectionAggregate(_Strict):
    junction_class: JunctionClass
    connection_type: ConnectionType
    count: Annotated[int, Field(ge=1)]


class CatalogType(_Strict):
    connection_type: ConnectionType
    family: Literal["traditional", "engineered"]
    description: str


class ConnectionCatalog(_Strict):
    catalog_version: Literal["vs02-connections-1"]
    types: list[CatalogType]


class TimberSchedulePayload(_Strict):
    model_config = ConfigDict(title="timber_schedule payload (artifacts.md §7)")

    units: ScheduleUnits = ScheduleUnits()
    length_basis: Literal["reference_axis"] = "reference_axis"
    assumptions: list[Assumption]
    members: list[ScheduleRow]
    aggregates: list[ScheduleAggregate]
    connections: list[ScheduleConnectionRow]
    connection_aggregates: list[ConnectionAggregate]
    connection_catalog: ConnectionCatalog


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
    connections = sorted((e for e in snapshot.entities if e.kind == "Connection"), key=lambda c: _utf16(c.generation_key))
    connection_rows = []
    counts: dict[tuple[str, str], int] = {}
    for connection in connections:
        connection_rows.append({
            "connection_id": connection.id,
            "generation_key": connection.generation_key,
            "junction_class": connection.junction_class,
            "connection_type": connection.connection_type,
            "member_ids": list(connection.member_ids),
            "quantity": 1,
        })
        pair = (connection.junction_class, connection.connection_type)
        counts[pair] = counts.get(pair, 0) + 1
    connection_aggregates = [  # zero rows never arise: only pairs in use are counted (ART-002 §6.2)
        {"junction_class": cls, "connection_type": type_, "count": count}
        for (cls, type_), count in sorted(counts.items(), key=lambda kv: (_utf16(kv[0][0]), _utf16(kv[0][1])))
    ]
    used_types = sorted({type_ for _, type_ in counts}, key=_utf16)
    payload = {
        "assumptions": [dict(a) for a in ASSUMPTIONS],
        "members": rows,
        "aggregates": aggregates,
        "connections": connection_rows,
        "connection_aggregates": connection_aggregates,
        "connection_catalog": {
            "catalog_version": CATALOG_VERSION,
            "types": [{"connection_type": t, "family": FAMILIES[t], "description": DESCRIPTIONS[t]} for t in used_types],
        },
    }
    return TimberSchedulePayload.model_validate(payload).model_dump(mode="json")


def _derive(context: DerivationContext) -> Outcome:
    return Outcome("CURRENT", build_schedule(context.snapshot))


SCHEDULE = Derivation("timber_schedule", "schedule-vs01", "2", _derive)
