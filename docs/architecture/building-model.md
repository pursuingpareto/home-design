# Semantic building model

**Status:** Foundational direction confirmed; detailed schemas provisional.

All persisted dimensions use a canonical unit system (recommended: SI internally), with explicit unit conversion at UI/import/export boundaries. Coordinate conventions and geometric tolerances must be specified before geometry implementation.

Minimum conceptual entity fields: `id`, `kind`, `schema_version`, `parameters`, `relationships`, `metadata`. Materials and structural members have specialized typed schemas. Every operation includes an operation ID, actor, base revision, target IDs, typed arguments, and validation outcome.

Example operation types: `CreateLevel`, `SetBuildingFootprint`, `SetRoofParameters`, `CreateTimberMember`, `MoveStructuralGridLine`, `SetMemberSection`, `AssignAssembly`, `DeleteComponent`. Operations must either commit atomically or return a structured error. Dependency invalidation produces an explicit list of affected artifacts.

For AI: `natural-language request -> structured proposal -> model validation -> impact preview -> user confirmation -> transactional commit -> derived updates`. AI does not write directly to database tables or bypass permissions.

## Related requirements

See FR-02, FR-04, and FR-05 in [functional requirements](../product/requirements.md).

## Next design work

Specify concrete entity schemas, canonical units, coordinate conventions, referential integrity, and model migrations before implementation.
