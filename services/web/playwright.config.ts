import { defineConfig } from "@playwright/test";

// These tests boot the stack automatically via `webServer`:
// - web: http://localhost:3000
// - api: http://localhost:8000

export default defineConfig({
  testDir: "./tests",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  webServer: [
    {
      command: "python3 -m uvicorn services.api.main:app --host 127.0.0.1 --port 8000",
      url: "http://127.0.0.1:8000/health",
      reuseExistingServer: !process.env.CI,
      env: {
        PYTHONPATH: "/workspace",
      },
    },
    {
      command: "npm run dev -- --port 3000",
      cwd: __dirname,
      url: "http://127.0.0.1:3000",
      reuseExistingServer: !process.env.CI,
      env: {
        NEXT_PUBLIC_API_BASE_URL: "http://127.0.0.1:8000",
      },
    },
  ],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    trace: "retain-on-failure",
  },
});

