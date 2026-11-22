# D069 — VS-02b openings: user-placed rough openings, framed-opening fit, routine commands

**Status:** Confirmed  
**Date:** 2026-11-21  
**Scope:** What a VS-02b opening is, how it is placed and edited, what "fits" means, what happens to it when its wall or assembly changes, and how its commands are classified. Approved as proposal 6 of the [VS-02b scope proposal](../../implementation/acceptance-tests/vs-02b.md) (§11), as revised for [D066](D066-vs02b-wall-framing.md).

## Decision

- **Record:** an `Opening` has a kind (`WINDOW` or `DOOR`), its wall's ID, a **rough-opening** width and height, a sill height above the wall's lower datum (0 for a door), and an offset of its rough opening along the wall from the wall's start. It is a rectangle in the wall's reference plane. Doors and windows are voids, not products: no unit size, frame, glazing, or hardware data.
- **User-placed:** the first user-authored records. They have no generation key. IDs are minted from the command ([D041](D041-deterministic-id-minting.md)), and `UndoToRevision` restores them ([D044](D044-undo-to-revision.md)). Their framing is generated from them (D066), keyed by the opening's ID.
- **Commands:** `AddOpening`, `SetOpening` (replaces one opening's dimensions and position), and `RemoveOpening` (working names).
- **Fit,** checked on the full candidate snapshot, as the brace fit is. The **framed opening** is the rough opening plus its D066 framing: in stud infill walls, the kings (and jacks above the threshold) on each side and the header above; in straw bale walls, the buck. Then:
  - the framed opening lies inside the wall's reference rectangle (axis to axis, datum to datum);
  - it stays clear of the knee-brace axes in that wall;
  - framed openings in one wall do not overlap.

  Post, sill, and beam sections are not deducted, because the frame's axes stay on datums ([D058](D058-datum-reference-axes.md)). An assumption line says the fit does not check clearance to member faces.
- **When the wall or its assembly changes:**
  - a frame edit that keeps the wall's key keeps the opening, at the same offset and size, and regenerates its framing;
  - a change after which an opening no longer fits is **rejected**, naming the opening and the edited field (AC-06). That includes a frame edit and a `SetWallAssembly` ([D068](D068-vs02b-wall-assembly-choice.md)) whose framing would not fit. Nothing moves or shrinks an opening silently (principle 3);
  - a grid edit that removes the wall removes its openings and their framing, and the preview lists them. Such edits are already consequential.
- **Routine:** the three opening commands regenerate only their own wall's framing. They change no timber member, no connection, and no other wall, so they are applied with undo, like VS-01's routine edits. The commit still validates fully, and a preview is available.

## Rationale

- Rough-opening dimensions are what framing is built to, so the model holds the value a builder frames.
- Checking the framed opening, not the bare rectangle, keeps every accepted opening buildable as generated (D066).
- Rejecting rather than adjusting keeps user-authored data exactly as entered (principle 3).
- Placing a window is the most frequent homeowner edit; its effect is local to one wall, so the apply-with-undo flow fits.

## Alternatives considered

- **Opening commands as consequential:** every window edit through the confirmation dialog.
- **Rejecting any grid edit that would remove a wall with openings.**
- **Generated openings** from a parameter.

## What this does not decide

Argument names, detail codes, and exact fit tolerances (MODEL-006). How openings appear in the outputs (proposal 7). The reference house's openings (proposal 9). Nothing here claims egress, fire, energy-code, or structural adequacy (AC-08).
