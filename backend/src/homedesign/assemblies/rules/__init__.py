"""Wall-rule registry keyed by ``WallSystem.generation_rule_version`` (MODEL-006 §7).

Model validation reaches wall rules only through this registry, as it reaches frame rules through
``homedesign.timber.rules``; the model module holds no rule logic (interfaces.md §1). Under D055
only the newest rule is registered.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from homedesign.timber.inventory import ConformanceIssue

from ..inventory import (
    FramedOpening,
    GeneratedFramingPiece,
    GeneratedWall,
    WallInventory,
    framing_conformance,
    wall_conformance,
)

if TYPE_CHECKING:
    from homedesign.model.schema import Snapshot


@dataclass(frozen=True)
class WallRule:
    version: str
    # One pass over a snapshot that passes stages 1-3: walls sorted by key, their pieces sorted by
    # key, each opening's framed rectangle, and each wall's girt heights (MODEL-006 §7). No IDs.
    # Total: never raises on such a snapshot, even when it will fail the fit at stage 4.
    build: Callable[["Snapshot"], WallInventory]

    def generate_walls(self, snapshot: "Snapshot") -> tuple[GeneratedWall, ...]:
        return self.build(snapshot).walls

    def generate_framing(self, snapshot: "Snapshot") -> tuple[GeneratedFramingPiece, ...]:
        return self.build(snapshot).framing

    def framed_openings(self, snapshot: "Snapshot") -> Mapping[str, FramedOpening]:
        return self.build(snapshot).framed_openings

    def girt_heights(self, snapshot: "Snapshot") -> Mapping[str, tuple[float, ...]]:
        return self.build(snapshot).girt_heights

    def conformance(self, snapshot: "Snapshot", inventory: WallInventory | None = None) -> list[ConformanceIssue]:
        """Walls first; wall framing only once the walls conform (MODEL-006 §6.5)."""
        inventory = inventory or self.build(snapshot)
        issues = wall_conformance(snapshot, inventory.walls)
        if not issues:
            issues = framing_conformance(snapshot, inventory.framing)
        return issues


_REGISTRY: dict[str, WallRule] = {}


def register(rule: WallRule) -> None:
    if rule.version in _REGISTRY:
        raise ValueError(f"wall rule {rule.version!r} is already registered")
    _REGISTRY[rule.version] = rule


def get_wall_rule(version: str) -> WallRule | None:
    return _REGISTRY.get(version)


def registered_versions() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))


from . import vs02b_walls_1 as _vs02b_walls_1  # noqa: E402  (registers itself)

__all__ = ["WallRule", "get_wall_rule", "register", "registered_versions"]
