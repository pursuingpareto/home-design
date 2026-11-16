# Geometry and rendering

**Status:** Provisional.

The semantic parametric building model is authoritative. Exact CAD representations, browser rendering meshes, structural analysis models, and fabrication geometry are derived views. Three.js is a provisional rendering choice, not the precision geometry kernel. Evaluate OpenCascade and alternatives with a proof of concept.

## VS-01 geometry contract

Given a valid revision of the rectangular two-story reference model, deterministically derive 2D plan geometry and 3D display primitives. Record the source revision for all derived artifacts. Payload shapes are [artifacts.md](artifacts.md) (`plan2d`, `mesh3d`) (D027).

Canonical units, axes, and the 1e-6 m comparison epsilon are confirmed ([D026](../product/decisions/D026-canonical-units-identity-persistence.md)). Display conversion is at the UI boundary.

## Open

Exact-kernel selection and render-library proof of concept remain unresolved. See [open questions](../product/open-questions.md).
