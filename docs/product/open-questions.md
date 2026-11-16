# Open decisions and research

1. ~~Exact reference-house footprint, story heights, bay grid, roof pitch, and sample timber sizes.~~ **Resolved for VS-01:** [D025](decisions/D025-reference-house-001-vs01-fixture.md). Later houses and engineering loads remain open.
2. Canonical coordinate system, numerical precision, unit policy, and tolerances.
3. Exact geometry kernel and browser/editor libraries after proof-of-concept evaluation.
4. Initial supported timber connection types and engineering analysis boundaries.
5. Authoritative Vermont code editions, jurisdictional applicability, and load inputs.
6. Source and licensing of materials, price, environmental-product, and climate datasets.
7. Project data storage strategy (normalized entities vs versioned document snapshots) and migrations.
8. Hosting, identity provider, backups, security/privacy requirements, and deployment workflow.
9. Drawing/export formats, interoperability priorities, and expected accuracy for each milestone.
10. Detailed first-slice task breakdown and interface definitions.

## Proposed defaults requiring confirmation

- Architecture v0.2 proposes meters, +Z up, radians, UUIDs, JSONB revision snapshots, and optimistic concurrency. These are **not** confirmed product-owner decisions.
- VS-01 reference fixture geometry is confirmed (D025); still confirm product-wide units/coordinate policy before treating meters/+Z-up as more than a provisional implementation default.
- Validate the geometric tolerance and exact-kernel choice experimentally before relying on fabrication dimensions.
