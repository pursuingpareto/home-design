"""The VS-02 connection catalog (D054; MODEL-005 §4.4).

One definition of junction classes, connection types, and which types each class
allows, shared by validation, connection generation (CONN-001), and payloads (ART-002).
Types are representational only: they carry no capacity, fastener, or machining claim.
"""

from __future__ import annotations

from typing import Literal, get_args

CATALOG_VERSION = "vs02-connections-1"

JunctionClass = Literal["post-beam", "post-sill", "brace", "joist-beam", "rafter-peak", "rafter-foot", "purlin-rafter"]
ConnectionType = Literal["PEGGED_MORTISE_TENON", "BRIDLE", "HOUSED_DOVETAIL", "STEEL_KNIFE_PLATE", "JOIST_HANGER"]

JUNCTION_CLASSES: tuple[str, ...] = get_args(JunctionClass)
CONNECTION_TYPES: tuple[str, ...] = get_args(ConnectionType)

# D054: every class defaults to its traditional type and allows exactly one engineered alternative.
DEFAULTS: dict[str, str] = {
    "post-beam": "PEGGED_MORTISE_TENON",
    "post-sill": "PEGGED_MORTISE_TENON",
    "brace": "PEGGED_MORTISE_TENON",
    "joist-beam": "HOUSED_DOVETAIL",
    "rafter-peak": "BRIDLE",
    "rafter-foot": "PEGGED_MORTISE_TENON",
    "purlin-rafter": "PEGGED_MORTISE_TENON",
}
ALTERNATIVES: dict[str, str] = {
    "post-beam": "STEEL_KNIFE_PLATE",
    "post-sill": "STEEL_KNIFE_PLATE",
    "brace": "STEEL_KNIFE_PLATE",
    "joist-beam": "JOIST_HANGER",
    "rafter-peak": "STEEL_KNIFE_PLATE",
    "rafter-foot": "STEEL_KNIFE_PLATE",
    "purlin-rafter": "STEEL_KNIFE_PLATE",
}
ALLOWED: dict[str, frozenset[str]] = {c: frozenset({DEFAULTS[c], ALTERNATIVES[c]}) for c in JUNCTION_CLASSES}


# ART-002 §6.3: a family (vs-02.md §9.2) and a description per type, carried by the schedule for the
# types it lists. Every description says the type is representational only (D054, AC2-07).
_REPRESENTATIONAL = "Representational only: no capacity, sizes, or fasteners."
FAMILIES: dict[str, str] = {
    "PEGGED_MORTISE_TENON": "traditional",
    "BRIDLE": "traditional",
    "HOUSED_DOVETAIL": "traditional",
    "STEEL_KNIFE_PLATE": "engineered",
    "JOIST_HANGER": "engineered",
}
DESCRIPTIONS: dict[str, str] = {
    "PEGGED_MORTISE_TENON": f"Pegged mortise and tenon. {_REPRESENTATIONAL}",
    "BRIDLE": f"Bridle joint. {_REPRESENTATIONAL}",
    "HOUSED_DOVETAIL": f"Housed dovetail. {_REPRESENTATIONAL}",
    "STEEL_KNIFE_PLATE": f"Concealed steel knife plate with dowels. {_REPRESENTATIONAL}",
    "JOIST_HANGER": f"Joist hanger. {_REPRESENTATIONAL}",
}


def allowed(junction_class: str, connection_type: str) -> bool:
    return connection_type in ALLOWED.get(junction_class, frozenset())
