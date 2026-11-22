# VS-02b — Scope and acceptance criteria

**Status:** Draft, under review (2026-11-21). Decided so far: proposal 1, the slice boundary, Option 1 ([D064](../../product/decisions/D064-vs02b-slice-boundary.md)); proposal 2, wall placement, as recommended ([D065](../../product/decisions/D065-vs02b-wall-placement.md)). proposal 3, wall framing, to the product owner's direction ([D066](../../product/decisions/D066-vs02b-wall-framing.md)); proposal 4, assembly definitions, as recommended ([D067](../../product/decisions/D067-vs02b-assembly-definitions.md)); proposal 5, one project-wide wall assembly, as recommended ([D068](../../product/decisions/D068-vs02b-wall-assembly-choice.md)); proposal 6, openings, as revised ([D069](../../product/decisions/D069-vs02b-openings.md)); proposal 7, quantities and outputs, as revised ([D070](../../product/decisions/D070-vs02b-quantities-and-outputs.md)); proposal 8, thermal and moisture values with a framing-corrected figure, as revised ([D071](../../product/decisions/D071-vs02b-thermal-moisture-values.md)); proposal 9, the Reference House 001 v3 design intent, as revised ([D072](../../product/decisions/D072-reference-house-001-v3-design-intent.md)). The routine items 10–15 are approved (2026-11-21). The acceptance criteria and task breakdown (§15–16) await approval. §5 lists the proposals: routine items may be approved together, and judgment items are discussed with the product owner one at a time ([AGENTS.md](../../../AGENTS.md), "Collaboration workflow"). The acceptance criteria (§15) and the task breakdown (§16) are drafts pending those decisions.  
**Roadmap line:** "Modular assemblies (straw bale and stud infill first), with walls and openings as needed, on the VS-02 frame" ([roadmap.md](../roadmap.md); [D051](../../product/decisions/D051-vs02-slice-boundary.md)).  
**Builds on:** VS-02, complete and verified by `TEST-002` ([vs-02.md](vs-02.md), [vs-02-traceability.md](vs-02-traceability.md)).  
**Requirements:** FR-05 (modular assemblies), D008 (straw bale and stud-wall infill), and the parts of FR-02 (walls, openings, assemblies), FR-08 (quantities and cost), and FR-10 (preliminary outputs) that walls need.

## 1. Where VS-02 leaves the product

VS-02 delivers a complete, generated timber frame on Reference House 001 v2:

- **Model:** schema version 2, rule `vs02-frame-1`, 193 members (posts, beams, sills, floor joists, principal rafters, purlins, knee braces) and 312 connections typed per junction class ([D052](../../product/decisions/D052-vs02-frame-members.md)–[D054](../../product/decisions/D054-vs02-connection-catalog.md), [D059](../../product/decisions/D059-vs02-junction-rules-connection-type-command.md)). Every axis lies on a datum, and sections never move one ([D058](../../product/decisions/D058-datum-reference-axes.md)).
- **Commands:** footprint, story heights, roof, grid, frame parameters, sections, and connection types, with preview, confirmation, and undo.
- **Artifacts:** `plan2d` (four planes), `mesh3d`, `timber_schedule` (members and connections), and `preliminary_estimate` (timber per meter, connections each). Selectors make `impacted_artifacts` exact, and unchanged payloads are reused across revisions ([D056](../../product/decisions/D056-dependency-selectors.md), [D061](../../product/decisions/D061-vs02-selector-contents.md)).
- **Browser:** both views, the Frame and Connections tabs, the schedule's tables, and the confirmation dialog ([D062](../../product/decisions/D062-vs02-browser-connections.md)).
- **Checks:** two traceability matrices, a golden scenario, property-based sequences with the if-and-only-if impact check, and payload size and time ceilings ([D063](../../product/decisions/D063-vs02-traceability-and-budgets.md)). The reference house's payloads sit at 66% of their 256 KiB ceiling.

Deliberately absent:

- walls, openings, and assemblies (FR-05). The model reserves the kinds `Wall`, `Opening`, `AssemblyDefinition`, `AssemblyInstance`, and `Layer` (building-model.md §3.2), and nothing defines them;
- girts and studs, which D052 deferred "with walls, in VS-02b";
- thermal, moisture, or any other material property data, and any dataset for them (open question 6);
- rooms, floors, roof assemblies, foundations, and MEP.

The reference house says the same: "Configurable straw bale or conventional stud-wall infill (later slices)", with assemblies listed as "still open" and not to be invented for engineering claims ([README](../../reference-projects/vermont-timber-house/README.md)).

## 2. What VS-02b adds

The roadmap names assemblies, with walls and openings "as needed". These are the candidate themes:

| Theme | What it would add | Value | Main prerequisites and risks |
|---|---|---|---|
| **A. Assembly definitions** | Reusable layered definitions for the two initial wall families, straw bale and stud infill: layers with thickness and material, and nullable property values with provenance | FR-05 and D008; the base for every envelope output | What a definition records, and where its values come from (open question 6). Values must be supplied or approved by the product owner, never invented |
| **B. Walls** | Wall records in the frame's perimeter bays, each with an assembly | The building gets an envelope in 2D, 3D, and the schedule; the straw bale versus stud comparison becomes possible (D014) | Where walls sit relative to the frame (in the bay, or outside it), whether they are generated or placed, and how they meet the knee braces that lie in the perimeter wall planes |
| **C. Openings** | Doors and windows placed in walls | Walls without openings give wrong areas and are of little use to a homeowner (vs-02.md §2) | The first **user-placed** records: their identity, how they survive frame edits, and what "fits" means |
| **D. Quantities and cost** | Wall areas net of openings, per-layer quantities, and estimate lines for them | The homeowner cost story (D009) and a builder's envelope takeoff | A quantity basis (reference or installed area), new price-book units, and a new artifact or an extended schedule |
| **E. Thermal and moisture values** | Declared layer values with provenance, and an assembly-level figure only when every input is known | The comfort story (D008), with honest assurance (principle 7) | No dataset exists (open question 6). Climate-specific details must be flagged unverified (FR-05). Nothing may read as code compliance |

Infill framing (studs, girts) belongs to themes A and B: it can be a layer of the stud-infill definition, or generated members (§8).

## 3. Scope options (proposal 1, decided as D064)

**Option 1: "Perimeter infill walls with openings"**, **chosen ([D064](../../product/decisions/D064-vs02b-slice-boundary.md), 2026-11-21)**: themes A–E for walls only.

