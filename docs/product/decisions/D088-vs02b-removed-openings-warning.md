# D088 — VS-02b browser: openings removed with their walls are listed above Confirm

**Status:** Confirmed; not yet implemented ([UI-004](../../implementation/tasks/UI-004.md))  
**Date:** 2026-11-22  
**Scope:** How the confirmation dialog shows the openings that a consequential edit removes with their walls. Approved as [UI-004](../../implementation/tasks/UI-004.md) §15 item 2.  
**Applies:** [D069](D069-vs02b-openings.md)'s "a grid edit that removes the wall removes its openings and their framing, and the preview lists them", and AC2b-04's "Openings removed with their wall are listed in the preview".

## Problem

Wall keys name their grid lines ([D080](D080-vs02b-wall-key-formats.md)). So a grid edit that re-identifies a line, even one that changes no geometry, replaces the walls on that line and removes their openings ([MODEL-006](../../implementation/tasks/MODEL-006.md) §8.5; [ART-003](../../implementation/tasks/ART-003.md) §8.3, §17). On Reference House 001 v3, removing grid line `y1` and adding one at the same position removes the 8 east and west windows. The preview lists them only as `changes` entries with `after: null`, and in the field-change table those read as "Opening · (record) · … · —".

## Decision

- **A warning block above Confirm** in the dialog: "These N openings will be removed with their walls. Undo restores them." It is followed by each opening's label and rough-opening size, read from the head snapshot (for example "Window 3' 0" × 4' 0", east wall, Level 0, y0–y1").
- **Confirm works as it does now.** No acknowledgment or extra step: the edit is already consequential and needs confirmation.
- The block appears for every previewed command whose `changes` remove an `Opening`.

## Rationale

- The user sees, by name and before confirming, what an edit that looks harmless will delete.
- It uses what the preview already serves; the rule itself and the commands are unchanged.
- One confirmation, as for every other consequential edit, and Undo restores the openings with their IDs ([D044](D044-undo-to-revision.md)).

## Alternatives considered

- **An acknowledgment checkbox** that enables Confirm: harder to miss, but a second confirmation inside a confirmation.
- **The field-change rows only,** as served: easy to miss, and they don't explain why the openings go.

## What this does not decide

Whether re-identifying a grid line should keep openings (the D069 and D080 rules are unchanged). Any payload, command, or validation change.
