# D071 — VS-02b thermal and moisture values: declared with provenance, and a framing-corrected figure

**Status:** Confirmed  
**Date:** 2026-11-21  
**Scope:** What property data VS-02b assembly layers record, and what is computed from it. Approved as proposal 8 of the [VS-02b scope proposal](../../implementation/acceptance-tests/vs-02b.md) (§13), as revised to the product owner's direction.  
**Refined by:** [D084](D084-vs02b-no-surface-air-films.md): `parallel-path-1` adds no surface air films.  
**Extends:** [D067](D067-vs02b-assembly-definitions.md) (the framing layer gets two materials).

## Product owner direction

Provide a **figure corrected for framing**. [D066](D066-vs02b-wall-framing.md) generates every stud, girt, and opening piece, so the framing fraction is known from the model, and the figure can set the product apart. The first recommendation, a layer sum only, was not adopted.

## Decision

- **Recorded per layer:** a declared thermal conductivity or thermal resistance, and a vapor permeance, each nullable and each with provenance (source, date, and a note). Unknown is `null`, never 0.
- **The framing layer has two materials:** its framing material (studs, girts, and opening pieces) and its fill (for example dense-pack cellulose between studs), each with its own nullable conductivity. In straw bale walls, the bale layer is the fill and the buck is the framing material.
- **Recorded per definition:** the climate-specific details to flag as unverified. They appear with every figure, under the unverified-climate warning.
- **Computed, per wall:**
  - **framing fraction** `f`: the face area of the wall's framing pieces in its plane (section width in the wall plane times reference-axis length, with stud and girt crossings counted once), divided by the wall's net area;
  - **two path resistances:** through the fill (every layer, with the framing layer at its fill value) and through the framing (the same, with the framing layer at its framing material's value);
  - **framing-corrected value:** the parallel-path combination `U = f / R_framing + (1 − f) / R_fill`, reported as a U-value and its effective R-value;
  - **center-of-cavity value:** `R_fill`, reported beside it.
- **Computed, per definition and for all walls:** area-weighted figures over net wall area (sum of `U × area`, and the average U), **opaque walls only**. No whole-envelope or heat-loss figure.
- **Gating:** a figure is computed only when every value it uses is known; otherwise it is `null`, with the missing layers or materials named.
- **Method named and versioned** in the output (`parallel-path-1`), so a later method can replace it, as the jack threshold can be replaced (D066).
- **Labels:** parallel-path method, framing fraction from the generated framing; heavy-timber frame members in the wall plane, air leakage, and moisture effects are not included; declared values, not verified; not a code-compliance calculation. No output claims energy-code compliance (AC-08).
- **Moisture:** recorded only. No hygrothermal analysis and no condensation claim.
- **Values:** `null` unless the product owner supplies them with a source (open question 6 stays open).

## Rationale

- The model already knows every framing piece, so the framing penalty can be computed from the design itself rather than from a generic framing factor.
- Showing the center-of-cavity value beside the corrected one makes the penalty visible to homeowners and builders.
- Gating and labels keep the figure honest: unknown inputs give no number, and nothing reads as compliance (principle 7, FR-08).

## Alternatives considered

- **A layer sum only** (the first recommendation).
- **Record values and compute nothing.**
- **Including the heavy-timber frame as a bridge:** posts, sills, beams, and braces do not span the full wall thickness, so each needs its own mixed path, and the result depends on member sections. Left for a later method version.
- **Isothermal-planes or two-dimensional methods:** more data and per-layer method choices.

## What this does not decide

The values themselves (proposal 9). Field names, payload shapes, and numeric rules (ART-003). Any energy-code or moisture-performance claim.
