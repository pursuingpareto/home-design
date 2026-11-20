# D062 — VS-02 browser: grouped connection markers, 3D visibility, a Connections tab, a generated catalog

**Status:** Confirmed; implemented ([UI-003](../../implementation/tasks/UI-003.md), VS-02)  
**Date:** 2026-11-20  
**Scope:** How the browser draws connection markers, where connection types are edited, and where the editor gets the connection catalog. Approved from [UI-003](../../implementation/tasks/UI-003.md) §12, items 10–13. The routine items 1–9 of that list are specified in the task file.  
**Resolves:** the open point of [D060](D060-vs02-artifact-payloads.md), "how the browser draws coincident connection markers", and the choice that [vs-02.md](../../implementation/acceptance-tests/vs-02.md) §12.2 left open ("connection types in the Sections tab, or a new tab").

## Decision

### One glyph per shared point (item 10)

Connections meet where member axes meet ([D058](D058-datum-reference-axes.md)), so many markers share a point. On Reference House 001 v2, the plan's 312 markers fall on 177 distinct points (up to 8 at an interior Level 1 or eave station), and the 3D view's on 193 (up to 4).

- The plan and the 3D view draw **one glyph per distinct position**. Positions are grouped by exact coordinate equality, per plan plane and per 3D point.
- A glyph for one connection behaves as a single marker.
- A glyph for several connections shows their count. It takes the type color when they share one type, and a "mixed" style otherwise. Its tooltip lists each connection, and clicking it selects all of them.
- Markers stay at the served positions (`xy_m`, `location_m`). The client computes nothing else.

### 3D markers over the members, and one switch (item 11)

- Every connection lies inside the member boxes, so 3D markers are drawn **after the members, without depth testing**. They stay visible through the boxes, and are picked before members.
- One **"Connections" switch** controls the markers in both views. It is on by default and remembered per browser, like the units preference. Turning it off hides the markers only; the schedule's connection tables are unaffected.
- Glyph sizes are fixed display symbols. They say nothing about a joint's size ([D054](D054-vs02-connection-catalog.md), AC2-07).

### A Connections tab (item 12)

Connection types are edited in a new **Connections** tab. The editor tabs become Footprint · Stories · Roof · Grid · Frame · Sections · Connections. Each row is one junction class, with its count, its two catalog types, the type's description, and a pricing note. Changes go through the preview (`SetConnectionType` is consequential, [D059](D059-vs02-junction-rules-connection-type-command.md)).

### A generated catalog export (item 13)

The browser gets the catalog from a **committed export generated from the backend**:

- the backend writes `docs/architecture/schemas/connection-catalog.json` from `model/connections.py`: the catalog version, each class's default and alternative, and each type's family and description;
- the frontend's `generate:api` step turns it into `src/api/connectionCatalog.ts`;
- the backend's schema-export check and the frontend's `check:api` both fail when it is stale.

The server still validates every command (D028). The catalog only limits what the editor offers.

## Rationale

- **Glyphs:** every connection stays reachable from the views at its served position. Overlapping markers would hide 135 of the 312 plan markers.
- **3D visibility:** depth-tested markers inside the boxes are invisible. Markers larger than the sections would read as joint sizes, which D054 rules out. The switch lets the frame be read without markers.
- **Tab:** the Sections tab stays about sections, and the Frame tab stays one command (`SetFrameParameters`, [MODEL-005](../../implementation/tasks/MODEL-005.md) §7).
- **Catalog:** one source, no runtime cost, and no hand copy, checked like the other committed exports.

## Alternatives considered

- **Markers:** offsetting each marker toward its entering member (markers leave the served positions, and in the plan a brace foot and its beam's end still coincide); drawing them overlapping.
- **3D:** ghosting the members (translucent boxes) whenever markers are shown; markers larger than the sections; no switch.
- **Tab:** the Sections tab (types per class parallel sections per role, one tab fewer); the Frame tab (two commands, one long form).
- **Catalog:** a hand-written client constant checked against the fixture; an API route; the full catalog in the schedule payload (reverses ART-002 §6.3 and needs a new generator version).

## What this does not decide

- Colors, line styles, and labels (UI-003 §4, §8.3, routine).
- Any payload, command, or validation change. The export adds a file and changes no behavior.
- Per-connection editing, new junction classes or types, and any engineering meaning of connections (D054, VS-04). Everything stays preliminary (AC-08).
