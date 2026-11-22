# Frontend

Browser client for VS-01, VS-02, and VS-02b ([UI-001](../docs/implementation/tasks/UI-001.md), with editors from [UI-002](../docs/implementation/tasks/UI-002.md), the complete frame and connections from [UI-003](../docs/implementation/tasks/UI-003.md), and walls, openings, wall framing, and the assembly schedule from [UI-004](../docs/implementation/tasks/UI-004.md)): React 18, TypeScript (strict), and Vite, with plain Three.js for the 3D view and SVG for the 2D plan ([overview.md](../docs/architecture/overview.md)). It holds no building rules: it sends typed commands to the API and renders the derived artifacts exactly as served (D028).

## Setup

Requires Node 22 or later.

```bash
cd frontend
npm ci
npx playwright install chromium   # once, for the end-to-end tests
```

## Running locally

The simplest way, from the repository root, starts the API and this dev server together:

```bash
scripts/dev.sh            # or: scripts/dev.sh --memory   (no database)
```

To run the pieces separately, start the API (see [backend/README.md](../backend/README.md)), then the dev server:

```bash
npm run dev
```

Open http://localhost:5173 and sign in with a token from `HOMEDESIGN_DEV_TOKENS`.

- **Proxy:** Vite proxies `/api` to `http://127.0.0.1:8000`, so the browser makes same-origin requests and needs no CORS. Set `HOMEDESIGN_API_URL` to point elsewhere.
- **Sign-in:** the token is kept in `sessionStorage` and is cleared when the tab closes. It is sent only as `Authorization: Bearer` (D050).
- **Repository launch configuration:** [`.claude/launch.json`](../.claude/launch.json) runs `scripts/dev.sh --memory` (token `dev-token`). It is for local use only.

## Commands

```bash
npm run dev            # dev server with the /api proxy
npm test               # Vitest unit and component tests (jsdom)
npm run e2e            # Playwright: starts uvicorn (in-memory store) and Vite, then runs e2e/
npm run typecheck      # tsc --noEmit over src, tests, and e2e
npm run build          # type-check and production build into dist/
npm run generate:api   # regenerate src/api/schema.d.ts (from openapi.v1.json) and src/api/connectionCatalog.ts (from connection-catalog.json)
npm run check:api      # fail if either generated file is stale
```

