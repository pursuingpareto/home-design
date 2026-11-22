# D079 — VS-02b openings in one wall must not overlap along the wall

**Status:** Confirmed (implemented in VS-02b; [MODEL-006](../../implementation/tasks/MODEL-006.md) with [ASM-001](../../implementation/tasks/ASM-001.md))  
**Date:** 2026-11-22  
**Scope:** When two openings in one wall are rejected as overlapping. Approved as [ASM-001](../../implementation/tasks/ASM-001.md) §13 item 2, within [D066](D066-vs02b-wall-framing.md), [D069](D069-vs02b-openings.md), and [D076](D076-vs02b-framed-opening-geometry.md).  
**Refines:** D069's "framed openings in one wall do not overlap", and D076's framed rectangle. **Amends:** MODEL-006 §5.2, the `OPENINGS_OVERLAP` check, which was approved as overlap in both `u` and `v`.

## Problem

MODEL-006 rejected two framed openings only if they overlapped both along the wall (`u`) and up it (`v`). So stacked openings, such as a window directly above a door, were accepted. D066 makes kings continuous, from the lower datum to the upper one (or a brace), so the lower opening's kings would pass through the upper opening. The rule could not frame it buildably.

## Decision

- **Framed openings in one wall must not overlap along the wall:** two openings are rejected when their framed ranges `[u0, u1]` overlap by more than ε (1e-6 m), whatever their heights. Touching within ε is accepted.
- **Both families:** the rule applies to straw bale walls too, though their bucks would not conflict. The rule is then family-independent, and `SetWallAssembly` meets no rejection that depends on the family.
- **Code and paths unchanged:** `OPENINGS_OVERLAP` (stage 4), at the later opening's `offset_m` by ID order, with the earlier opening's `offset_m` in `related_paths`. Only the test is narrowed to `u`.
- **Consequence for the rule:** each layout stud and each girt piece lies within at most one opening's framed range, so D078's band rules never meet two openings at once.
- **Reference House 001 v3** has one opening per wall, so nothing changes there.

## Rationale

- Every accepted opening stays buildable as generated (D069's rationale), with D066's continuous kings unchanged.
- One rule for both families keeps the fit independent of the assembly, and is simpler to explain.

## Alternatives considered

- **The `u`-only rule for stud infill walls only:** stacked openings stay possible in straw bale walls, but switching such a wall to stud infill is then rejected.
- **Kings that stop at another opening's framing:** keeps stacked openings, but D066 does not describe such framing, and it would need rules of its own.

## What this does not decide

- Transoms, sidelights, and openings combined into one rough opening, which come with opening products (D069).
- Any egress, fire, or structural claim (AC-08).
