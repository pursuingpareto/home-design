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


def allowed(junction_class: str, connection_type: str) -> bool:
    return connection_type in ALLOWED.get(junction_class, frozenset())
