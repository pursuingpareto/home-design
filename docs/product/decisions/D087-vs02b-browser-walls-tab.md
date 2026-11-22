# D087 — VS-02b browser: a Walls tab, and openings chosen from the views

**Status:** Confirmed; not yet implemented ([UI-004](../../implementation/tasks/UI-004.md))  
**Date:** 2026-11-22  
**Scope:** Where the browser's wall controls live, and how an opening is chosen for editing. Approved as [UI-004](../../implementation/tasks/UI-004.md) §15 item 1, following [D062](D062-vs02-browser-connections.md)'s precedent of a new tab for new commands.

## Decision

- **A new Walls tab**, the eighth: Footprint · Stories · Roof · Grid · Frame · Sections · Connections · Walls. It holds all four wall commands:
  - the **wall assembly** at the top: `SetWallAssembly`, through preview and confirmation ([D068](D068-vs02b-wall-assembly-choice.md));
  - the **openings** below it: a list grouped by wall, and a form for the current opening or a new one. `AddOpening`, `SetOpening`, and `RemoveOpening` are applied directly, with Undo, as routine edits are ([D069](D069-vs02b-openings.md)).
- **The tab follows the selection.** Picking an opening in the plan, the 3D view, or the assembly schedule makes it the tab's current opening. Picking a wall makes it the wall for a new opening.
- **The active tab does not change by itself.** Picking something in a view never switches the side panel, just as picking a member does not open the Sections tab ([UI-003](../../implementation/tasks/UI-003.md) §6).

## Rationale

- The four wall commands sit together, next to the build-up they change, and the other tabs stay about the frame.
- The assembly's effect on openings (their framing and their fit) is visible in the same tab.
- Picks behave the same everywhere. The cost is one click to open the tab after picking an opening.

## Alternatives considered

- **Two tabs, "Assembly" and "Openings":** each shorter, but nine tabs in all, with the assembly's effect on openings a tab away.
- **A contextual editor beside the views** that appears on selection: the most direct, but it falls outside the tab conventions (UI-002 §4), and adding an opening still needs a place to start.
- **The Walls tab opens itself** when an opening is picked: one click fewer, but a pick would then change the side panel, which no other pick does.

## What this does not decide

The form's fields, hints, and error placement (UI-004 §8, routine). How removed openings appear in the dialog (UI-004 item 2). Any command, payload, or validation change.
