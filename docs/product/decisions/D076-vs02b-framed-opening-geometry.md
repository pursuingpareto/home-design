# D076 — VS-02b framed-opening geometry: the rectangle rule for braces, rough sills included, and stud-section opening pieces

**Status:** Confirmed (not yet implemented; [MODEL-006](../../implementation/tasks/MODEL-006.md))  
**Date:** 2026-11-21  
**Scope:** What the framed opening of [D069](D069-vs02b-openings.md) is, exactly, and how it is checked against the knee braces. Settled as [MODEL-006](../../implementation/tasks/MODEL-006.md) §13 item 4, parts 4a–4c, one at a time, within [D066](D066-vs02b-wall-framing.md) and D069.  
**Refines:** D069's fit rule, which left "exact rules and codes" to MODEL-006. D069's own statement left the rough sill out of a stud-infill window's framed opening; 4b adds it.

## Decision

Coordinates are wall-local: `u` along the wall from its start post axis, `v` up from its lower datum. ε is 1e-6 m.

### The framed opening (4b, 4c)

For an opening with rough opening `[o, o + w] × [s, s + h]`, the framed opening is the rectangle `[u0, u1] × [v0, v1]`:

| Wall | `u0`, `u1` | `v1` | `v0` |
|---|---|---|---|
| Stud infill, rough-opening width at most the jack threshold (+ε) | `o − t`, `o + w + t` (kings) | `s + h + d` (header) | `s − t` for a window (rough sill), `s` for a door |
| Stud infill, width above the threshold | `o − 2t`, `o + w + 2t` (jacks and kings) | `s + h + d` | as above |
| Straw bale | `o − b`, `o + w + b` (buck jambs) | `s + h + b` (buck head) | `s − b` for a window (buck sill), `s` for a door |

- **4b: the rough sill is part of a stud-infill window's framed opening,** as the buck sill already is in straw bale walls. A window's sill height must leave room for it (`s ≥ t`, through the inside-the-wall check), so no rough sill is generated below the lower datum.
- **4c: sections and in-plane dimensions.** Kings, jacks, cripples, and rough sills take the definition's **stud section**; bucks take the **buck section**. A piece's in-plane dimension is its section's `actual_width_m` (`t` for stud-section pieces and girts, `b` for bucks), except a **header's**, which is its `actual_depth_m` (`d`, vertical), as D066's "the header's depth sets the cripples' lower end" requires.

### Clearance to braces (4a): the rectangle rule

- With the wall's brace plane on, each wall has a brace at each top corner, from `(0, H − L)` to `(L, H)` and from `(W, H − L)` to `(W − L, H)`.
- The framed rectangle **must not meet either brace axis, nor lie in the triangle above it** (between brace, post, and beam). Touching within ε is accepted.
- Kings are continuous studs, so above the header a king may stop on a brace, like any stud (D066). Windows may sit under a brace when they are low enough.

### Reference House 001 v3

- A 3'-0" window centered in a 12' bay spans `u` from 4'-4½" to 7'-7½" in either family; `v` from 2'-10½" to 7'-7¼" (stud infill) or 7'-1½" (straw bale). A 5'-0" stud-infill window, with jacks, spans 3'-3" to 8'-9".
- With the windows at their offsets, a bay can shrink to 8'-9" with the straw bale default (9'-4¼" with stud infill). The golden scenario's grid step to four 10' bays stays valid.

## Rationale

- **4a:** the rectangle rule is the literal reading of "clear of the knee-brace axes" for the rectangle that the header and kings enclose, and it keeps ordinary frame edits valid on the reference house. Kings stopping on a brace above the header are framed like any other stud.
- **4b:** treating the two families alike means every accepted window has room for the piece under it, so nothing is generated below the floor datum.
- **4c:** D066 and D067 name only the stud, girt, header, and buck sections; using the stud section for the other opening pieces invents no new values, and the header's vertical depth is what D066 already assumes.

## Alternatives considered

- **4a: no part of a framed opening within a brace leg of either post,** so every king is full height. Simpler to explain, but the reference house's windows would need bays of at least 10'-7½" (3'-0") and 11'-7½" (5'-0"), and the golden scenario's grid step would be rejected.
- **4b: D069 as written,** with windows whose sill is under the stud thickness generating a rough sill below the floor datum.
- **4c: separate sections for kings, jacks, and rough sills** in the framing layer, which D067 does not list.

## What this does not decide

Detail codes and paths (MODEL-006 §5.2, routine). Piece positions, keys, and cripple rules (`ASM-001`). Clearance to member faces, which stays unchecked (D069). Any structural or code claim about headers, kings, or jacks (AC-08).
