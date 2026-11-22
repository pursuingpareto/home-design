# D080 — VS-02b generation keys for walls and wall framing

**Status:** Confirmed (not yet implemented; [ASM-001](../../implementation/tasks/ASM-001.md))  
**Date:** 2026-11-22  
**Scope:** The `generation_key` formats of `Wall` and `WallFramingPiece` records under rule `vs02b-walls-1`. Approved as [ASM-001](../../implementation/tasks/ASM-001.md) §13 item 3. Routine item 11 of the [VS-02b scope](../../implementation/acceptance-tests/vs-02b.md) (§6) left the formats to the task file. This decision sets them within [D041](D041-deterministic-id-minting.md), [D042](D042-stable-grid-line-ids.md), [D065](D065-vs02b-wall-placement.md), [D066](D066-vs02b-wall-framing.md), and [D069](D069-vs02b-openings.md).

## Decision

| Record | `generation_key` |
|---|---|
| Wall along X | `wall/axis-x/{y}/{xa}-{xb}/level-{i}` |
| Wall along Y | `wall/axis-y/{x}/{ya}-{yb}/level-{i}` |
| Layout stud | `{wall key}/stud/s{k}` |
| Girt piece from the start post | `{wall key}/girt/g{i}/start` |
| Girt piece after an opening | `{wall key}/girt/g{i}/after/{opening id}` |
| Opening framing | `{wall key}/opening/{opening id}/{piece}` |

`{piece}` is one of:

- `king/start`, `king/end`;
- `jack/start`, `jack/end`;
- `header`, `rough-sill`;
- `cripple/s{k}/above`, `cripple/s{k}/below`;
- `buck-jamb/start`, `buck-jamb/end`, `buck-head`, `buck-sill`.

The tokens:

- **Grid lines:** `{x}`, `{y}`, `{xa}-{xb}`, and `{ya}-{yb}` are grid-line IDs, as in beam keys (D042).
- **Level:** `{i}` is the level index, as in post keys (`level-0`, `level-1`).
- **Ordinals:** `k` counts layout positions from the start post, as joist ordinals do. `i` counts girts from the bottom. Both start at 1 and are not zero-padded.
- **Opening:** `{opening id}` is the opening's UUID.
- **Sides:** `start` and `end` name the side toward the wall's start or end.

Properties:

- **No collision:** member keys start with `frame/`, connection keys with `connection/`, and wall and framing keys with `wall/`. A framing key is its wall's key followed by `/`, so it never equals a wall key.
- **Girt pieces are named by what they start from.** Adding, moving, or removing an opening renames no other girt piece. Adding an opening keeps the piece before it, shortened, and adds `after/{id}`.
- **Opening framing follows its opening.** An opening keeps its ID and its wall (D069), so its framing keys survive every edit that keeps the wall.
- **Projects from the template:** opening IDs are minted per project (D041), so a created project's opening framing keys differ from the fixture's in the `{opening id}` token.
- **Order:** code-unit order (D030), so each wall's framing sorts under it.

## Rationale

- The keys reuse the frame's tokens, so a wall's key reads like its beam's.
- Naming girt pieces by what they start from keeps surviving pieces' IDs stable when openings come and go.
- Keying framing under the wall keeps each wall's pieces together in every sorted list and payload.

## Alternatives considered

- **Girt pieces by ordinal** (`g1/1`, `g1/2`): adding an opening before a piece renumbers every later piece, so surviving girts trade IDs.
- **Opening framing at the top level** (`opening/{id}/…`): shorter keys, but framing no longer sorts under its wall.

## What this does not decide

- Payload field names and ordering (`ART-003`).
- Keys for later wall rules: a new rule version may define its own.
