"""Generation-rule registry keyed by ``generation_rule_version`` (TIMBER-001 §6, TIMBER-002 §6).

Model validation reaches rules only through this registry; new rule versions are
added by registering them here. Under D055 only the newest rule is registered.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..inventory import ConformanceIssue, GeneratedConnection, GeneratedMember, connection_conformance, member_conformance

if TYPE_CHECKING:
    from homedesign.model.schema import Snapshot


@dataclass(frozen=True)
class Rule:
    version: str
    generated_roles: frozenset[str]
    generated_junction_classes: frozenset[str]
    generate: Callable[["Snapshot"], tuple[GeneratedMember, ...]]
    # Connections for a snapshot whose members conform; keyed to members by generation key.
    generate_connections: Callable[["Snapshot"], tuple[GeneratedConnection, ...]]

    def conformance(self, snapshot: "Snapshot") -> list[ConformanceIssue]:
        """Members first; connections only once the members conform (D046, MODEL-005 §6.5)."""
        issues = member_conformance(snapshot, self.generate(snapshot))
        if not issues:
            issues = connection_conformance(snapshot, self.generate_connections(snapshot))
        return issues


_REGISTRY: dict[str, Rule] = {}


def register(rule: Rule) -> None:
    if rule.version in _REGISTRY:
        raise ValueError(f"rule {rule.version!r} is already registered")
    _REGISTRY[rule.version] = rule


def get_rule(version: str) -> Rule | None:
    return _REGISTRY.get(version)


def registered_versions() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))


from . import vs02_frame_1 as _vs02_frame_1  # noqa: E402  (registers itself)

__all__ = ["Rule", "get_rule", "register", "registered_versions"]
