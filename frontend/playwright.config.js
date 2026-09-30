import { defineConfig, devices } from "@playwright/test"

// Runs against the built site (`vite preview`), which proxies /api to a running API server.
// Start the API first, for example against a database filled with `sentiment seed-demo`.
const apiUrl = process.env.E2E_API_URL ?? "http://127.0.0.1:8000"

export default defineConfig({
  testDir: "e2e",
  outputDir: "e2e/.results",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["list"]] : "list",
  use: { baseURL: "http://127.0.0.1:4173", trace: "retain-on-failure" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
  webServer: {
    command: "npm run build && npx vite preview --host 127.0.0.1 --port 4173 --strictPort",
    url: "http://127.0.0.1:4173",
    reuseExistingServer: !process.env.CI,
    env: { VITE_DEV_API_PROXY: apiUrl },
    timeout: 120_000,
  },
})
