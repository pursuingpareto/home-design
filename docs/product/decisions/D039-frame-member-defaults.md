# D039 — Per-role section and material defaults on `FrameSystem`

**Status:** Confirmed  
**Date:** 2026-11-18  
**Scope:** How generated timber members get their `Section` and `Material`. Changes the `FrameSystem` record (schema version 1, pre-release), the Reference House 001 fixture, and the `vs01-post-beam-1` generation rule. Closes gap M1.

## Problem

`vs01-post-beam-1` assigned "the post section" and "the beam section", but no field said which records those were. Generation was therefore undefined whenever the generator had to create a member it could not copy from an existing one: for a new grid bay, for a frame generated from nothing, or after a section change.

## Decision

`FrameSystem` gains a required field **`member_defaults`**, a map from member role to the section and material used for every generated member with that role:

```json
"member_defaults": {
  "BEAM": {"section_id": "<Section>", "material_id": "<Material>"},
  "POST": {"section_id": "<Section>", "material_id": "<Material>"}
}
```

- **Keys** are `TimberMember.member_role` values (`POST`, `BEAM`, `FLOOR_JOIST`, `RAFTER`). Any other key is `INVALID_ENUM` (stage 1).
- **Values** are objects with exactly the required keys `section_id` and `material_id`. Stage 2 checks that they reference existing records of kind `Section` and `Material` (`DANGLING_REFERENCE`, `WRONG_REFERENCE_KIND`).
- **Required roles:** under a supported generation rule, the map must have an entry for **every role the rule generates**. For `vs01-post-beam-1` those are `POST` and `BEAM`. A missing entry is the new detail code **`MISSING_ROLE_DEFAULT`** (stage 2, `VALIDATION_FAILED`). Its path is the map, and `value` is the missing role. Entries for roles the rule does not generate are allowed and ignored.
- **The generator** assigns each generated member its role's `section_id` and `material_id`. Changing a default changes the section or material of every generated member with that role on the next regeneration. Member IDs are preserved, because geometry and section may change without changing an ID (building-model.md §5).
- **Conformance:** checking that every member's `section_id` and `material_id` equal its role's defaults is part of the generation-rule conformance check in `TIMBER-001`.
- **A map, not fields:** roles added in later rule versions (joists, rafters) add entries, not schema fields. A material per role permits combinations such as engineered beams on solid-sawn posts without another schema change.

## Reference House 001

`POST` → the 8×8 section and eastern white pine; `BEAM` → the 8×12 section and eastern white pine. These are the assignments the fixture's members already have. No member changes. The fixture's canonical fingerprint changes because `FrameSystem` changes, and this decision approves that change.

## Schema version

No revision has been persisted yet (persistence arrives with `MODEL-004`). As with [D033](D033-level-story-height.md), this is a **pre-release correction of schema version 1**: version numbers stay `1`, no migration is written, and the fixture, exported JSON Schema, test vectors, and tests change in the same commit.

## Alternatives rejected

- **Inferring sections from existing members:** undefined when a role has no members, ambiguous when sections are mixed, and it makes the result depend on edit history rather than on the snapshot's parameters.
- **Hard-coding sizes in the rule:** finding records by `nominal_label` uses names as identifiers, which D026 rules out, and fixes the sizes for every project.

## What this does not decide

- What `SetMemberSection` means: changing a role default, or overriding one member, and how overrides would survive regeneration. This is the next question.
- Per-member overrides, and how they would be recorded.
- A general policy for changing schema version 1 before the first persisted revision.