- Two wall definitions, walls in every perimeter bay of both stories, user-placed doors and windows, net-area quantities, per-layer estimate lines, and declared thermal and moisture values.
- Roof, floor, and ceiling assemblies (also FR-05) wait for a later slice.
- **Why:** it delivers D008's comparison on the part of the envelope that the frame already bounds. Every perimeter bay is a rectangle between generated members, so placement can follow the grid, as members do.
- **Cost:** the envelope is incomplete: no roof, floor, or gable-end walls. Any thermal or area total must say "walls only".

**Option 2: "Walls without openings":** themes A, B, D, E.

- Smaller: no user-placed records yet.
- Gross areas overstate every quantity, and adding openings later changes the quantity basis, the schedule, and the estimate again.

**Option 3: "Whole envelope":** wall, roof, and floor assemblies, with openings.

- Completes FR-05's list and allows whole-envelope figures.
- Much larger: roof assemblies need decisions about what spans the purlins (decking, common rafters, or panels), and floor assemblies about the joists and the foundation, which is not modeled.

Proposals 2–9 build on Option 1.

## 4. Cross-cutting concerns (any option)

- **Schema version 3 replaces version 2** ([D055](../../product/decisions/D055-pre-release-schema-replacement.md); proposal 10): new kinds bump `model_schema_version` to 3. Version 2 snapshots are rejected with `UNSUPPORTED_SCHEMA_VERSION`, with no readers or migrations, and local databases are recreated.
- **Reference House 001 v3:** the definitions, the default assembly, and any openings need design intent supplied or approved by the product owner and recorded in a decision, as D025 and D053 were (proposal 9).
- **Frame unchanged:** members, connections, and their counts stay as VS-02 left them (193 and 312), unless proposal 3 adds infill members.
- **Engineering boundary unchanged:** everything stays preliminary (AC-08). Walls make no structural, fire, energy-code, or moisture-performance claim. VS-04 owns analysis.
- **Determinism and golden tests:** the golden record, UI fixtures, and both existing matrices are regenerated for version 3 as reviewed diffs (D055). VS-01's and VS-02's criteria keep their meaning against the v3 house.
- **Browser:** walls and openings need 2D and 3D rendering, an assembly selector, an opening editor, and schedule and estimate tables (UI-002 and UI-003 patterns).
- **Budgets:** walls add data to `plan2d` and `mesh3d`, and a new artifact may be added. D063's per-payload ceilings (256 KiB and 2 MB) leave room, but D063 does not decide budgets for VS-02b's new payloads (proposal 15).

## 5. Proposals

| # | Proposal | Mark | Section |
|---|---|---|---|
| 1 | ~~Slice boundary: Option 1, 2, or 3~~ **Decided: Option 1** ([D064](../../product/decisions/D064-vs02b-slice-boundary.md)) | **Your judgment** | §3 |
| 2 | ~~Where walls go, and how they relate to the frame~~ **Decided as recommended** ([D065](../../product/decisions/D065-vs02b-wall-placement.md)) | **Your judgment** | §7 |
| 3 | ~~Infill framing: studs and girts~~ **Decided: generated wall framing owned by each wall, with kings and jacks by a width threshold** ([D066](../../product/decisions/D066-vs02b-wall-framing.md)) | **Your judgment** | §8 |
| 4 | ~~Assembly definitions: what they record, and where they live~~ **Decided as recommended** ([D067](../../product/decisions/D067-vs02b-assembly-definitions.md)) | **Your judgment** | §9 |
| 5 | ~~Choosing a wall's assembly: granularity, command, classification~~ **Decided as recommended** ([D068](../../product/decisions/D068-vs02b-wall-assembly-choice.md)) | **Your judgment** | §10 |
| 6 | ~~Openings: records, commands, fit, survival, classification~~ **Decided as revised** ([D069](../../product/decisions/D069-vs02b-openings.md)) | **Your judgment** | §11 |
| 7 | ~~Quantities and outputs: quantity basis, a new artifact, estimate lines~~ **Decided as revised** ([D070](../../product/decisions/D070-vs02b-quantities-and-outputs.md)) | **Your judgment** | §12 |
| 8 | ~~Thermal and moisture values: what is recorded, and what is computed~~ **Decided as revised: declared values and a framing-corrected figure** ([D071](../../product/decisions/D071-vs02b-thermal-moisture-values.md)) | **Your judgment** | §13 |
| 9 | ~~Reference House 001 v3 design intent~~ **Decided as revised** ([D072](../../product/decisions/D072-reference-house-001-v3-design-intent.md)) | **Your judgment** | §14 |
| 10 | Schema version 3 replaces version 2 — **approved** | Routine | §6 |
| 11 | Walls follow the frame's identity and conformance rules — **approved** | Routine | §6 |
| 12 | Selectors and exact impact for the new data and artifact — **approved** | Routine | §6 |
| 13 | Still preliminary, with an unverified-climate warning — **approved** | Routine | §6 |
| 14 | Browser follows the UI-002 and UI-003 patterns — **approved** | Routine | §6 |
| 15 | Traceability and budgets in D063's form — **approved** | Routine | §6 |

**Order of discussion:** 1 first, then 2–9 in order, because each builds on the ones before it. The routine items 10–15 follow from D041, D042, D046, D055, D056, D061, D063, AC-08, and FR-05; they can be approved together now that 1 is settled. Approved judgment items are recorded as decisions: D064 is proposal 1, D065 proposal 2, D066 proposal 3, D067 proposal 4, D068 proposal 5, D069 proposal 6, D070 proposal 7, D071 proposal 8, D072 proposal 9.

## 6. Routine items (10–15)

**Approved together** (2026-11-21). They follow from earlier decisions, so no new decision record is needed; the task files carry them out.

