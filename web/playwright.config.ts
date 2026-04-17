import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  use: {
    baseURL: "http://127.0.0.1:3001",
    trace: "on-first-retry",
  },
  webServer: {
    command: "pnpm dev --hostname 127.0.0.1 --port 3001",
    port: 3001,
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
});
