"""Generation-rule registry keyed by ``generation_rule_version`` (TIMBER-001 §6).

Model validation reaches rules only through this registry; new rule versions are
added by registering them here.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..inventory import ConformanceIssue, GeneratedMember

if TYPE_CHECKING:
    from homedesign.model.schema import Snapshot


@dataclass(frozen=True)
class Rule:
    version: str
    generated_roles: frozenset[str]
    generate: Callable[["Snapshot"], tuple[GeneratedMember, ...]]
    conformance: Callable[["Snapshot"], list[ConformanceIssue]]


_REGISTRY: dict[str, Rule] = {}


def register(rule: Rule) -> None:
    if rule.version in _REGISTRY:
        raise ValueError(f"rule {rule.version!r} is already registered")
    _REGISTRY[rule.version] = rule


def get_rule(version: str) -> Rule | None:
    return _REGISTRY.get(version)


def registered_versions() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))


from . import vs01_post_beam_1 as _vs01_post_beam_1  # noqa: E402  (registers itself)

__all__ = ["Rule", "get_rule", "register", "registered_versions"]