The component tests render payloads captured from the real backend in `tests/fixtures/reference-house-001.json`, including five previews (a width change, eave braces off, `joist-beam` → `JOIST_HANGER`, `SetWallAssembly` to stud infill, and re-identifying grid line `y1`), the five envelopes after the stud infill commit, and a **test-only** assembly schedule with declared values on every layer (built by the backend's builder; no project carries them). Regenerate them with `uv run python -m homedesign.api.ui_fixtures` in `backend/`; the backend suite fails when they are stale.

## Layout

| Path | Contents |
|---|---|
| `src/api/` | Generated `schema.d.ts` and `connectionCatalog.ts` (committed; the D054 catalog exported by the backend, D062), type names, and the typed client (openapi-fetch) with `ApiError` |
| `src/display/` | `labels.ts`, the one module of display labels (artifacts, roles, junction classes, connection types, UI-003 §8.3; assembly families, layer functions, opening kinds, sides, framing groups, and wall and opening labels, UI-004 §12), and `palette.ts`, one color per role, connection type, layer function, and framing group, the wall band, and the opening outline (UI-003 §4, UI-004 §12) |
| `src/units/` | Exact length and money input: imperial through 1/64-inch steps, cents via BigInt, half-even rounding; area and volume display; `thermal.ts`, the display conversion of thermal figures (D089) |
| `src/views/` | `pairViews` (the only path to rendering 2D and 3D together), `Plan2dView` (SVG), `Mesh3dView` and `meshScene` (Three.js), `markers` (one glyph per distinct connection position, D062), `walls` (band corners, framing marks, the framing box rule, void tessellation, and the joins the views are given), `Legend`, and `highlight` (what the views draw as selected and report as picked) |
| `src/workspace/` | Revision data, the selection (a member, a set of connections, a wall, an opening, or a set of wall framing pieces; UI-003 §6, UI-004 §7), the command flow (preview → confirm, or apply for routine commands), the impact dialog, panels (including the schedule's connection tables), `AssemblySchedulePanel`, `wallLabels` (wall, opening, and path labels), and the price-book form |
| `src/workspace/editors/` | The tabbed editors: Footprint · Stories · Roof · Grid · Frame · Sections · Connections · Walls (UI-002; Frame and Connections from UI-003; Walls from UI-004, D087) |
| `src/auth/`, `src/projects/`, `src/app/` | Sign-in, the project list, routing, preferences, and the app shell |
| `tests/` | Vitest tests, the fixture, and an in-memory HTTP fake that drives the real client |
| `e2e/` | Playwright tests for AC-01, AC-02, AC-05 to AC-08, undo, conflicts, price books, access, and every editor; `connections.spec.ts` for UI-003 (markers, selection, the Frame and Connections tabs, and the dialog's impact); `walls.spec.ts` for ART-003's `m2` prices and UI-004 (walls and switches, the assembly switch, opening edits, fit rejections, removed openings, and reported timings) |

## Views and selection (UI-003)

- **Roles:** each role has one color in the plan, the 3D view, and the schedule's swatches, and its own plan line weight. Knee braces are drawn after the beams, thinner and dashed. Each view has a legend of the roles (and connection types) present.
- **Connection markers:** one glyph per distinct position (exact coordinates, per plan plane and per 3D point), colored by type, or white with a dark ring when its connections have several types. A glyph for several connections shows their count. Glyph sizes are fixed symbols and mean nothing about a joint (AC2-07). In 3D, glyphs are drawn after the members without depth testing, and picked before them.
- **The "Connections" switch** above the views hides the markers in both. It is on by default and stored per browser (`homedesign.connections` in `localStorage`, `app/preferences.ts`). The schedule's connection tables are unaffected.
- **Selection:** a member, or a set of connections (a connection row, or every connection of a glyph). Selected connections highlight their glyphs and rows; their members get a second highlight color in both views and the member table, when the schedule is `CURRENT` for the views' revision. Picking the same thing again, clicking empty plan space, a plane change, or a commit clears it.
- **Test hooks:** plan glyphs carry `data-connection-ids`, `data-connection-count`, and `data-connection-type`; the plan figure reports `data-connection-count` and `data-glyph-count` for the markers drawn on the shown plane, and the 3D figure `data-member-count`, `data-connection-count` (as served), and `data-glyph-count` (0 when hidden).

## Walls and openings (UI-004)

- **Plan:** on Level 0 and Level 1, each wall is a band of its served extents (`exterior_m` out and `interior_m` in, D083) with a gap at each rough opening, drawn under the members. Openings are outlined in their gaps after the members, unfilled, so a thin build-up's openings show over the sill and beam lines; a window has a line along the reference line, a door none. Wall framing is drawn after the members as fixed-size symbols (squares for vertical pieces, lines for horizontal ones), one mark per distinct position: a header and its rough sill, a buck head and its sill, and the two cripples of a position share a mark (D062's rule).
- **3D:** each wall is one opaque solid per layer, tessellated around its voids and colored by layer function; each void has a thin outline on the exterior face and an invisible pick surface. Wall framing is one box per piece (one `InstancedMesh` per framing group), oriented by the served rule: through-wall along the wall's `outward_xy`, in-plane perpendicular to the axis. Glyphs are still picked first; otherwise the nearest visible member, layer (its wall), opening, or piece.
- **The "Wall layers" and "Wall framing" switches** beside "Connections" hide the bands, openings, and layers, or the framing, in both views. Both are on by default and stored per browser (`homedesign.wallLayers`, `homedesign.wallFraming`). Turning one off clears a selection of what it hides. They change no schedule, estimate, or command (D066).
- **Joins:** wall and opening labels, piece kinds with their sections and keys, and layer materials come from the same revision's assembly schedule (D086), computed in the workspace and passed to the views; without a `CURRENT` schedule for the views' revision, tooltips show the kind or key alone and an opening's framing is not highlighted.
- **Selection:** a wall (band, layer, or row), an opening (mark, outline, or row; its framing pieces get the second highlight color), or wall framing pieces (mark, box, or row).
- **Walls tab** (D087): the assembly select with the chosen definition's build-up from the snapshot, previewed (`SetWallAssembly`); the openings grouped by wall, and a form for the current or a new opening, applied directly with Undo (`AddOpening`, `SetOpening`, `RemoveOpening`). Picking an opening anywhere makes it current there, and picking a wall makes it the wall for a new opening; the active tab does not change by itself.
- **Dialog:** wall and wall framing counts, family labels for the definition, labels for added and removed openings, and a warning block above Confirm that lists the openings an edit removes (D088). Paths into an opening, wall, or definition read as its label, with the raw path in the tooltip.
- **Assembly schedule panel:** the climate warning (from the envelope) and details, the definition's layers with declared values and provenance ("Not declared" when null), the thermal figures with the method's notes ("Not computed" when null, with the missing inputs listed once), walls, openings, the framing takeoff, layer quantities, pieces, and the assumptions. Thermal figures follow the units switch (D089: SI as served, or IT-Btu imperial units; vapor permeances stay SI).
- **Test hooks:** the plan figure reports `data-wall-count`, `data-opening-count`, `data-framing-count`, and `data-framing-mark-count` for the shown plane; the 3D figure `data-wall-count`, `data-opening-count`, and `data-framing-count` as served, and `data-wall-solid-count` and `data-framing-box-count` as drawn (0 when hidden). Bands carry `data-wall-id`, opening marks `data-opening-id` and `data-opening-kind`, framing marks `data-piece-ids` and `data-piece-kind`, and the schedule's rows the same IDs.
