/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        // Local backend runs on 8002 (see backend/.env FRONTEND_URL / the
        // frontend .env VITE_API_URL). Keep in sync with the backend port.
        target: "http://localhost:8002",
        changeOrigin: true,
      },
    },
  },
  test: {
    // React 19.2's react-dom/test-utils only forwards to React.act, which is
    // absent from the production react build. The test script
    // (scripts/vitest-run.cjs) pins NODE_ENV=test so Vite resolves the dev
    // react build (which ships React.act); without it, every render() throws
    // "React.act is not a function".
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
  },
});
