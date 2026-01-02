import { defineConfig, devices } from "@playwright/test";
import path from "path";

// These tests boot the stack automatically via `webServer`:
// - web: http://localhost:3000
// - api: http://localhost:8000

const venvPython = path.resolve(__dirname, "../..", "venv", "Scripts", "python.exe");
// Keep E2E DB out of the repo working tree by default.
const dbUrl = process.env.RETAILOS_E2E_DATABASE_URL || "sqlite:////tmp/retailos_e2e.sqlite";

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
      command: process.platform === "win32"
        ? `"${venvPython}" -m uvicorn services.api.main:app --host 127.0.0.1 --port 8000`
        : "python3 -m uvicorn services.api.main:app --host 127.0.0.1 --port 8000",
      url: "http://127.0.0.1:8000/health",
      reuseExistingServer: !process.env.CI,
      env: {
        PYTHONPATH: path.resolve(__dirname, "../.."),
        DATABASE_URL: dbUrl,
        // Enable auth bypass for E2E tests
        RETAIL_OS_INSECURE_ALLOW_HEADER_ROLES: "true",
        RETAIL_OS_DEFAULT_ROLE: "power",
      },
      cwd: path.resolve(__dirname, "../.."),
    },
    {
      command: process.platform === "win32"
        ? `"${venvPython}" retail_os/trademe/worker.py`
        : "python3 retail_os/trademe/worker.py",
      cwd: path.resolve(__dirname, "../.."),
      reuseExistingServer: !process.env.CI,
      env: {
        PYTHONPATH: path.resolve(__dirname, "../.."),
        DATABASE_URL: dbUrl,
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
});

