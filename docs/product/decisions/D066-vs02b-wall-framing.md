# D066 — VS-02b wall framing: generated studs, girts, and opening framing, owned by each wall

**Status:** Confirmed  
**Date:** 2026-11-21  
**Scope:** Whether and how VS-02b generates infill framing (studs, girts, and framing at openings), how it is shown, and whether it gets joint records. Settled as proposal 3 of the [VS-02b scope proposal](../../implementation/acceptance-tests/vs-02b.md) (§8, sub-questions 3a–3e), within [D064](D064-vs02b-slice-boundary.md) and [D065](D065-vs02b-wall-placement.md).  
**Resolves:** D052's deferral of "girts and studs (with walls, in VS-02b)".  
**Refined by:** [D078](D078-vs02b-opening-framing-details.md): where opening pieces end, layout studs at an opening, and when a girt is cut.  
**Amends:** [D058](D058-datum-reference-axes.md), for wall framing only (below). D058 is unchanged for the timber frame.

## Product owner direction

The first recommendation, stud framing as an area-quantified layer with no individual pieces, was **not adopted**. The direction:

- the walls stay a separate layer that can be toggled on and off;
- the user and the builder see every stud and girt, and the builder gets their counts;
- framing must be **realistically buildable**, with king and jack studs where required;
- eventually, "where required" depends on the **local building code**.

## Decision

### Where wall framing lives (3a)

- Studs, girts, and opening framing are a **separate wall-framing record kind owned by each wall**, not `TimberMember` records. They are generated with their wall and its openings.
- They are listed in the **assembly schedule** with counts and lengths, not in the timber schedule. The builder has two framing lists: heavy timber in the timber schedule, and wall framing in the assembly schedule.
- Each piece's section and spacing come from its wall's assembly definition (its framing layer), not from `member_defaults`. `SetMemberSection` does not apply to them.
- **The timber frame is unchanged:** 193 members, 312 connections, `vs02-frame-1`, and its oracle.

### Display (3a′)

Both views have two switches for walls: **"Wall layers"** (the build-ups: plaster, bales, sheathing, insulation) and **"Wall framing"** (studs, girts, and opening framing). Turning wall layers off shows the framing; turning both off shows the bare timber frame. Both are on by default, remembered per browser, and display only: schedules are unaffected (as D062's Connections switch).

### Girts (3b)

- Girts are **declared by the assembly definition**: a count per wall, `n` (0 or more), at evenly divided heights `i / (n + 1)` of the wall's datum-to-datum height, as purlins divide the rafter slope.
- Each girt runs horizontally in the wall's reference plane from post axis to post axis, one piece per wall, except where an opening cuts it (3d).
- The **straw bale** definition declares **0** girts. The stud infill count is design intent for Reference House 001 v3.
- **Fit:** with a brace plane on, every girt lies below the brace feet in its wall (`z − L` on the wall's upper plane), checked on the full candidate. A change that would put a girt across a brace is rejected.

### Studs (3c)

- Only walls whose definition has a stud framing layer (stud infill) get studs.
- Spacing comes from the definition, measured **from the wall's start post axis** (west for walls along X, south for walls along Y): positions `k · s` while short of the end post by more than 1e-6 m. No stud lies on a post axis.
- **Continuous studs:** one stud per position, from the wall's lower plane to its upper plane. Girts are **let in across the studs**; neither is cut at the crossing, and the notches are not modeled.
- A stud that meets a knee-brace axis ends on it.
- Studs are vertical in the wall's reference plane. Lengths are reference-axis lengths, not cut lengths. No bottom or top plates are generated.

### Framing at openings (3d)

- **`Opening` dimensions are rough-opening dimensions.** Unit sizes are not modeled.
- **Stud infill walls:**
  - **a king stud on each side,** continuous like any stud;
  - **a jack stud on each side,** inside the king, from the lower plane to the header, **only when the rough-opening width exceeds the definition's jack threshold width** (by more than 1e-6 m). At or below the threshold, the opening has kings only, with the header framed between them. There is one threshold, so at most one jack per side in VS-02b;
  - **a header** of the definition's header section, its underside at the rough-opening head; one piece, plies not counted separately;
  - **a rough sill** for windows;
  - **cripples:** a layout stud that falls between the kings is replaced by a piece from the header to the upper plane and, for windows, a piece from the lower plane to the rough sill. A layout stud that would overlap a king is dropped;
  - **girts are cut at openings:** a girt that crosses an opening stops at its kings.
- **Straw bale walls:** a **buck** for each opening: two jambs, a head, and, for windows, a sill. No kings or jacks.
- **The threshold is a declared value, not derived from any code.** It is versioned with the definition and named in the outputs, which make no compliance claim (AC-08). A jurisdiction-specific rule replaces it later, once code editions and applicability are decided (open question 5) and versioned by location.

### Sections position wall framing (amends D058 for wall framing only)

Kings and jacks sit beside each other, so their axes are offset from the rough-opening edge by the definition's stud thickness: a jack's by half a thickness, a king's by one and a half (or half, with no jack). The header's depth sets the cripples' lower end. A change to the stud or header section therefore moves opening framing. **The timber frame keeps D058:** its axes stay on datums, and sections never move them.

### Joints (3e)

- Wall framing gets **no joint records**. `Connection` joins two `TimberMember` records (D054), and the catalog has no fastening types. The connection catalog and the 312 connections are unchanged.
- An assumption line in the assembly schedule says that wall framing fastenings and attachments (stud ends, girt to post, headers, and opening framing) are not modeled or counted, as D059 did for post splices and sill joints.

## Rationale

- **Buildable and countable:** the builder gets every stud, girt, king, jack, header, sill, and cripple as a piece, as the direction requires.
- **Separate from the frame:** dimensional infill framing stays out of the heavy-timber schedule, its rule, its oracle, and its connection catalog, so VS-02's verified frame is untouched.
- **Straw bale stays honest:** no girts through the courses, and bucks rather than stud framing at openings.
- **Replaceable rules:** the jack threshold is a declared, versioned value, so a code-based rule can replace it without changing the model.
- **The D058 exception is local:** realistic king and jack positions need section offsets; confining them to wall framing keeps every frame axis, connection location, and selector unaffected by sections.

## Alternatives considered

- **Framing as an area-quantified layer** (the first recommendation): no pieces, no counts.
- **`STUD` and `GIRT` member roles in the timber frame,** with one "Walls" switch over the build-ups.
- **Studs stopping at girts; girts cut into blocks; layout from the building corner; generated plates** (3b, 3c).
- **One king and one jack at every opening; edge studs only, on datums** (3d).
- **Counted wall-framing joints with a fastening catalog; girt-to-post joints as a new junction class** (3e).

## What this does not decide

- Section, spacing, girt count, header section, and jack threshold values for Reference House 001 v3 (proposal 9).
- Opening records, commands, fit, and classification (proposal 6). Opening commands now regenerate wall framing, so their classification is revisited there; the fit rule must leave room for kings and jacks inside the bay.
- How the assembly schedule presents framing (proposal 7).
- Any structural, fire, or code claim about wall framing (AC-08, FR-07).
