import { defineConfig } from "@playwright/test";

const PORT = 5199;

export default defineConfig({
  testDir: "e2e",
  fullyParallel: true,
  retries: 1,
  reporter: "list",
  use: { baseURL: `http://localhost:${PORT}` },
  webServer: {
    command: `npx vite dev --port ${PORT} --strictPort`,
    url: `http://localhost:${PORT}/login`,
    reuseExistingServer: true,
    timeout: 120_000,
    env: {
      VITE_API_BASE_URL: process.env["VITE_API_BASE_URL"] ?? "http://localhost:8000/api/v1",
    },
  },
});
