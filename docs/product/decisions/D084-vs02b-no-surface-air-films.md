# D084 — VS-02b `parallel-path-1` adds no surface air films

**Status:** Confirmed; implemented in VS-02b by [ART-003](../../implementation/tasks/ART-003.md) (2026-11-22)  
**Date:** 2026-11-22  
**Scope:** Whether the D071 method `parallel-path-1` includes inside and outside surface air-film resistances. Approved as [ART-003](../../implementation/tasks/ART-003.md) §12 item 3.  
**Refines:** [D071](D071-vs02b-thermal-moisture-values.md), whose path resistances are "the sum of every layer's resistance".

## Decision

- **No surface air films:** `R_fill` and `R_framing` are the sums of the definition's layer resistances only. Nothing else enters the figures.
- **The method says so:** its notes include "Surface air films are not included." The figures are therefore conservative (U slightly higher than with films), and every number in them comes from the definition's declared values with their provenance (D075).
- **A later method version** (for example `parallel-path-2`) can add films, with sourced values recorded where their provenance can be shown, once open question 6 is settled.

## Rationale

- Film values are property data. Putting them in code would make them the first values without the provenance D071 and D075 require.
- Leaving them out errs on the conservative side, by a few percent for these build-ups, and the note keeps it visible.

## Alternatives considered

- **Fixed film values in the method,** with their source named in the note: closer to published practice, but the values would live in code rather than in the model with provenance.

## What this does not decide

Film values or where a later method would record them. Any energy-code or compliance claim (AC-08).
