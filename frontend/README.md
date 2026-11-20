# Frontend

Browser client for VS-01 and VS-02 ([UI-001](../docs/implementation/tasks/UI-001.md), with editors from [UI-002](../docs/implementation/tasks/UI-002.md), and the complete frame and connections from [UI-003](../docs/implementation/tasks/UI-003.md)): React 18, TypeScript (strict), and Vite, with plain Three.js for the 3D view and SVG for the 2D plan ([overview.md](../docs/architecture/overview.md)). It holds no building rules: it sends typed commands to the API and renders the derived artifacts exactly as served (D028).

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

The component tests render payloads captured from the real backend in `tests/fixtures/reference-house-001.json`, including three previews (a width change, eave braces off, and `joist-beam` → `JOIST_HANGER`). Regenerate them with `uv run python -m homedesign.api.ui_fixtures` in `backend/`; the backend suite fails when they are stale.

## Layout

| Path | Contents |
|---|---|
| `src/api/` | Generated `schema.d.ts` and `connectionCatalog.ts` (committed; the D054 catalog exported by the backend, D062), type names, and the typed client (openapi-fetch) with `ApiError` |
| `src/display/` | `labels.ts`, the one module of display labels (artifacts, roles, junction classes, connection types; UI-003 §8.3), and `palette.ts`, one color per role and per connection type for the plan, the 3D view, and the schedule (UI-003 §4) |
| `src/units/` | Exact length and money input: imperial through 1/64-inch steps, cents via BigInt, half-even rounding |
| `src/views/` | `pairViews` (the only path to rendering 2D and 3D together), `Plan2dView` (SVG), `Mesh3dView` and `meshScene` (Three.js), `markers` (one glyph per distinct connection position, D062), `Legend`, and `highlight` (what the views draw as selected and report as picked) |
| `src/workspace/` | Revision data, the selection (a member or a set of connections, UI-003 §6), the command flow (preview → confirm, or apply for routine commands), the impact dialog, panels (including the schedule's connection tables), and the price-book form |
| `src/workspace/editors/` | The tabbed editors: Footprint · Stories · Roof · Grid · Frame · Sections · Connections (UI-002; Frame and Connections from UI-003) |
| `src/auth/`, `src/projects/`, `src/app/` | Sign-in, the project list, routing, preferences, and the app shell |
| `tests/` | Vitest tests, the fixture, and an in-memory HTTP fake that drives the real client |
| `e2e/` | Playwright tests for AC-01, AC-02, AC-05 to AC-08, undo, conflicts, price books, access, and every editor; `connections.spec.ts` for UI-003 (markers, selection, the Frame and Connections tabs, and the dialog's impact) |

## Views and selection (UI-003)

- **Roles:** each role has one color in the plan, the 3D view, and the schedule's swatches, and its own plan line weight. Knee braces are drawn after the beams, thinner and dashed. Each view has a legend of the roles (and connection types) present.
- **Connection markers:** one glyph per distinct position (exact coordinates, per plan plane and per 3D point), colored by type, or white with a dark ring when its connections have several types. A glyph for several connections shows their count. Glyph sizes are fixed symbols and mean nothing about a joint (AC2-07). In 3D, glyphs are drawn after the members without depth testing, and picked before them.
- **The "Connections" switch** above the views hides the markers in both. It is on by default and stored per browser (`homedesign.connections` in `localStorage`, `app/preferences.ts`). The schedule's connection tables are unaffected.
- **Selection:** a member, or a set of connections (a connection row, or every connection of a glyph). Selected connections highlight their glyphs and rows; their members get a second highlight color in both views and the member table, when the schedule is `CURRENT` for the views' revision. Picking the same thing again, clicking empty plan space, a plane change, or a commit clears it.
- **Test hooks:** plan glyphs carry `data-connection-ids`, `data-connection-count`, and `data-connection-type`; the plan figure reports `data-connection-count` and `data-glyph-count` for the markers drawn on the shown plane, and the 3D figure `data-member-count`, `data-connection-count` (as served), and `data-glyph-count` (0 when hidden).
