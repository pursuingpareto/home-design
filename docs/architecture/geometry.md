# Geometry and rendering

**Status:** Provisional.

The semantic parametric building model is authoritative. Exact CAD representations, browser rendering meshes, structural analysis models, and fabrication geometry are derived views. Three.js is a provisional rendering choice, not the precision geometry kernel. Evaluate OpenCascade and alternatives with a proof of concept.

## VS-01 geometry contract

Given a valid revision of the rectangular two-story reference model, deterministically derive 2D plan geometry and 3D display primitives. Record the source revision for all derived artifacts. Payload shapes are [artifacts.md](artifacts.md) (`plan2d`, `mesh3d`) (D027).

**Numeric evaluation** ([GEOM-001](../implementation/tasks/GEOM-001.md) §4, approved as §7 item 2):

- **Exact formulas:** derived coordinates are IEEE-754 doubles evaluated exactly as written, left to right, with no fused multiply-add and no rounding or snapping, as in [generation-rules.md, "Numeric evaluation"](../reference-projects/vermont-timber-house/generation-rules.md#numeric-evaluation).
- **The one exception is `tan(pitch_rad)`.** Library implementations of `tan` are not required to be correctly rounded, so values that depend on it (ridge height, overhang edge) must agree across implementations within **1e-12 m**. All other derived values must be bit-identical. The tolerance is a million times smaller than the D026 comparison epsilon and does not affect validation or display. *VS-02 ([TIMBER-002](../implementation/tasks/TIMBER-002.md) §8, approved as §11 item 5):* the same exception covers the `z` coordinates of generated principal rafters and purlins, which the cross-language inventory vector compares within 1e-12 m; every other generated coordinate is compared bit for bit.
- **Roof geometry** follows [D048](../product/decisions/D048-roof-plane-through-wall-line.md).
- **Box orientation:** one rule covers every member role, in [artifacts.md §6](artifacts.md#6-mesh3d-payload) ([ART-002](../implementation/tasks/ART-002.md) §5.1): posts take width along +X; any other axis takes width horizontal and perpendicular to its plan projection, and depth along `axis × width` with a non-negative Z. It gives joists and purlins a vertical depth and rafters a depth perpendicular to the roof plane ([D060](../product/decisions/D060-vs02-artifact-payloads.md)).

**Member source** ([GEOM-001](../implementation/tasks/GEOM-001.md) §3, approved as §7 item 3): `plan2d` and `mesh3d` take each member's axis from the **stored** snapshot (`start_m`, `end_m`) and its section dimensions from the referenced `Section`. They never regenerate members from the rule, so the views always show exactly what was committed. Stage 5 conformance (D046) already guarantees agreement with the rule within 1e-6 m. Consequence: the hand-entered fixture shows its decimals (`3.6576`), while command-produced revisions show generator output (`3.6575999999999995`). Both display identically after unit conversion.

Canonical units, axes, and the 1e-6 m comparison epsilon are confirmed ([D026](../product/decisions/D026-canonical-units-identity-persistence.md)). Display conversion is at the UI boundary.

## Open

Exact-kernel selection and render-library proof of concept remain unresolved. See [open questions](../product/open-questions.md).
