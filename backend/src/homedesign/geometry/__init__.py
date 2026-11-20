"""Display geometry derived from the semantic model (GEOM-001, ART-002): `plan2d`, `mesh3d`."""

from homedesign.dependencies.registry import Derivation, DerivationContext, Outcome

from .payloads import Mesh3dPayload, Plan2dPayload
from .views import build_mesh3d, build_plan2d


def _plan2d(context: DerivationContext) -> Outcome:
    return Outcome("CURRENT", build_plan2d(context.snapshot))


def _mesh3d(context: DerivationContext) -> Outcome:
    return Outcome("CURRENT", build_mesh3d(context.snapshot))


PLAN2D = Derivation("plan2d", "plan2d-vs01", "2", _plan2d)
MESH3D = Derivation("mesh3d", "mesh3d-vs01", "2", _mesh3d)

__all__ = ["MESH3D", "PLAN2D", "Mesh3dPayload", "Plan2dPayload", "build_mesh3d", "build_plan2d"]
