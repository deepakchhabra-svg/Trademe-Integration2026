import { defineConfig, devices } from "@playwright/test";
import path from "path";

// These tests boot the stack automatically via `webServer`:
// - web: http://localhost:3000
// - api: http://localhost:8000

export default defineConfig({
  testDir: "./tests",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 1,
  workers: process.env.CI ? 4 : undefined,
  reporter: [
    ["html"],
    ["list"],
  ],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command: "python -m uvicorn services.api.main:app --host 127.0.0.1 --port 8000",
      url: "http://127.0.0.1:8000/health",
      reuseExistingServer: true,
      env: {
        PYTHONPATH: path.resolve(__dirname, "../.."),
        DATABASE_URL: "sqlite:///./test_db.sqlite", // Use a separate test DB if possible
      },
      cwd: path.resolve(__dirname, "../.."),
    },
    {
      command: "python retail_os/trademe/worker.py",
      cwd: path.resolve(__dirname, "../.."),
      env: {
        PYTHONPATH: path.resolve(__dirname, "../.."),
        NEXT_PUBLIC_TEST_MODE: "1",
        DATABASE_URL: "sqlite:///./test_db.sqlite",
      },
      // Worker doesn't have a URL to check, so we just let it run.
    },
    {
      command: "npm run dev -- --port 3000",
      cwd: __dirname,
      url: "http://127.0.0.1:3000",
      reuseExistingServer: true,
      env: {
        NEXT_PUBLIC_API_BASE_URL: "http://127.0.0.1:8000",
        NEXT_PUBLIC_TEST_MODE: "1",
      },
    },
  ],
});

