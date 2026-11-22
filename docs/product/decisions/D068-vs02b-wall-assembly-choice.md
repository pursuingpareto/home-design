# D068 — VS-02b wall assembly choice: one project-wide default, `SetWallAssembly`, consequential

**Status:** Confirmed  
**Date:** 2026-11-21  
**Scope:** At what granularity a wall's assembly is chosen in VS-02b, by which command, and how the command is classified. Approved as proposal 5 of the [VS-02b scope proposal](../../implementation/acceptance-tests/vs-02b.md) (§10), within [D064](D064-vs02b-slice-boundary.md)–[D067](D067-vs02b-assembly-definitions.md).

## Decision

- **One project-wide wall default:** a new field holds the default `AssemblyDefinition`, and every generated wall ([D065](D065-vs02b-wall-placement.md)) takes it, as members take `member_defaults` ([D039](D039-frame-member-defaults.md)).
- **One command,** `SetWallAssembly {assembly_definition_id}` (working name), switches every wall. A definition not in the project is `DANGLING_REFERENCE`, and the current value is a no-op ([D045](D045-no-op-commits.md)).
- **Consequential:** it changes every wall, its wall framing (studs, girts, and kings and jacks at openings become bucks, or the reverse; [D066](D066-vs02b-wall-framing.md)), and the estimate at once, which dependencies.md §4 classes as consequential, as `SetConnectionType` is ([D059](D059-vs02-junction-rules-connection-type-command.md)). Its row goes into the new classification table version.

## Rationale

- It delivers the whole-house straw bale versus stud comparison (D008, D014) with one command.
- No override has to survive regeneration. [D040](D040-setmembersection-role-default.md) deferred per-member overrides for the same reason.

## Alternatives considered

- **Per elevation and story** (eight fixed defaults): allows, for example, a stud south wall with more glass and straw bale elsewhere.
- **Per wall:** a default plus overrides keyed by the wall's generation key. The most flexible, and the natural next step; it needs a rule for overrides whose wall disappears.

## What this does not decide

The field and argument names, and error details (MODEL-006). The default definition for Reference House 001 v3 (proposal 9). Nothing here claims structural, fire, energy-code, or moisture performance (AC-08).
