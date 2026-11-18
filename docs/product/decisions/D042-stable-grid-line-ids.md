# D042 — Stable grid-line identities and generation keys

**Status:** Confirmed  
**Date:** 2026-11-18  
**Scope:** The `TimberGrid` record, `vs01-post-beam-1` generation keys, the Reference House 001 fixture, and validation paths. Closes gap C4.  
**Amends:** [D025](D025-reference-house-001-vs01-fixture.md) (key format and grid representation), [D030](D030-canonical-snapshot-entity-order.md), [D032](D032-vs01-numeric-bounds.md), and [D037](D037-error-related-paths.md) (field names in their text). All values and geometry are unchanged.

## Problem

Generation keys numbered grid lines by position (`frame/x-2/…`). Inserting or removing an interior line renumbered the lines after it:

- A member could keep its ID while becoming a different physical member.
- Members on the outer lines received new IDs.
- The spec's own test ("Remove grid bay … preserve surviving member IDs", dependencies.md §8) could not pass.

## Decision

### Grid representation

`TimberGrid` replaces `x_fractions` / `y_fractions` with **`x_lines`** / **`y_lines`**: arrays of line records `{"id": <line id>, "fraction": <number>}`.

- **Order:** the arrays have a semantic order, strictly ascending by `fraction`, from 0 to 1 inclusive (D030). The fraction rules and D032 bounds are unchanged; they now apply to `x_lines[k].fraction`. The station count is the array length.
- **Line ID format:** `x<n>` in `x_lines` and `y<n>` in `y_lines`, where `<n>` is a decimal integer without leading zeros (pattern `^x(0|[1-9][0-9]{0,8})$`, or the same with `y`). Any other form, including the wrong axis letter, is the new stage-1 code **`INVALID_LINE_ID`**.
- **Unique per axis:** a repeated ID is the new stage-2 code **`DUPLICATE_LINE_ID`**. Its path is the later occurrence's `id`, and `related_paths` is the first occurrence's `id`; this is a new D037 mapping row.
- **Opaque:** a line ID is an identifier, not a display label and not an index. `x4` may sit between `x1` and `x2`. Labels such as bent numbers are a separate, later concern (D026: names are not identifiers).

### Assigning new line IDs

When a command adds a line, it receives `x<n>` (or `y<n>`), where `n` is one more than the largest number on that axis in either the previous grid or the new grid. A line removed and another added in the same command therefore never share an ID. Across separate commands a number can recur after the highest-numbered line was removed; members on it still get new IDs, because [D041](D041-deterministic-id-minting.md) mints from the command. Command arguments for referring to existing lines and adding new ones are part of gap M5.

### Generation keys (`vs01-post-beam-1`, amended)

| Member | Key |
|---|---|
| Post, story L (0 or 1) | `frame/{x}/{y}/level-{L}/post`, for example `frame/x0/y1/level-0/post` |
| X-direction beam | `frame/axis-x/{y}/{x_a}-{x_b}/{plane}/beam`, for example `frame/axis-x/y0/x0-x1/plane-L1/beam` |
| Y-direction beam | `frame/axis-y/{x}/{y_a}-{y_b}/{plane}/beam`, for example `frame/axis-y/x0/y0-y1/plane-eave/beam` |

Here `{x}`, `{y}` are line IDs, `{x_a}-{x_b}` are the IDs of the bay's two adjacent lines in ascending-fraction order, and `{plane}` is `plane-L1` or `plane-eave`.

**Behavior:**

- Members on lines that survive an edit keep their keys, and therefore their IDs.
- Inserting a line splits a bay: the old bay's beams are retired, and new beams are created for both halves.
- Removing a line merges two bays: their beams are retired, and a new beam spans the merged bay.
- Posts on a removed line are retired.

The plan2d plane rules (artifacts.md §5) are unchanged, because they match the `/level-0/post`, `/level-1/post`, `/plane-L1/`, and `/plane-eave/` segments.

### Reference House 001

`x_lines` = `x0`…`x3` at fractions `0, 1/3, 2/3, 1`, and `y_lines` = `y0`…`y2` at `0, 0.5, 1`. All 58 members keep their IDs and geometry, and only their `generation_key` values change. `member_ids` is re-sorted by the new keys. The fixture's canonical fingerprint changes, and this decision approves that change.

### Schema and rule version

As with [D033](D033-level-story-height.md) and [D039](D039-frame-member-defaults.md), no revision has been persisted. This is a **pre-release correction**: model schema version 1 and rule name `vs01-post-beam-1` are unchanged, and the fixture, exported schema, vectors, and tests change in the same commit.

## What this does not decide

- Command arguments for `SetTimberGrid` (gap M5).
- Display labels for grid lines or bents.
- A stored counter to prevent line numbers from recurring across commands. Not needed while nothing attaches to lines; revisit if annotations on lines are introduced.
