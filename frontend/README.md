# Frontend

Browser client for VS-01 ([UI-001](../docs/implementation/tasks/UI-001.md), with editors from [UI-002](../docs/implementation/tasks/UI-002.md)): React 18, TypeScript (strict), and Vite, with plain Three.js for the 3D view and SVG for the 2D plan ([overview.md](../docs/architecture/overview.md)). It holds no building rules: it sends typed commands to the API and renders the derived artifacts exactly as served (D028).

## Setup

Requires Node 22 or later.

```bash
cd frontend
npm ci
npx playwright install chromium   # once, for the end-to-end tests
```

## Running locally

Start the API (see [backend/README.md](../backend/README.md)), then the dev server:

```bash
npm run dev
```

Open http://localhost:5173 and sign in with a token from `HOMEDESIGN_DEV_TOKENS`.

- **Proxy:** Vite proxies `/api` to `http://127.0.0.1:8000`, so the browser makes same-origin requests and needs no CORS. Set `HOMEDESIGN_API_URL` to point elsewhere.
- **Sign-in:** the token is kept in `sessionStorage` and is cleared when the tab closes. It is sent only as `Authorization: Bearer` (D050).
- **Repository launch configuration:** [`.claude/launch.json`](../.claude/launch.json) starts an in-memory API with the token `dev-token` and an all-zero preview key. It is for local use only.

## Commands

```bash
npm run dev            # dev server with the /api proxy
npm test               # Vitest unit and component tests (jsdom)
npm run e2e            # Playwright: starts uvicorn (in-memory store) and Vite, then runs e2e/
npm run typecheck      # tsc --noEmit over src, tests, and e2e
npm run build          # type-check and production build into dist/
npm run generate:api   # regenerate src/api/schema.d.ts from docs/architecture/schemas/openapi.v1.json
npm run check:api      # fail if src/api/schema.d.ts is stale
```

The component tests render payloads captured from the real backend in `tests/fixtures/reference-house-001.json`. Regenerate them with `uv run python -m homedesign.api.ui_fixtures` in `backend/`; the backend suite fails when they are stale.

## Layout

| Path | Contents |
|---|---|
| `src/api/` | Generated `schema.d.ts` (committed), type names, and the typed client (openapi-fetch) with `ApiError` |
| `src/units/` | Exact length and money input: imperial through 1/64-inch steps, cents via BigInt, half-even rounding |
| `src/views/` | `pairViews` (the only path to rendering 2D and 3D together), `Plan2dView` (SVG), `Mesh3dView` and `meshScene` (Three.js) |
| `src/workspace/` | Revision data, the command flow (preview → confirm, or apply for routine commands), the impact dialog, panels, and the price-book form |
| `src/workspace/editors/` | The tabbed editors (UI-002): footprint, stories, roof, grid, and sections |
| `src/auth/`, `src/projects/`, `src/app/` | Sign-in, the project list, routing, preferences, and the app shell |
| `tests/` | Vitest tests, the fixture, and an in-memory HTTP fake that drives the real client |
| `e2e/` | Playwright tests for AC-01, AC-02, AC-05 to AC-08, undo, conflicts, price books, access, and every editor |
