/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Development: the browser talks to Vite only; /api is proxied to uvicorn (UI-001 §8, item 7).
const apiTarget = process.env.HOMEDESIGN_API_URL ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: Number(process.env.HOMEDESIGN_UI_PORT ?? 5173),
    strictPort: true,
    proxy: { "/api": { target: apiTarget, changeOrigin: false } },
  },
  test: {
    environment: "jsdom",
    include: ["tests/**/*.test.{ts,tsx}"],
    setupFiles: ["tests/setup.ts"],
  },
});
