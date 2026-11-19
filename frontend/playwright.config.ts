/**
 * End-to-end tests (UI-001 §9, item 5): a real uvicorn API with the in-memory store and test tokens,
 * and the Vite dev server proxying /api to it. Both are started fresh for each run.
 */

import { defineConfig, devices } from "@playwright/test";

export const API_PORT = 8765;
export const UI_PORT = 5175;
export const TOKENS = { a: "e2e-token-a", b: "e2e-token-b" };
const ACTORS = { a: "00000000-0000-4000-8000-00000000e2e1", b: "00000000-0000-4000-8000-00000000e2e2" };

export default defineConfig({
  testDir: "e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  reporter: [["list"]],
  use: { baseURL: `http://127.0.0.1:${UI_PORT}`, trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1400, height: 1000 } } }],
  webServer: [
    {
      command: `uv run --project ../backend uvicorn homedesign.api.app:create_app --factory --host 127.0.0.1 --port ${API_PORT}`,
      url: `http://127.0.0.1:${API_PORT}/openapi.json`,
      reuseExistingServer: false,
      env: {
        HOMEDESIGN_STORE: "memory",
        HOMEDESIGN_PREVIEW_KEY: "e2e0".repeat(16), // test-only key
        HOMEDESIGN_DEV_TOKENS: `${TOKENS.a}=${ACTORS.a},${TOKENS.b}=${ACTORS.b}`,
      },
    },
    {
      command: `npx vite --host 127.0.0.1`,
      url: `http://127.0.0.1:${UI_PORT}`,
      reuseExistingServer: false,
      env: { HOMEDESIGN_API_URL: `http://127.0.0.1:${API_PORT}`, HOMEDESIGN_UI_PORT: String(UI_PORT) },
    },
  ],
});
