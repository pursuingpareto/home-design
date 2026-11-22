# D078 — VS-02b opening framing details: pieces meet at faces, the band rule for layout studs, and girts cut by band overlap

**Status:** Confirmed (implemented in VS-02b; [ASM-001](../../implementation/tasks/ASM-001.md) with [MODEL-006](../../implementation/tasks/MODEL-006.md))  
**Date:** 2026-11-22  
**Scope:** Where the opening framing pieces of [D066](D066-vs02b-wall-framing.md) end, which layout studs become cripples, and when a girt counts as crossing an opening. Settled as [ASM-001](../../implementation/tasks/ASM-001.md) §13 item 1, parts 1a–1c, one at a time, within D066 and [D076](D076-vs02b-framed-opening-geometry.md).  
**Refines:** D066 §3d, which names the pieces but not their ends, the jack case, or what "crosses" means.

## Decision

Coordinates are wall-local: `u` along the wall from its start post axis, and `v` up from its lower datum. ε is 1e-6 m. `t` is the stud section's in-plane thickness, `t_g` the girt section's, `d` the header's vertical depth, and `b` the buck's in-plane thickness (D076). An opening has rough opening `[o, o + w] × [s, s + h]`, and framed rectangle `[u0, u1] × [v0, v1]` (D076).

### 1a. Pieces meet at faces

Opening pieces meet one another at **faces**. Every piece meets the frame at a **datum or a brace axis**, as studs do (D066).

| Piece | Extent |
|---|---|
| Header | Between the kings' inner faces: `w`, or `w + 2t` with jacks, bearing on them |
| Rough sill; buck head and buck sill | The rough opening, `o` to `o + w` |
| Jacks | From the lower datum to the header's underside |
| Upper cripples | From the header's top to the upper datum, or to a brace axis |
| Lower cripples | From the lower datum to the rough sill's underside |
| Buck jambs | The framed rectangle's full height, `v0` to `v1` |
| Cut girt pieces | From a post axis to the kings' outer faces (`u0`, `u1`), the framed rectangle's sides |

No two pieces' faces then overlap, except where a girt crosses a vertical piece. D071's framing fraction counts those crossings once and needs no other deduction.

### 1b. Layout studs at an opening: the band rule

Each layout stud is taken as its band `[p − t/2, p + t/2]`. Touching within ε is not overlapping.

| The band… | Result |
|---|---|
| overlaps no framed range `[u0, u1]` by more than ε | a layout stud |
| overlaps a king by more than ε | dropped (D066) |
| otherwise, between the kings | an upper cripple; for a window, also a lower cripple, **unless the band overlaps a jack** by more than ε, where the jack carries the rough sill's end |

### 1c. Girts are cut by band overlap

- A girt is **cut** by an opening when its band `[v − t_g/2, v + t_g/2]` overlaps the framed height `[v0, v1]` by more than ε. The pieces stop at the kings' outer faces (1a).
- A girt that passes above or below a framed opening is not cut. It is let in across the kings, jacks, and cripples it crosses, as across studs (D066).

### Reference House 001 v3

- No layout stud overlaps a king or a jack.
- Every opening cuts its mid-height girt: at 5'-0" on Level 0, and 4'-6" on Level 1.
- With stud infill, the house has **246** wall framing pieces: 76 studs, 40 girts, 40 kings, 4 jacks, 20 headers, 19 rough sills, and 47 cripples. That is 12 pieces per wall with a 3'-0" window, 16 with a 5'-0" window, and 10 with the door. This is the exact count behind [D072](D072-reference-house-001-v3-design-intent.md)'s "about 250". With the straw bale default it stays 79 buck pieces.

## Rationale

- **1a:** pieces that meet at faces are how opening framing is built, and the face areas then add up without double counting. The frame's datum convention still holds wherever wall framing meets the frame.
- **1b:** a lower cripple under a jack would occupy the jack's space; the jack already supports the sill there.
- **1c:** the band test follows the physical piece. A girt whose axis clears the header could still overlap it by up to half its thickness.

## Alternatives considered

- **1a: axis to axis,** as frame members meet: headers and cut girts run to the king axes, and sills to the jack axes. Each such piece is then `t/2` longer at each end, and the faces overlap at every opening, so `ART-003` would need to deduct them.
- **1b: keep both cripples** wherever a stud falls between the kings. The lower cripple and a jack would then occupy the same space.
- **1c: cut by axis:** a girt is cut when its axis lies within the framed height.

## What this does not decide

- Stacked openings, the key formats, and the template text (ASM-001 §13, items 2–4).
- Quantities and framing fractions (`ART-003`).
- Any structural or code claim about headers, kings, jacks, or cripples (AC-08).