10. **Schema version 3 replaces version 2** (D055). New kinds and fields bump `model_schema_version` to 3. Record versions stay per kind (building-model.md §3.3): new kinds start at 1, and a changed kind's version moves. The committed schema export becomes `snapshot.v3.schema.json`. Version 2 snapshots are rejected with `UNSUPPORTED_SCHEMA_VERSION`, and the migration runner refuses a database that holds them. New detail codes go into building-model.md §6.1 by stage (D035).
11. **Walls and wall framing follow the frame's identity and conformance rules.** Walls (D065) get generation keys built from grid-line IDs and the story (D042), IDs minted from `"generation/" + key` (D041), and stage-5 conformance codes like the members' (D046). Wall framing (D066) is keyed under its wall's key, and opening framing under the opening's ID (D069). Surviving keys keep their IDs; removed keys are retired and never reused. Key formats are set in the task file.
12. **Selectors and exact impact.** Every new or changed artifact declares a selector holding exactly what its builder reads (D061), and AC2-04's if-and-only-if property extends to it. The existing artifacts' selections change only where their payloads gain wall or opening data. The new commands get rows in the classification table, as a new version `vs02b-change-classes-1` (dependencies.md §4.1): `SetWallAssembly` consequential (D068), and `AddOpening`, `SetOpening`, and `RemoveOpening` routine (D069).
13. **Still preliminary.** Every new output carries `suitability: "preliminary"`, false claims, and `PRELIMINARY_UNVERIFIED` (AC-08). FR-05's "flag unverified climate-specific details" becomes a warning on every output that reports assembly properties (working name `CLIMATE_DETAILS_UNVERIFIED`). No output carries a code-compliance or performance claim.
14. **Browser.** Walls, wall framing, and openings are drawn in 2D and 3D, with the Wall layers and Wall framing switches (D066), and their commands use the existing preview and apply flows: consequential commands through the confirmation dialog, routine ones applied with undo (UI-002, UI-003). Tabs, colors, and labels are set in the UI task file.
15. **Traceability and budgets.** A separate `vs-02b-traceability.md`, one row per criterion bullet, checked against this file's IDs and wording, as D063 set for VS-02. The VS-01 and VS-02 matrices stay enforced. D063's per-payload ceilings (256 KiB for the reference house, 2 MB for the largest supported case) apply to every payload, new ones included (wall framing enlarges `plan2d`, `mesh3d`, and the assembly schedule), and D063's stop-and-report rule applies if a measurement passes half a ceiling.

## 7. Proposal 2: where walls go (decided as D065)

**Question:** which surfaces get walls, how a wall relates to the frame, and whether walls are generated or placed.

**Recommendation**, **approved as recommended ([D065](../../product/decisions/D065-vs02b-wall-placement.md), 2026-11-21)**:

- **Where:** one wall in every **perimeter bay of each story**: between two adjacent grid stations on a perimeter grid line, from the story's lower datum to its upper one (Level 0: `z0` to `z1`; Level 1: `z1` to `z_eave`). The count is `2 · ((nx − 1) + (ny − 1))` per story. Reference House 001: 10 per story, **20 walls**, with reference areas of 1,200 sf on Level 0 and 1,080 sf on Level 1 (2,280 sf, 211.8189312 m²; from the D025 dimensions).
- **Relation to the frame: in-plane infill.** The wall fills the bay between posts, and its reference plane is the grid line, as member axes are (D058). The definition's layers are placed symmetrically about it unless proposal 9's build-ups say otherwise. "Infill" is the word D008, the vision, and the roadmap use.
- **Generated, not placed,** as members and connections are: walls regenerate with the frame, keep their IDs under footprint, story, and roof edits, and are removed or added with grid lines (D042). Users cannot remove a wall to leave a bay open in VS-02b.
- **Not in VS-02b:** gable-end triangles above the eave tie beams (216 sf on the reference house), interior partitions, rooms, and walls off the grid.

**Consequences to accept:**

