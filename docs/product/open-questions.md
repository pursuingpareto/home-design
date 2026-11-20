# Open decisions and research

1. ~~Exact reference-house footprint, story heights, bay grid, roof pitch, and sample timber sizes.~~ **Resolved for VS-01:** [D025](decisions/D025-reference-house-001-vs01-fixture.md). Later houses and engineering loads remain open.
2. ~~Canonical coordinate system, numerical precision, unit policy, and tolerances.~~ **Resolved:** [D026](decisions/D026-canonical-units-identity-persistence.md). Adapter kernel internals and fabrication tolerance remain distinct from the 1e-6 m comparison epsilon.
3. Exact geometry kernel and browser/editor libraries after proof-of-concept evaluation.
4. Initial supported timber connection types and engineering analysis boundaries. *(Connection types for VS-02 resolved by [D054](decisions/D054-vs02-connection-catalog.md); engineering analysis boundaries remain open, for VS-04.)*
5. Authoritative Vermont code editions, jurisdictional applicability, and load inputs.
6. Source and licensing of materials, price, environmental-product, and climate datasets.
7. ~~Project data storage strategy (normalized entities vs versioned document snapshots) and migrations.~~ **Resolved for VS-01:** immutable JSONB snapshots plus append-only operations ([D026](decisions/D026-canonical-units-identity-persistence.md)). Migration mechanics and later dual representations remain implementation work, not an open product fork.
8. Hosting, identity provider, backups, security/privacy requirements, and deployment workflow. *(VS-01 uses a pluggable development authenticator and owner-only projects, [D050](decisions/D050-vs01-authentication-authorization.md); the production identity provider remains open.)*
9. Drawing/export formats, interoperability priorities, and expected accuracy for each milestone. Internal VS-01 plan/mesh/schedule/estimate JSON is specified ([D027](decisions/D027-vs01-artifact-dtos.md)); this item remains about DXF/IFC and similar interchange.
10. Detailed first-slice task breakdown. Interface and artifact contracts for VS-01 exist; executable `MODEL-001`… task files are still missing.

## Remaining research (not product forks for VS-01)

- Validate kernel-internal numeric behavior experimentally before relying on fabrication dimensions. Do not treat 1e-6 m comparison as mill tolerance.
- Exact geometry kernel and editor libraries remain open (item 3). D022 stack choices stay suitability-first.
