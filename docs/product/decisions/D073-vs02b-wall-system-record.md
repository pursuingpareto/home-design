# D073 — VS-02b wall system: a `WallSystem` record holds the wall rule, the default assembly, and the lists of walls and openings

**Status:** Confirmed (not yet implemented; [MODEL-006](../../implementation/tasks/MODEL-006.md))  
**Date:** 2026-11-21  
**Scope:** Where the version 3 model keeps generated walls, user-placed openings, the project-wide wall assembly, and the wall rule's version. Approved as [MODEL-006](../../implementation/tasks/MODEL-006.md) §13 item 1, within [D065](D065-vs02b-wall-placement.md)–[D069](D069-vs02b-openings.md).  
**Settles:** the field location that [D068](D068-vs02b-wall-assembly-choice.md) left to MODEL-006 ("a new field holds the default definition").

## Decision

- **A new record kind, `WallSystem`** (record version 1), referenced from **`Building.wall_system_id`**. `Building` moves to record version 2. There is exactly one `WallSystem` per snapshot, as there is one `FrameSystem`.
- **Its fields:**
  - `generation_rule_version`: the registered wall rule (`vs02b-walls-1`, from `ASM-001`), as `TimberGrid.generation_rule_version` names the frame rule;
  - `default_assembly_definition_id`: the project-wide default of D068. Every generated wall takes it, as members take `member_defaults` ([D039](D039-frame-member-defaults.md));
  - `wall_ids`: every `Wall` record, ascending by `generation_key` ([D030](D030-canonical-snapshot-entity-order.md)), as `member_ids` lists members;
  - `opening_ids`: every `Opening` record, ascending by ID. Openings are user-authored and have no generation key.
- **The timber frame is untouched:** `FrameSystem`, `vs02-frame-1`, and its 193 members and 312 connections are unchanged ([D066](D066-vs02b-wall-framing.md)).

## Rationale

- D066 keeps wall framing out of the heavy-timber frame. A separate record keeps the frame's record and rule out of wall changes too.
- The wall rule gets its own version field, so a later wall rule (for example a code-dependent jack rule, open question 5) is registered beside the frame rule, not inside it.
- Wall inputs sit in one record, so `ART-003`'s selectors read one place, as DEP-001's read `FrameSystem` for the frame.

## Alternatives considered

- **The same fields on `FrameSystem`:** no new kind, but it changes the frame record that D066 left alone and mixes two rules' inputs in one record.
- **Fields on `Building`:** no new kind, but it puts generated-record lists on the root record.

## What this does not decide

The fields of `AssemblyDefinition`, `Wall`, `WallFramingPiece`, and `Opening`, and the validation codes for them (MODEL-006 §13, items 2–13). Wall key formats and the wall rule itself (`ASM-001`).
