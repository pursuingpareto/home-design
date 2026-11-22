"""Derivation registry (ART-001 §3; DEP-001 §4).

Artifact content comes from derivations registered by GEOM-001 and EST-001. A type with
no registered derivation is always reported as MISSING (never invented, artifacts.md §2.1).

Every derivation declares a pure selector (D056, D061). The selector extracts exactly what the
derivation reads; the selection is fingerprinted, and it is the derivation's only model input.
The selectors are the dependency graph: impact is computed by comparing selections' fingerprints.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any, Literal

# artifacts.md §1: every manifest lists exactly these, in this order (VS-02b adds `assembly_schedule`, ART-003 §8.2).
ARTIFACT_TYPES: tuple[str, ...] = ("plan2d", "mesh3d", "timber_schedule", "assembly_schedule", "preliminary_estimate")


@dataclass(frozen=True)
class Outcome:
    status: Literal["CURRENT", "UNAVAILABLE", "FAILED"]
    payload: dict[str, Any] | None = None
    warnings: tuple[dict[str, str], ...] = ()
    error: dict[str, str] | None = None


@dataclass(frozen=True)
class DerivationContext:
    """What a derivation may read (D061 item 9): its selection and its external inputs. No snapshot."""

    project_id: str
    selection: Any  # the derivation's own selection (DEP-001 §4.2)
    external: dict[str, Any]  # inputs from outside the snapshot (e.g. the price book, EST-001)


# A selector receives the snapshot when the derivation has no dependencies, and otherwise the
# outcomes of its declared dependencies for the same revision, by type (DEP-001 §4.2: the estimate
# selects from the schedule's outcome, never from the snapshot). It must be pure and return I-JSON.
Selector = Callable[[Any], Any]


@dataclass(frozen=True)
class Derivation:
    artifact_type: str
    generator_id: str
    generator_version: str
    select: Selector  # Snapshot -> selection, or {dependency: Outcome} -> selection (see Selector)
    derive: Callable[[DerivationContext], Outcome]
    depends_on: tuple[str, ...] = ()
    # Returns extra inputs from outside the snapshot, given (tx, project_id). Keys are merged into
    # the fingerprint input object (DEP-001 §5), except keys starting with "_", which are context only and must
    # be fully determined by the fingerprinted keys. All keys are passed as context.external.
    external_inputs: Callable[[Any, str], dict[str, Any]] | None = None


@dataclass
class Registry:
    derivations: dict[str, Derivation] = field(default_factory=dict)

    def register(self, derivation: Derivation) -> None:
        if derivation.artifact_type not in ARTIFACT_TYPES:
            raise ValueError(f"unknown artifact type {derivation.artifact_type!r}")
        for dependency in derivation.depends_on:
            if dependency not in ARTIFACT_TYPES:
                raise ValueError(f"unknown dependency {dependency!r}")
        self.derivations[derivation.artifact_type] = derivation

    def ordered(self) -> list[Derivation]:
        """Registered derivations in dependency order (dependencies.md §6: topological)."""
        order: list[Derivation] = []
        seen: set[str] = set()

        def visit(kind: str, stack: tuple[str, ...]) -> None:
            if kind in seen or kind not in self.derivations:
                return
            if kind in stack:
                raise ValueError(f"dependency cycle through {kind!r}")
            for dependency in self.derivations[kind].depends_on:
                visit(dependency, (*stack, kind))
            seen.add(kind)
            order.append(self.derivations[kind])

        for kind in ARTIFACT_TYPES:
            visit(kind, ())
        return order


def registry_of(derivations: Iterable[Derivation]) -> Registry:
    registry = Registry()
    for derivation in derivations:
        registry.register(derivation)
    return registry


def default_registry() -> Registry:
    """Production registry: GEOM-001 views, EST-001 schedule and estimate, and ART-003's assembly schedule."""
    from homedesign.assemblies.schedule import ASSEMBLY_SCHEDULE  # lazy: these modules import this one
    from homedesign.estimating import ESTIMATE
    from homedesign.geometry import MESH3D, PLAN2D
    from homedesign.timber.schedule import SCHEDULE

    return registry_of([PLAN2D, MESH3D, SCHEDULE, ASSEMBLY_SCHEDULE, ESTIMATE])