- **Knee braces lie in the perimeter wall planes.** With both brace planes on, each perimeter wall has a brace in each top corner: 40 of the reference house's 68 braces. In-plane infill would be notched or cut around them. Quantities ignore them (proposal 7), and an assumption line says so.
- **Bales are thicker than posts.** An in-plane straw bale wall (about 18" thick) projects beyond 8×8 posts on both sides. That is a display and detailing fact, not a placement problem, because the plane stays on the grid line.

**Alternatives:**

- **Outside the frame (a wrap):** common for straw bale on timber frames, because it keeps the frame exposed inside and avoids bridging at the posts. Its reference plane would sit at the frame's outer face, which depends on post sections, so sections would move walls (D058 avoided this for members).
- **Per family:** straw bale outside, stud infill in plane. Two placement rules.
- **User-placed walls** (an `AddWall` command): needed eventually for interior walls and off-grid walls. Hand placement needs its own identity and validation story, as D054 said of connections.
- **Gable-end walls now:** completes the end walls, but needs triangular panels in 2D, 3D, and quantities.

## 8. Proposal 3: infill framing (decided as D066)

**Decided** ([D066](../../product/decisions/D066-vs02b-wall-framing.md), 2026-11-21). The sections below keep the discussion: the product owner's direction (§8.1), and the five sub-questions with what was chosen (§8.2).

D052 deferred "girts and studs (with walls, in VS-02b)". This proposal decides whether VS-02b generates them.

### 8.1 Product owner direction (2026-11-21)

The first recommendation (stud framing as an area-quantified layer, with no stud or girt members) was **not adopted**. The product owner's direction:

- the walls stay a **separate layer that can be toggled on and off**;
- the user and the builder **see every stud and girt**;
- stud and girt **counts are available to the builder**.

So VS-02b generates studs and girts as individual pieces. The direction leaves the questions in §8.2 open. They are discussed one at a time, as 3a–3e, and recorded together as one decision when all are settled.

### 8.2 Open sub-questions

**3a. Where studs and girts live.** **Settled (2026-11-21): separate wall framing.**

- **Chosen:** studs and girts are a **separate wall-framing record kind owned by each wall**, not `TimberMember` records. They are generated with their wall, listed in the assembly schedule (counts and lengths for the builder) rather than the timber schedule, and drawn with the walls.
- **Why:** dimensional infill framing stays out of the heavy-timber schedule, its member rule, and its connection catalog.
- **Consequences:**
  - the frame is unchanged: 193 members and 312 connections, the `vs02-frame-1` rule, and its oracle;
  - each piece's section and spacing come from its wall's assembly definition (the framing layer, proposal 4), not from `member_defaults`, so `SetMemberSection` does not apply to them;
  - stud and girt counts and lengths are in the assembly schedule (proposal 7), so the builder has two framing lists: heavy timber in the timber schedule, wall framing in the assembly schedule;
  - `Connection` joins two `TimberMember` records (D054), so wall framing gets no connection records unless 3e decides otherwise.
- **Not adopted:** `STUD` and `GIRT` member roles in the timber frame, with a single "Walls" switch over the build-ups only.

**3a′. Seeing the framing inside a wall.** **Settled (2026-11-21) as recommended: two switches.** Because wall framing is drawn with the walls, the build-up layers (plaster, bales, sheathing, insulation) would cover it. *Recommendation:* the wall layer has **two display switches** in both views: **"Wall layers"** (the build-ups) and **"Wall framing"** (studs and girts). Turning wall layers off shows the framing; turning both off shows the bare timber frame. Both are on by default, remembered per browser, and display only: schedules are unaffected (as D062's Connections switch). *Alternative:* one "Walls" switch over both, with the build-ups drawn translucent so the framing shows through.

**3b. Where girts go.** **Settled (2026-11-21) as recommended.** Which walls get girts, how many, at what height, and whether straw bale walls get them.

- **Recommendation:** girts are **declared by the assembly definition**, as part of its framing layer:
  - a girt count per wall, `n` (an integer, 0 or more), at evenly divided heights `i / (n + 1)` of the wall's datum-to-datum height, as purlins divide the rafter slope (D052);
  - each girt runs horizontally in the wall's reference plane from post axis to post axis, one piece per wall, not continuous across posts;
  - every wall that uses the definition gets them; the section comes from the definition (3a);
  - the **straw bale** definition declares **0** girts, because in-plane bales are laid in courses from sill to beam and a girt would interrupt them. The **stud infill** count is design intent (proposal 9; strawman: 1, at mid-height);
  - **fit:** with a brace plane on, every girt must lie below the brace feet in its wall (`z − L` on the wall's upper plane), checked on the full candidate as the brace fit is. A frame or definition change that would put a girt across a brace is rejected. On the reference house a mid-height girt is at 5'-0" on Level 0 (brace feet at 7'-0") and 4'-6" on Level 1 (brace feet at 6'-0"). How girts meet openings is 3d.
- **Alternatives:**
  - **girts in every perimeter wall, whatever its assembly** (nailers for cladding as part of the frame): straw bale walls then carry girts through their courses;
  - **girts at a fixed height** (for example the window head height), rather than divided: aligns with openings, but couples framing to a value that stories of different heights share;
  - **no girts in VS-02b:** simplest, but D052 deferred girts to VS-02b, and the direction in §8.1 asks to see them.

**3c. Stud layout.** **Settled (2026-11-21): continuous studs, with girts let in across them.** Which walls get studs, the spacing and where it is measured from, and how studs meet girts and braces.

- **Chosen** (the recommendation, with continuous studs in place of studs that stop at girts):
  - **Which walls:** only walls whose definition has a stud framing layer (stud infill). Straw bale walls have none.
  - **Spacing** comes from the definition's framing layer (3a; strawman 24" on center, proposal 9). It is measured **from the wall's start post axis** (the lower grid station: west for walls along X, south for walls along Y), as joists are measured from each bay's west beam line: positions `k · s` for `k = 1, 2, …` while short of the end post by more than 1e-6 m. No stud lies on a post axis, and a wall no wider than the spacing has no studs.
  - **Continuous studs:** one stud per position, from the wall's lower plane (sill or Level 1 beam) to its upper plane. Girts stay one piece from post to post (3b) and are **let in across the studs**: studs and girts cross in the wall's plane, and neither is cut at the crossing. An assumption line says the let-in notches are not modeled.
  - **Studs stop at braces:** a stud that meets a knee-brace axis ends on it, so studs within the brace leg of a post are shorter. With 3' legs and 24" spacing, the stud 2' from each post ends 1' below the beam.
  - **Axes on datums,** as D058 set for members: studs lie in the wall's reference plane, vertical, and lengths are reference-axis lengths, not cut lengths.
  - **No plates:** the sill and beams are the datums studs end on. Bottom and top plates are not generated, and an assumption line says so.
  - **For scale:** with the strawman (24", 1 girt), every stud infill wall has 5 studs and 1 girt before openings: 100 studs and 20 girts on the reference house's 20 walls if all are stud infill.
- **Not adopted:** studs stopping at girts (`n + 1` pieces per position); girts cut into blocks between studs; layout from the building corner; generated plates.

**3d. Framing at openings.** **Settled (2026-11-21): the revised recommendation, with jacks set by a width threshold.** Whether doors and windows get generated framing, so that the stud and girt counts are complete.

- **Chosen:** the revised recommendation below, except that **"where required" is a width threshold** in place of "every opening":
  - the stud infill definition's framing layer declares a **jack threshold width**. An opening whose rough-opening width **exceeds** it (by more than 1e-6 m) gets **a king and a jack on each side**, with the header bearing on the jacks;
  - an opening no wider than the threshold gets **a king on each side** and no jacks, with the header framed between the kings;
  - the threshold is design intent for Reference House 001 v3 (proposal 9). It is a declared value, **not derived from any code**, and the outputs say so;
  - the rest stands: rough-opening dimensions, cripples, girts cut at the kings, header sections, straw bale bucks, and section offsets for wall framing as an exception to D058 (wall framing only);
  - a jurisdiction-specific rule (for example more jacks for wider headers, from the local code) replaces the threshold later (open question 5).
- *Reading stated to the product owner and not corrected; recorded in D066:* below the threshold, kings and a header remain; one threshold, so at most one jack per side in VS-02b.

**Product owner direction (2026-11-21):** the framing must be **realistically buildable**, so **king and jack studs are included where required**. Eventually, "where required" is to **depend on the local building code**. The first recommendation (one edge stud per side, no jacks, no section offsets) is not adopted.

- **Revised recommendation:** generated opening framing, as wall-framing pieces of the opening's wall, regenerated whenever the wall or the opening changes.
  - **The opening's size is its rough opening:** `Opening` width and height (proposal 6) are rough-opening dimensions, the clear space the framing leaves. Unit sizes are not modeled.
  - **Stud infill walls:**
    - **a jack stud on each side,** from the wall's lower plane to the underside of the header, its inner face on the rough-opening edge;
    - **a king stud on each side,** outside the jack, continuous from the lower to the upper plane like any stud (3c), stopping at braces;
    - **a header** across the opening between the kings, bearing on the jacks, its underside at the rough-opening head;
    - **a rough sill** for windows, between the jacks at the rough-opening sill;
    - **cripples:** a layout stud (3c) that falls between the kings is replaced by a piece from the header to the upper plane and, for windows, a piece from the lower plane to the rough sill. A layout stud that would overlap a king is dropped;
    - **girts are cut at openings:** a girt that crosses an opening stops at its kings.
  - **"Where required" in VS-02b:** every opening in a stud infill wall gets **one king and one jack on each side**. This is a **declared framing rule, versioned and named in the outputs, and not derived from any code**. It is the kind of rule that a jurisdiction-specific rule replaces later (for example more jacks for wider headers), once code editions and applicability are decided (open question 5) and versioned by location (overview.md, "Safety, reliability, and data requirements"). Outputs say the rule is not code-derived, and make no compliance claim (AC-08).
  - **Sections now position wall framing:** a jack's axis is half a stud thickness outside the rough-opening edge, and a king's one and a half thicknesses; the header's depth sets the cripples' lower end. These offsets use the definition's stud and header sections (3a). This is a deliberate **exception to D058 for wall framing only**: D058 still holds for the timber frame, whose axes stay on datums. A change to the stud or header section therefore moves opening framing.
  - **Header section:** a header has its own section in the definition's framing layer (design intent, proposal 9). It is one piece of that section; plies of a built-up header are not counted separately.
  - **Straw bale walls:** a **buck** for each opening: two jambs, a head, and, for windows, a sill, on the rough-opening edges. No kings or jacks.
  - **Example:** a 3'-0" window centered in a 12' stud infill bay at 24", with 1½"-thick studs, has its rough-opening edges at 4'-6" and 7'-6". Jacks are at 4'-5¼" and 7'-6¾", kings at 4'-3¾" and 7'-8¼". The layout studs at 2', 4', 8', and 10' stay, the one at 6' becomes two cripples, and the mid-height girt becomes two pieces.
- **Alternatives:**
  - **jacks only where a declared width threshold is exceeded** (a value in the definition): closer to "where required", but the threshold would be an invented number until a code module supplies it;
  - **edge studs only, on datums** (the first recommendation): keeps D058 for wall framing, but is not buildable as drawn.
- **Knock-on:** opening commands regenerate wall framing, so proposal 6's recommendation that they are routine is revisited. Proposal 6 also takes the rough-opening meaning of `Opening` dimensions, and its fit rule must leave room for kings and jacks inside the bay.

**3e. Joints.** **Settled (2026-11-21) as recommended.** Whether studs, girts, and opening framing get joint records.

- **Recommendation: no joint records for wall framing.**
  - `Connection` joins two `TimberMember` records (D054), and wall framing is a separate kind (3a), so it gets no `Connection` records. The connection catalog (`vs02-connections-1`), the 312 connections, and the timber schedule's connection tables are unchanged.
  - Wall framing is nailed or screwed, and the catalog has no fastening types. Girts let into studs and attached to posts (3c) are fastened the same way.
  - An assumption line in the assembly schedule says: wall framing fastenings and attachments (stud ends, girt to post, headers, and opening framing) are not modeled or counted. D059 did the same for post splices and sill joints.
- **Alternatives:**
  - **counted joints between wall framing pieces,** with a small fastening catalog (for example nailed, screwed, bracket): a fuller takeoff, but every type and count rule would be invented until fastening is specified (FR-04's fabrication information);
  - **girt-to-post joints only,** as a new junction class: the one joint with heavy-timber character. D059 requires a new catalog version with a traditional and an engineered type, and `Connection` would have to join a wall-framing piece to a member.

### 8.3 Knock-on effects to revisit

- **Proposal 6 (openings):** if 3d generates opening framing, opening commands regenerate members, so the recommendation that they are routine is revisited (dependencies.md §4).
- **Proposal 5 (assembly choice):** switching the wall assembly then adds or removes every stud, which is already consequential.
- **Proposal 7 (quantities):** stud and girt counts and lengths are in the assembly schedule (3a), beside the wall areas and the non-framing layers.
- **Proposal 9 (design intent):** girt positions and sections, stud spacing and section, and opening framing sizes need values for Reference House 001 v3.
- **§15, §16:** the timber frame stays at 193 members and 312 connections (3a), but walls gain generated framing, with its own keys, conformance, and oracle coverage. The task breakdown and AC2b-03 are revised once 3a–3e are settled.
- **Proposal 15 (budgets):** wall framing enlarges `plan2d`, `mesh3d`, and the assembly schedule.

## 9. Proposal 4: assembly definitions (decided as D067)

**Question:** what an assembly definition records, and where definitions live.

**Recommendation**, **approved as recommended ([D067](../../product/decisions/D067-vs02b-assembly-definitions.md), 2026-11-21)**:

- **Content:** an `AssemblyDefinition` has a family (`STRAW_BALE` or `STUD_INFILL`), a unique label, an ordered list of layers from exterior to interior, a short installation note (text, not checked), and a list of climate-specific details to flag as unverified (FR-05). Each `Layer` has a material, a thickness, a function (for example finish, sheathing, insulation, framing), and nullable property values, each with provenance (proposal 8). The **framing layer** of the stud infill definition adds the stud section and spacing, the girt count and section, the header section, and the jack threshold width; the straw bale definition's framing is its girt count (0) and its buck section ([D066](../../product/decisions/D066-vs02b-wall-framing.md)).
- **Snapshot records,** copied from the template into each project, like `Section` and `Material`: catalog records that may be unreferenced (D038). The model stays the single source (principle 4), and every output names the revision whose definitions it used (principle 6).
- **Fixed in VS-02b:** the template's two definitions only. Users cannot author or edit definitions or layers yet. "Reusable" (FR-05) means reused by every wall in the project; a library shared across projects comes later.
- **Materials** are `Material` records, as for timber, with unknown properties `null` (D025).

**Alternatives:**

- **A global versioned catalog,** like the connection catalog (`vs02-connections-1`), referenced by key. That suits keys that are representational only. Definitions carry quantities and property values that users will later edit, which belong in the model.
- **User-authored definitions now** (commands to add and edit layers): FR-05's full intent, but it needs validation rules for build-ups and doubles the command surface.

## 10. Proposal 5: choosing a wall's assembly (decided as D068)

**Question:** at what granularity a wall's assembly is chosen, by which command, and how the command is classified.

**Recommendation**, **approved as recommended ([D068](../../product/decisions/D068-vs02b-wall-assembly-choice.md), 2026-11-21)**:

- **One project-wide wall default:** a new field holds the default definition, and every generated wall takes it, as members take `member_defaults` (D039).
- **One command,** `SetWallAssembly {assembly_definition_id}` (working name), which switches every wall. A definition not in the project is `DANGLING_REFERENCE`, and the current value is a no-op (D045).
- **Consequential:** it changes every wall, its wall framing (studs, girts, and opening framing become bucks, or the reverse; D066), and the estimate at once, which dependencies.md §4 classes as consequential, as `SetConnectionType` is (D059).

**Why:** it delivers the whole-house straw bale versus stud comparison (D008, D014) with one command, and no override needs to survive regeneration. D040 deferred per-member overrides for the same reason.

**Alternatives:**

- **Per elevation and story** (south, north, east, west, times two): allows a stud south wall with more glass and straw bale elsewhere. A fixed set of eight defaults, still no overrides.
- **Per wall:** a default plus overrides keyed by the wall's generation key. The most flexible, and the natural next step. It needs a rule for overrides whose wall disappears.

## 11. Proposal 6: openings (decided as D069)

**Decided as revised** ([D069](../../product/decisions/D069-vs02b-openings.md), 2026-11-21).

**Question:** what an opening is, how it is placed and edited, what "fits" means, what happens to it when its wall changes, and how its commands are classified.

*Revised for [D066](../../product/decisions/D066-vs02b-wall-framing.md):* opening dimensions are rough-opening dimensions, openings now generate wall framing, and the fit rule must leave room for that framing.

**Recommendation:**

- **Record:** an `Opening` has a kind (`WINDOW` or `DOOR`), its wall's ID, a **rough-opening** width and height, a sill height above the wall's lower datum (0 for a door), and an offset of its rough opening along the wall from the wall's start. It is a rectangle in the wall's reference plane. Doors and windows are voids, not products: no unit size, frame, glazing, or hardware data.
- **User-placed:** the first user-authored records. They have no generation key. IDs are minted from the command (D041), and `UndoToRevision` restores them (D044). Their framing is generated from them (D066), keyed by the opening's ID.
- **Commands:** `AddOpening`, `SetOpening` (replaces one opening's dimensions and position), and `RemoveOpening` (working names).
- **Fit,** checked on the full candidate snapshot, as the brace fit is (building-model.md §3.3). The **framed opening** is the rough opening plus its framing (D066): in stud infill walls, the kings (and jacks above the threshold) on each side and the header above; in straw bale walls, the buck. Then:
  - the framed opening lies inside the wall's reference rectangle (axis to axis, datum to datum);
  - it stays clear of the knee-brace axes in that wall;
  - framed openings in one wall do not overlap.

  Post, sill, and beam sections are not deducted, because the frame's axes stay on datums (D058). An assumption line says the fit does not check clearance to member faces. Exact rules and codes are set in the task file.
- **When the wall or its assembly changes:**
  - a frame edit that keeps the wall's key keeps the opening, at the same offset and size, and regenerates its framing;
  - a change after which an opening no longer fits is **rejected**, naming the opening and the edited field (AC-06's contradictory constraints). That includes a frame edit and a `SetWallAssembly` whose framing would not fit. Nothing moves or shrinks an opening silently (principle 3);
  - a grid edit that removes the wall removes its openings and their framing, and the preview lists them. Such edits are already consequential.
- **Routine:** the three opening commands regenerate only their own wall's framing (D066). They change no timber member, no connection, and no other wall, so they are applied with undo, like VS-01's routine edits. The commit still validates fully, and a preview is available.
- **Strawman check:** a 3'-0" window centered in a 12' bay with 3' brace legs and 1½" studs keeps its kings' outer faces at 4'-3" and 7'-9" from the start post with jacks (4'-4½" and 7'-7½" without), clear of the braces (proposal 9).

**Alternatives:**

- **Openings as consequential:** every window edit goes through the confirmation dialog, because it regenerates framing. More conservative, and slower for the most frequent edit a homeowner makes.
- **Reject any grid edit that would remove a wall with openings:** nothing user-authored is ever removed as a side effect, but the user must first remove the openings.
- **Generated openings** (for example one window per bay from a parameter): no user-authored records yet, but not how anyone places windows.

## 12. Proposal 7: quantities and outputs (decided as D070)

**Decided as revised** ([D070](../../product/decisions/D070-vs02b-quantities-and-outputs.md), 2026-11-21).

**Question:** how wall quantities are measured, which artifact reports them, and how the estimate prices them.

*Revised for [D066](../../product/decisions/D066-vs02b-wall-framing.md) and [D069](../../product/decisions/D069-vs02b-openings.md):* wall framing is counted piece by piece in the assembly schedule, and openings are rough openings.

**Recommendation:**

- **Reference area:** a wall's gross area is its bay length between grid stations times its story height between datums. Rough-opening areas are subtracted to give its net area. This is a **reference area, not an installed area**, as member lengths are reference-axis lengths: member faces, braces, and the framing around openings are not deducted. The output says so.
- **Layer quantities:** each non-framing layer's area is the wall's net area, and its volume is that area times the layer's thickness. The framing layer is quantified by its pieces, not by area.
- **Wall framing quantities:** one row per piece (D066): its key, wall, kind (stud, girt, king, jack, header, rough sill, cripple, buck jamb, buck head, buck sill), section, and reference-axis length. Aggregates give the **count and total length per kind and section**, the builder's framing takeoff.
- **A new artifact, `assembly_schedule`,** owned by the `assemblies` module (overview.md):
  - one row per wall: its key, story, elevation side, definition, and gross, opening, and net areas;
  - one row per opening: its kind, rough-opening size, wall, and whether it has jacks;
  - one row per wall framing piece, as above;
  - aggregates: area per definition; area and volume per definition and non-framing layer; framing count and length per kind and section; opening counts per kind;
  - its assumptions (D066, D069, and the lines below), and the property figures of proposal 8.

  The timber schedule stays about the heavy-timber frame. The manifest lists five types, which amends artifacts.md §1 and §3 ("all four").
- **Views:** `plan2d` shows each wall as an outline of its total thickness on its story's plane, with gaps at openings, and wall framing in plan. `mesh3d` shows the wall layers as boxes with rectangular voids, and each wall framing piece as a box of its section. Both tag wall layers and wall framing separately, for the two switches (D066). New payload fields and a new generator version.
- **Estimate:**
  - **layers:** one line per definition and non-framing layer, key `assembly.<label>.<layer>`, priced per square meter of net area (unit `m2`);
  - **wall framing:** one line per framing kind and section, key `wallframing.<kind>.<section label>`, priced per meter of reference-axis length (unit `m`), like timber lines. Counts are shown beside the lengths;
  - the price book's units gain `m2`, with `PRICE_UNIT_MISMATCH` for an `assembly.` key without `m2` or a `wallframing.` key without `m`. Unpriced lines stay unpriced, never 0 (artifacts.md §8.1).
- **Openings are not priced** in VS-02b. Windows and doors are products, and no product data exists. An assumption line says the estimate excludes them.
- **Not counted:** bale counts, which need course rules; plates; let-in notches; and fastenings (D066). Assumption lines say so.

**Alternatives:**

- **Clear area between member faces:** closer to what is installed, but areas then depend on post and beam sections, so a section change would change every wall quantity.
- **Walls and wall framing in `timber_schedule`:** no new artifact type, but D066 kept wall framing out of the timber schedule, and every wall edit would impact it.
- **Wall framing priced per piece** (`each`, by kind and section): matches how studs are bought, but a precut length per piece is not known (lengths are reference-axis lengths), so a per-piece price would hide length differences.
- **Price per definition** (one line per square meter of assembly, framing included): simpler for a homeowner; a builder can't price layers or framing.

## 13. Proposal 8: thermal and moisture values (decided as D071)

**Decided as revised** ([D071](../../product/decisions/D071-vs02b-thermal-moisture-values.md), 2026-11-21).

**Question:** what property data a layer records, and what, if anything, is computed from it.

**Product owner direction (2026-11-21):** provide a **figure corrected for framing**. D066 generates every stud, girt, and opening piece, so the framing fraction is known from the model, and the figure can set the product apart. The first recommendation (a layer sum only) is revised below.

**Revised recommendation:**

- **Recorded per layer:** a declared thermal conductivity or thermal resistance, and a vapor permeance, each nullable and each with provenance (source, date, and a note). Unknown is `null`, never 0 (building-model.md §2).
- **The framing layer has two materials:** its framing material (the studs, girts, and opening pieces) and its fill (for example dense-pack cellulose between studs), each with its own nullable conductivity. In straw bale walls, the bale layer is the fill and the buck is the framing material. This extends D067's framing layer.
- **Recorded per definition:** the climate-specific details to flag as unverified, for example plaster and rain-screen detailing, and bale moisture protection at the sill. They appear with every figure, under the warning of proposal 13.
- **Computed, per wall:**
  - **framing fraction** `f`: the face area of the wall's framing pieces in its plane (each piece's section width in the wall plane times its reference-axis length, with stud and girt crossings counted once), divided by the wall's net area. It comes from the generated pieces, so it reflects the spacing, girts, kings, jacks, headers, and bucks of that wall and its openings;
  - **two path resistances:** through the fill, the sum of every layer's resistance with the framing layer at its fill value; and through the framing, the same with the framing layer at its framing material's value;
  - **framing-corrected value:** the **parallel-path** combination, `U = f / R_framing + (1 − f) / R_fill`, reported as a U-value and as its effective R-value;
  - **center-of-cavity value:** `R_fill` alone, reported beside it, so the framing penalty is visible.
- **Computed, per definition and for all walls:** area-weighted figures over net wall area (the walls' sum of `U × area`, and the average U), **opaque walls only**. No whole-envelope or heat-loss figure: there are no roof, floor, or opening values.
- **Gating:** a figure is computed only when every value it uses is known; otherwise it is `null`, with the missing layers or materials named. The method is named and versioned in the output (for example `parallel-path-1`), as the jack threshold is (D066).
- **Labels:** "parallel-path method, framing fraction from the generated framing; heavy-timber frame members in the wall plane, air leakage, and moisture effects are not included; declared values, not verified; not a code-compliance calculation". No output claims energy-code compliance (AC-08).
- **Moisture:** recorded only. No hygrothermal analysis and no condensation claim.
- **Values:** come from proposal 9. Unless the product owner supplies values with a source, they are `null`, because open question 6 (dataset sources and licensing) is still open. With every value `null`, the reference house shows the framing fractions and no U-values.

**Not included, and why:**

- **The heavy-timber frame as a bridge:** posts, sills, beams, and braces lie in the wall plane (D065), but they do not span the full wall thickness, so each needs a path of its own through part timber and part fill. That is a heavier method, and it depends on member sections. A later method version can add it.
- **Isothermal-planes or two-dimensional methods:** more accurate for some build-ups, but they need more data and a stated method choice per layer.

**Alternatives:**

- **Record the values and compute only the layer sum** (the first recommendation): simplest, but it hides the framing penalty that the generated framing makes computable.
- **Record the values and compute nothing:** the safest, but the comfort comparison then needs the reader to do arithmetic.

## 14. Proposal 9: Reference House 001 v3 design intent (decided as D072)

**Decided as revised** ([D072](../../product/decisions/D072-reference-house-001-v3-design-intent.md), 2026-11-21).

**Question:** the values the v3 fixture needs, supplied or approved by the product owner and recorded in a decision, as D053 was. They are **illustrative values for a test house, not a specification**. Nothing about them is checked or claimed (AC-08). Every D025 and D053 value is unchanged.

*Revised for D066–D071:* the definitions now need framing values (D066, D067), the framing layer needs a framing material and a fill (D071), and the openings should exercise both sides of the jack threshold.

To be supplied, changed, or approved:

| Item | Strawman, for the product owner to change |
|---|---|
| Default wall assembly | Straw bale (the D008 story); stud infill as the alternative (D068) |
| Straw bale build-up, exterior to interior | Lime plaster 1½"; straw bales laid flat 18" (the fill); clay plaster 1" |
| Straw bale framing | Girts: 0 (D066). Bucks: 1½" × 18" (the bale depth), spruce-pine-fir |
| Stud infill build-up, exterior to interior | Wood siding ¾"; sheathing ½"; framing layer 5½" (2×6 studs, dense-pack cellulose fill); gypsum board ½" |
| Stud infill framing | Studs 2×6 (1½" × 5½" actual), 24" on center, spruce-pine-fir. Girts: 1 per wall, at mid-height, 2×6. Headers: 2×8 (1½" × 7¼"), one piece. Jack threshold width: 4'-0" |
| Materials | One `Material` per layer and framing material (lime plaster, straw, clay plaster, siding, sheathing, spruce-pine-fir, cellulose, gypsum board), with properties `null` unless supplied |
| Property values | `null`, unless the product owner supplies values with a source (D071). With all `null`, the reference house shows framing fractions and no U-values |
| Openings | One 3'-0" × 6'-8" door, centered in the middle Level 0 bay of the south wall. One 5'-0" × 4'-0" window, sill at 3'-0", centered in each outer Level 0 bay of the south wall (wider than the threshold, so with jacks). One 3'-0" × 4'-0" window, sill at 3'-0", centered in each of the other 17 walls (no jacks) |

**Checks on the strawman:**

- **Fit (D069):** a 3'-0" opening's kings have their outer faces 4'-4½" from each post, and a 5'-0" window's kings (with jacks) 3'-3", both clear of the 3' brace legs. Window heads at 7'-0" with 2×8 headers stay below the upper planes (10'-0" and 9'-0" above each story's floor). Mid-height girts (5'-0" and 4'-6") are below the brace feet (7'-0" and 6'-0"); the door and every window cross their girt, which is cut at the kings (D066).
- **Totals:** 20 walls, 1 door, and 19 windows (2 of them with jacks). Rough openings total 264 sf (24.52640256 m²), leaving **2,016 sf (187.29252864 m²)** of net reference wall area.
- **Wall framing:** with the straw bale default, 79 buck pieces (3 for the door, 4 for each window). With stud infill, about 250 pieces (studs, cripples, kings, jacks, headers, rough sills, and cut girts). Exact counts follow from the approved values and are reconciled in tests.

This item comes last because its content depends on proposals 2–8. Approved values are recorded in a decision, as D053 was.

## 15. Draft acceptance criteria (pending approval)

Revised for D064–D072 (2026-11-21). They build on the routine items 10–15 (approved), and are confirmed only when the product owner approves them.

- **AC2b-01: version 3 only.** New projects are Reference House 001 v3 (version 3, D072). Version 2 snapshots are rejected with `UNSUPPORTED_SCHEMA_VERSION` (D055).
- **AC2b-02: assembly definitions.**
  - The project holds the straw bale and stud infill definitions (D067), with ordered layers, thicknesses, materials, and their framing layers: stud, girt, and header sections, spacing, girt count, jack threshold, and buck section (D066).
  - Every property value is either declared with its provenance or `null`. Unknown is never shown as 0 (D071).
- **AC2b-03: walls and wall framing.**
  - Walls are generated deterministically in every perimeter bay of both stories (D065): 20 for the reference house. IDs are stable under frame edits that keep the bay.
  - Wall framing (studs, girts, kings, jacks above the threshold, headers, rough sills, cripples, and bucks) is generated deterministically from each wall's definition and openings, with stable IDs (D066).
  - Switching the wall assembly is a validated, consequential command (D068) that leaves members and connections unchanged: 193 and 312.
- **AC2b-04: openings.**
  - Doors and windows are added, changed, and removed by validated routine commands, with stable IDs and rough-opening dimensions (D069).
  - A framed opening that does not fit is rejected, whether from its own command, a frame edit, or `SetWallAssembly`, with an actionable error. Nothing moves an opening silently.
  - Openings removed with their wall are listed in the preview.
- **AC2b-05: quantities reconcile.**
  - Gross, opening, and net reference areas reconcile with the walls and openings: 2,016 sf net for the reference house (D072). Layer quantities reconcile with the net areas.
  - Wall framing counts and lengths per kind and section reconcile with the pieces (D070).
  - The estimate prices layers per square meter and wall framing per meter. Unpriced items are never shown as 0.
- **AC2b-06: thermal figures are honest.**
  - Each wall's framing fraction comes from its generated framing, and its framing-corrected and center-of-cavity values use the named method (D071).
  - A figure appears only when every input is known, otherwise `null` with the missing inputs named.
  - Climate-specific details are flagged unverified, and no output claims code compliance or performance.
- **AC2b-07: exact impact.** `impacted_artifacts` lists an artifact if and only if its payload changes, for the new artifact and commands too (AC2-04).
- **AC2b-08: earlier slices still hold.** AC-01 to AC-09 and AC2-02 to AC2-09 pass against the v3 house, and AC2b-01 takes the place of AC2-01. Regenerated fixtures and golden records are reviewed as diffs (D055).
- **AC2b-09: still preliminary.** Every output is labeled preliminary. Quantities are reference areas and reference-axis lengths. Assumption lines say what is not counted or modeled (braces and members in areas, let-in notches, plates, fastenings, bale counts, opening products, clearance to member faces), and that the jack threshold and the thermal method are not code-derived.
- **AC2b-10: browser.**
  - Walls, wall framing, and openings appear in 2D, 3D, and the assembly schedule, with the Wall layers and Wall framing switches (D066).
  - The wall assembly and the openings are editable through the existing preview and apply flows.
  - The price-book form handles square-meter rows.
- **AC2b-11: traceability.** A traceability matrix covers AC2b-01 to AC2b-10. The golden record, property-based sequences (including the if-and-only-if impact check), budgets, and CI run them.

## 16. Draft task breakdown (pending approval)

| Task | Delivers | Depends on |
|---|---|---|
| `MODEL-006` | Schema version 3: `AssemblyDefinition` and `Layer` (with the framing layer, D066, D067, D071), `Wall`, the wall-framing kind, `Opening`, and the wall default; validation stages and detail codes, the girt fit and the framed-opening fit included; retirement of version 2; `SetWallAssembly` and the opening commands, with classifications (`vs02b-change-classes-1`); committed schema export | — |
| `ASM-001` | Wall generation, keys, and conformance; wall framing (D066): studs, girts, and opening framing, with their keys, section offsets, jack threshold, and conformance; survival of openings under regeneration; the template definitions and materials; the Reference House 001 v3 fixture (D072: 20 walls, 20 openings, 79 buck pieces); the ECMAScript oracle extended to walls and wall framing | MODEL-006 |
| `ART-003` | `assembly_schedule` (D070): walls, openings, wall framing pieces, aggregates, assumptions, and the D071 thermal figures; walls, framing, and openings in `plan2d` and `mesh3d`, tagged for the two switches; `assembly.` (`m2`) and `wallframing.` (`m`) estimate lines and price-book units; selectors for all of them; artifacts.md and OpenAPI updates; interim browser changes for anything the payloads would otherwise break | ASM-001 |
| `UI-004` | Browser: walls, wall framing, and openings in 2D and 3D, with the Wall layers and Wall framing switches; the assembly selector and the opening editor; the assembly schedule and estimate tables; thermal figures with their method, provenance, and warnings | ART-003 |
| `TEST-003` | `vs-02b-traceability.md` for AC2b-01 to AC2b-10; the golden scenario with the new commands and their rejections; the new commands in the sequences; budgets for the new payloads | All the above |

**Keeping `main` green:** retiring version 2 (MODEL-006) breaks every existing test until walls are generated. MODEL-006 and ASM-001 are therefore specified separately but **merged together**, as MODEL-005 and TIMBER-002 were. Every later task merges on its own, with CI passing.

**Drafting order:** once this scope is approved, the task files are drafted and approved one at a time, starting with MODEL-006, each in its own session.
