# D085 — VS-02b browser interim: wall estimate lines and square-meter price rows ship with ART-003

**Status:** Confirmed (to be implemented in VS-02b, [ART-003](../../implementation/tasks/ART-003.md))  
**Date:** 2026-11-22  
**Scope:** Which browser changes ship with ART-003's payloads, before `UI-004`. Approved as [ART-003](../../implementation/tasks/ART-003.md) §12 item 4, following [D060](D060-vs02-artifact-payloads.md)'s precedent for VS-02.  
**Amends:** the task breakdown in [vs-02b.md](../../implementation/acceptance-tests/vs-02b.md) §16. AC2b-10's bullet "The price-book form handles square-meter rows" moves from `UI-004` to `ART-003`. The criterion's wording is unchanged.

## Decision

ART-003 makes the smallest browser changes that keep the existing views correct with its payloads:

- **The fifth artifact type:** the workspace knows `assembly_schedule` (its label, and its status wherever statuses are listed). There is no assembly schedule view.
- **The estimate table:** `assembly.` lines show their material, definition, and layer, with an area and a price per square foot or square meter; `wallframing.` lines show their kind and section, with the count beside the length, priced per foot or meter as timber lines are.
- **The price-book form:** `m2` rows take a price per square foot (imperial) or square meter (metric), converted as per-foot prices are, and are submitted as `m2`. `wallframing.` rows behave like timber rows.

Drawing walls, openings, and framing, the "Wall layers" and "Wall framing" switches, the assembly schedule view, thermal figures, the assembly selector, and the opening editor stay in `UI-004`.

## Rationale

- Without these changes the form would convert `m2` rows as if they were per foot and misprice them, and the table would show areas as lengths.
- With them, every price the API accepts can also be set and read in the browser, as D060 ensured for "each" rows.

## Alternatives considered

- **Only stop the breakage:** labels and the type, with `m2` rows read-only in the form until `UI-004`. Less work, but the API could set wall prices that the browser cannot edit.

## What this does not decide

The browser's wall views and controls (`UI-004`). Any price value (open question 6).
